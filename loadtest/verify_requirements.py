"""Run real HTTP checks against two managed API processes and shared Redis.

Run: python -m loadtest.verify_requirements
Writes reports/backend_verification.json; cleans only its unique Redis prefix.
Existing API servers and normal Redis data are left alone.
"""

import asyncio
import json
import os
import platform
import socket
import subprocess
import sys
import time
from collections import Counter
from pathlib import Path
from uuid import uuid4

import httpx
import redis

ROOT = Path(__file__).resolve().parents[1]
ADMIN = {"X-API-Key": os.environ.get("ADMIN_API_KEY", "admin-secret-key")}
USERS = list(zip(range(104, 109), [3, 4, 5, 7, 10]))


def sample(response):
    return {
        "status": response.status_code,
        "headers": {key: value for key, value in response.headers.items()
                    if key.startswith("x-") or key == "retry-after"},
        "body": response.json(),
    }


class Servers:
    def __init__(self, env):
        self.env = env
        self.processes = []
        self.ports = []
        # Let the OS choose free test ports instead of using existing APIs.
        sockets = [socket.socket(), socket.socket()]
        try:
            for sock in sockets:
                sock.bind(("127.0.0.1", 0))
                self.ports.append(sock.getsockname()[1])
        finally:
            for sock in sockets:
                sock.close()

    async def start(self, index):
        env = {**self.env, "INSTANCE_ID": f"verification-api{index + 1}"}
        process = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "app.main:app",
             "--host", "127.0.0.1", "--port", str(self.ports[index]),
             "--log-level", "error"],
            cwd=ROOT, env=env, stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=(subprocess.CREATE_NO_WINDOW if os.name == "nt"
                           else 0),
        )
        self.processes.append(process)
        async with httpx.AsyncClient(timeout=1) as client:
            for _ in range(150):
                if process.poll() is not None:
                    raise RuntimeError("Verification API exited at startup")
                try:
                    response = await client.get(self.url(index, "/health"))
                    if response.status_code == 200:
                        return process
                except httpx.HTTPError:
                    pass
                await asyncio.sleep(0.1)
        raise RuntimeError("Verification API did not become healthy")

    def url(self, index, path):
        return f"http://127.0.0.1:{self.ports[index]}{path}"

    @staticmethod
    def stop(process):
        if process.poll() is None:
            process.kill()
            process.wait(timeout=10)

    def close(self):
        for process in self.processes:
            self.stop(process)


async def configure(client, servers, number, quota, window):
    response = await client.post(servers.url(0, "/api/config"),
                                 headers=ADMIN, json={
        "user_id": f"user_{number}", "limit": quota,
        "window_seconds": window,
    })
    assert response.status_code == 200, sample(response)
    return response


def user_headers(number):
    return {"X-API-Key": f"key-user-{number}"}


async def verify_algorithm(algorithm, env):
    servers = Servers({**env, "RATE_LIMIT_ALGORITHM": algorithm,
                       "REDIS_MAX_CONNECTIONS": "10"})
    result = {}
    try:
        first = await servers.start(0)
        await servers.start(1)
        async with httpx.AsyncClient(
            timeout=45, limits=httpx.Limits(max_connections=500)
        ) as client:
            result["health"] = sample(await client.get(
                servers.url(0, "/health")
            ))
            configured = await configure(client, servers, 104, 3, 60)
            result["config"] = sample(configured)
            initial = await client.get(servers.url(1, "/api/status"),
                                       headers=user_headers(104))
            again = await client.get(servers.url(0, "/api/status"),
                                     headers=user_headers(104))
            assert initial.json()["remaining_requests"] == 3
            assert again.json()["remaining_requests"] == 3
            replies = []
            for index in range(4):
                replies.append(await client.get(
                    servers.url(index % 2, "/api/data"),
                    headers=user_headers(104),
                ))
            assert [reply.status_code for reply in replies] == [
                200, 200, 200, 429
            ]
            result["success"] = sample(replies[0])
            result["quota_exceeded"] = sample(replies[-1])
            result["status"] = sample(await client.get(
                servers.url(1, "/api/status"), headers=user_headers(104)
            ))
            for reply in replies:
                assert reply.headers["X-RateLimit-Limit"] == "3"
            assert replies[-1].headers["Retry-After"] == str(
                replies[-1].json()["retry_after"]
            )
            assert 1 <= replies[-1].json()["retry_after"] <= 60
            analytics = await client.get(servers.url(1, "/api/analytics"),
                                         headers=ADMIN)
            assert analytics.json()["users"]["user_104"] == {
                "allowed": 3, "blocked": 1
            }
            result["analytics_sample"] = sample(analytics)
            result["invalid_auth"] = sample(await client.get(
                servers.url(0, "/api/data"),
                headers={"X-API-Key": "invalid"},
            ))
            assert result["invalid_auth"]["status"] == 401
            forbidden = await client.post(
                servers.url(1, "/api/config"), headers=user_headers(104),
                json={"user_id": "user_105", "limit": 999,
                      "window_seconds": 60},
            )
            assert forbidden.status_code == 403
            result["forbidden_config"] = sample(forbidden)
            await configure(client, servers, 101, 10, 3600)
            responses = await asyncio.gather(*[
                client.get(servers.url(index % 2, "/api/data"),
                           headers=user_headers(101))
                for index in range(100)
            ])
            counts = Counter(reply.status_code for reply in responses)
            assert counts == {200: 10, 429: 90}, counts
            result["required_100_request_concurrency"] = dict(counts)
            for number, quota in USERS:
                await configure(client, servers, number, quota, 3600)
            async def exercise(number, quota):
                responses = await asyncio.gather(*[
                    client.get(servers.url(index % 2, "/api/data"),
                               headers=user_headers(number))
                    for index in range(100)
                ])
                counts = Counter(reply.status_code for reply in responses)
                assert counts == {200: quota, 429: 100 - quota}, counts
                served = sorted({reply.headers["X-Served-By"]
                                 for reply in responses})
                assert len(served) == 2
                return {"user_id": f"user_{number}", "quota": quota,
                        "status_counts": dict(counts), "served_by": served}
            result["five_users_500_simultaneous"] = await asyncio.gather(*[
                exercise(number, quota) for number, quota in USERS
            ])
            analytics = (await client.get(
                servers.url(1, "/api/analytics"), headers=ADMIN
            )).json()["users"]
            for number, quota in USERS:
                # The endpoint sample above contributed 3 allowed/1 blocked.
                offset = 3 if number == 104 else 0
                blocked_offset = 1 if number == 104 else 0
                assert analytics[f"user_{number}"] == {
                    "allowed": quota + offset,
                    "blocked": 100 - quota + blocked_offset,
                }
            servers.stop(first)
            await servers.start(0)
            restarted = await client.get(
                servers.url(0, "/api/data"), headers=user_headers(108)
            )
            assert restarted.status_code == 429
            persisted = await client.get(
                servers.url(0, "/api/status"), headers=user_headers(108)
            )
            assert persisted.json()["limit"] == 10
            assert persisted.json()["window_seconds"] == 3600
            assert persisted.json()["remaining_requests"] == 0
            result["after_real_api_restart"] = sample(persisted)
            await configure(client, servers, 104, 2, 2)
            for _ in range(2):
                assert (await client.get(
                    servers.url(0, "/api/data"), headers=user_headers(104)
                )).status_code == 200
            blocked = await client.get(
                servers.url(1, "/api/data"), headers=user_headers(104)
            )
            assert blocked.status_code == 429
            wait = blocked.json()["retry_after"]
            await asyncio.sleep(wait + 0.2)
            recovered = await client.get(
                servers.url(1, "/api/data"), headers=user_headers(104)
            )
            assert recovered.status_code == 200
            result["recovery"] = {"wait_seconds": wait,
                                   "response": sample(recovered)}
        print(f"{algorithm}: endpoints, 100/500 concurrency, analytics, "
              "two processes, restart and recovery PASS", flush=True)
        return result
    finally:
        servers.close()


async def verify_active(algorithm, env):
    servers = Servers({
        **env, "RATE_LIMIT_ALGORITHM": algorithm,
        "MAX_ACTIVE_REQUESTS_PER_USER": "1",
        "ACTIVE_REQUESTS_TTL_SECONDS": "1",
        "SIMULATED_WORK_SECONDS": "1.8",
    })
    try:
        first_process = await servers.start(0)
        await servers.start(1)
        async with httpx.AsyncClient(timeout=15) as client:
            await configure(client, servers, 104, 100, 3600)
            first = asyncio.create_task(client.get(
                servers.url(0, "/api/data"), headers=user_headers(104)
            ))
            async def wait_for_slot():
                for _ in range(100):
                    status = await client.get(
                        servers.url(1, "/api/status"),
                        headers=user_headers(104),
                    )
                    if status.json()["active_requests"] == 1:
                        return
                    await asyncio.sleep(0.01)
                raise AssertionError("Request never acquired its slot")
            await wait_for_slot()
            await asyncio.sleep(1.15)
            assert not first.done()
            blocked = await client.get(
                servers.url(1, "/api/data"), headers=user_headers(104)
            )
            assert blocked.status_code == 429
            assert blocked.json()["error"] == (
                "Too many simultaneous requests"
            )
            assert blocked.headers["X-RateLimit-Limit"] == "100"
            assert int(blocked.headers["Retry-After"]) > 0
            assert (await first).status_code == 200
            result = {"after_original_ttl": sample(blocked)}
            await configure(client, servers, 105, 100, 3600)
            crash_request = asyncio.create_task(client.get(
                servers.url(0, "/api/data"), headers=user_headers(105)
            ))
            # Observe the new user's owned slot before killing its process.
            for _ in range(100):
                status = await client.get(servers.url(1, "/api/status"),
                                           headers=user_headers(105))
                if status.json()["active_requests"] == 1:
                    break
                await asyncio.sleep(0.01)
            assert status.json()["active_requests"] == 1
            servers.stop(first_process)
            await asyncio.gather(crash_request, return_exceptions=True)
            await asyncio.sleep(1.2)
            status = await client.get(servers.url(1, "/api/status"),
                                       headers=user_headers(105))
            assert status.json()["active_requests"] == 0
            recovered = await client.get(servers.url(1, "/api/data"),
                                          headers=user_headers(105))
            assert recovered.status_code == 200
            result["after_process_crash"] = sample(status)
            result["request_after_crash"] = sample(recovered)
            print(f"{algorithm}: cross-process renewal and crash recovery "
                  "PASS", flush=True)
            return result
    finally:
        servers.close()


async def main():
    # Settings reads .env consistently with the application, including admin.
    from app.settings import settings

    ADMIN["X-API-Key"] = settings.admin_api_key
    prefix = f"verification:{uuid4().hex}:"
    env = {**os.environ, "REDIS_URL": settings.redis_url,
           "REDIS_KEY_PREFIX": prefix,
           "MAX_ACTIVE_REQUESTS_PER_USER": "200",
           "SIMULATED_WORK_SECONDS": "0",
           "ACTIVE_REQUESTS_TTL_SECONDS": "30"}
    storage = redis.Redis.from_url(settings.redis_url, decode_responses=True)
    storage.ping()
    evidence = {"timestamp_utc": time.strftime(
        "%Y-%m-%dT%H:%M:%SZ", time.gmtime()
    ), "python": platform.python_version(), "platform": platform.platform(),
        "redis_version": storage.info("server")["redis_version"],
        "algorithms": {}}
    try:
        for algorithm in ("sliding_window_log", "token_bucket"):
            evidence["algorithms"][algorithm] = await verify_algorithm(
                algorithm, env
            )
            evidence["algorithms"][algorithm]["active_limit"] = (
                await verify_active(algorithm, env)
            )
            # Keep samples for each algorithm independent.
            keys = list(storage.scan_iter(match=f"{prefix}*"))
            if keys:
                storage.delete(*keys)
        benchmark = subprocess.run(
            [sys.executable, "-m", "benchmarks.compare_algorithms"],
            cwd=ROOT, env=env, capture_output=True, text=True, check=True,
        )
        evidence["benchmark"] = benchmark.stdout
        print(benchmark.stdout, flush=True)
        evidence["result"] = "PASS"
        report = ROOT / "reports" / "backend_verification.json"
        report.parent.mkdir(exist_ok=True)
        report.write_text(json.dumps(evidence, indent=2) + "\n")
        print(f"Evidence saved to {report}", flush=True)
    finally:
        keys = list(storage.scan_iter(match=f"{prefix}*"))
        if keys:
            storage.delete(*keys)
        storage.close()


if __name__ == "__main__":
    asyncio.run(main())

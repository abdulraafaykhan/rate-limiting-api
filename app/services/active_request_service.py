"""Redis leases bound simultaneous requests across API processes."""

import asyncio
import logging
from contextlib import asynccontextmanager, suppress
from uuid import uuid4

import anyio
from redis.asyncio import Redis
from redis.exceptions import ConnectionError, RedisError

from app.exceptions import TooManyActiveRequests
from app.redis_keys import active_requests_key
from app.services.lua_loader import load_lua_script
from app.settings import Settings

logger = logging.getLogger(__name__)


class ActiveRequestService:
    """Each running request owns one renewable slot with crash expiry."""

    def __init__(self, redis_client: Redis, settings: Settings) -> None:
        self.redis_client = redis_client
        self.settings = settings
        for operation in ("acquire", "release", "renew", "count"):
            name = (
                "count_active_requests" if operation == "count"
                else f"{operation}_active_request"
            )
            script = redis_client.register_script(
                load_lua_script(name)
            )
            setattr(self, f"{operation}_script", script)

    async def acquire(self, user_id: str) -> str:
        owner = uuid4().hex
        maximum = self.settings.max_active_requests_per_user
        allowed, _, retry = await self.acquire_script(
            keys=[active_requests_key(user_id)],
            args=[maximum, self.settings.active_requests_ttl_seconds, owner],
        )
        if not allowed:
            raise TooManyActiveRequests(maximum, int(retry))
        return owner

    async def release(self, user_id: str, owner: str) -> None:
        await self.release_script(
            keys=[active_requests_key(user_id)], args=[owner]
        )

    async def renew(self, user_id: str, owner: str) -> bool:
        return bool(await self.renew_script(
            keys=[active_requests_key(user_id)],
            args=[owner, self.settings.active_requests_ttl_seconds],
        ))

    async def count(self, user_id: str) -> int:
        return int(await self.count_script(
            keys=[active_requests_key(user_id)]
        ))

    async def _heartbeat(self, user_id, owner, request_task, lost) -> None:
        try:
            while True:
                await asyncio.sleep(
                    self.settings.active_requests_ttl_seconds / 3
                )
                if not await self.renew(user_id, owner):
                    raise RuntimeError("Active request lease was lost")
        except (RedisError, RuntimeError):
            # Work must stop if its distributed slot can no longer be held.
            logger.exception("Unable to renew active request lease")
            lost.set()
            request_task.cancel()

    @asynccontextmanager
    async def hold(self, user_id: str):
        owner = await self.acquire(user_id)
        lost = asyncio.Event()
        heartbeat = asyncio.create_task(
            self._heartbeat(user_id, owner, asyncio.current_task(), lost)
        )
        try:
            yield
        except asyncio.CancelledError:
            if lost.is_set():
                # Turn internal lease-loss cancellation into the same 503
                # used for storage outages, preserving client cancellation.
                raise ConnectionError("Active request lease unavailable")
            raise
        finally:
            # Shield cleanup from client cancellation. If Redis is down,
            # expiry recovers the slot without masking the original error.
            with anyio.CancelScope(shield=True):
                heartbeat.cancel()
                with suppress(asyncio.CancelledError):
                    await heartbeat
                try:
                    await self.release(user_id, owner)
                except RedisError:
                    logger.warning("Slot release failed; lease will expire")

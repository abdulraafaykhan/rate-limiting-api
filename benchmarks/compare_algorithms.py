"""Bonus 4: compare the speed and memory use of the two algorithms.

Run from the project root (Redis must be running):

    python -m benchmarks.compare_algorithms

Change the three numbers below to make the test bigger or smaller.
"""

import asyncio
import time

from app.models.rate_limit import RateLimitConfig
from app.redis_client import close_redis_client, get_redis_client
from app.redis_keys import rate_limit_key
from app.services.algorithms import ALGORITHM_CLASSES

# How many requests each algorithm handles in each test.
TOTAL_REQUESTS = 2000

# How many requests run at the same moment in the concurrent test.
CONCURRENCY = 50

# A huge quota, so every request is allowed and we measure pure speed.
BENCHMARK_CONFIG = RateLimitConfig(
    limit=TOTAL_REQUESTS * 10,
    window_seconds=60,
)


def percentile_95(durations: list[float]) -> float:
    """Return the value that 95% of the durations are below."""
    ordered = sorted(durations)
    index = int(len(ordered) * 0.95) - 1
    return ordered[max(index, 0)]


async def run_sequential(algorithm, user_id: str) -> tuple[float, list[float]]:
    """Send requests one after another and time each one."""
    durations = []
    started_at = time.perf_counter()

    for _ in range(TOTAL_REQUESTS):
        call_started_at = time.perf_counter()
        await algorithm.check(user_id, BENCHMARK_CONFIG)
        durations.append(time.perf_counter() - call_started_at)

    return time.perf_counter() - started_at, durations


async def run_concurrent(algorithm, user_id: str) -> tuple[float, list[float]]:
    """Send many requests at once (limited to CONCURRENCY at a time)."""
    durations = []
    # The semaphore stops more than CONCURRENCY calls from running together.
    semaphore = asyncio.Semaphore(CONCURRENCY)

    async def timed_call() -> None:
        async with semaphore:
            call_started_at = time.perf_counter()
            await algorithm.check(user_id, BENCHMARK_CONFIG)
            durations.append(time.perf_counter() - call_started_at)

    started_at = time.perf_counter()
    await asyncio.gather(*[timed_call() for _ in range(TOTAL_REQUESTS)])

    return time.perf_counter() - started_at, durations


def print_row(name: str, mode: str, total_seconds: float, durations) -> None:
    """Print one result line of the table."""
    requests_per_second = TOTAL_REQUESTS / total_seconds
    average_ms = sum(durations) / len(durations) * 1000
    p95_ms = percentile_95(durations) * 1000
    print(
        f"{name:<20} {mode:<11} {requests_per_second:>10.0f} "
        f"{average_ms:>9.3f} {p95_ms:>9.3f}"
    )


async def main() -> None:
    redis_client = get_redis_client()
    memory_results = {}

    print(f"\n{TOTAL_REQUESTS} requests per test, concurrency {CONCURRENCY}\n")
    print(
        f"{'algorithm':<20} {'mode':<11} {'req/sec':>10} "
        f"{'avg ms':>9} {'p95 ms':>9}"
    )
    print("-" * 63)

    for name, algorithm_class in ALGORITHM_CLASSES.items():
        algorithm = algorithm_class(redis_client)
        user_id = f"benchmark_{name}"
        key = rate_limit_key(name, user_id)

        # Start from a clean key so earlier runs cannot change the result.
        await redis_client.delete(key)

        total_seconds, durations = await run_sequential(algorithm, user_id)
        print_row(name, "sequential", total_seconds, durations)

        total_seconds, durations = await run_concurrent(algorithm, user_id)
        print_row(name, "concurrent", total_seconds, durations)

        # After 2 x TOTAL_REQUESTS calls, see how much memory Redis uses.
        memory_results[name] = await redis_client.memory_usage(key)

        # Remove the benchmark data so nothing is left behind.
        await redis_client.delete(key)

    print("\nRedis memory used by ONE user's data after the test:")
    for name, bytes_used in memory_results.items():
        print(f"  {name:<20} {bytes_used} bytes")

    await close_redis_client()


if __name__ == "__main__":
    asyncio.run(main())

"""Measure sequential versus bounded-parallel async work.

Run: python scripts/bench.py --items 10 --delay-ms 100 --concurrency 10
"""

from __future__ import annotations

import argparse
import asyncio
import time
from collections.abc import Awaitable, Callable


AsyncOperation = Callable[[int], Awaitable[None]]


async def run_sequential(items: list[int], operation: AsyncOperation) -> float:
    start = time.perf_counter()
    for item in items:
        await operation(item)
    return time.perf_counter() - start


async def run_parallel(items: list[int], operation: AsyncOperation, concurrency: int) -> float:
    semaphore = asyncio.Semaphore(concurrency)

    async def bounded(item: int) -> None:
        async with semaphore:
            await operation(item)

    start = time.perf_counter()
    await asyncio.gather(*(bounded(item) for item in items))
    return time.perf_counter() - start


async def benchmark(items_count: int, delay_seconds: float, concurrency: int) -> tuple[float, float]:
    async def simulated_lookup(_item: int) -> None:
        await asyncio.sleep(delay_seconds)

    items = list(range(items_count))
    sequential = await run_sequential(items, simulated_lookup)
    parallel = await run_parallel(items, simulated_lookup, concurrency)
    return sequential, parallel


def main() -> None:
    parser = argparse.ArgumentParser(description="FoodLens concurrency benchmark")
    parser.add_argument("--items", type=int, default=10)
    parser.add_argument("--delay-ms", type=float, default=100)
    parser.add_argument("--concurrency", type=int, default=10)
    args = parser.parse_args()
    if args.items < 1 or args.delay_ms < 0 or args.concurrency < 1:
        parser.error("items and concurrency must be positive; delay-ms cannot be negative")

    sequential, parallel = asyncio.run(
        benchmark(args.items, args.delay_ms / 1000, args.concurrency)
    )
    speedup = sequential / parallel if parallel else float("inf")
    print(f"items={args.items}, delay={args.delay_ms:.0f}ms, concurrency={args.concurrency}")
    print(f"sequential: {sequential:.3f}s")
    print(f"parallel:   {parallel:.3f}s")
    print(f"speed-up:   {speedup:.2f}x")


if __name__ == "__main__":
    main()

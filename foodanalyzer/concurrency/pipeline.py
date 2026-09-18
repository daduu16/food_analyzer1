from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable, Sequence
from dataclasses import dataclass
from typing import Generic, TypeVar


Item = TypeVar("Item")
Result = TypeVar("Result")


@dataclass(frozen=True)
class LookupOutcome(Generic[Item, Result]):
    item: Item
    value: Result | None = None
    error: Exception | None = None


async def lookup_all(
    items: Sequence[Item], lookup: Callable[[Item], Awaitable[Result]], *, max_concurrency: int = 10
) -> list[LookupOutcome[Item, Result]]:
    """Look up all items concurrently while never exceeding the given limit.

    Errors are retained per item, so one unavailable USDA result does not cancel
    the full food analysis.
    """
    if max_concurrency < 1:
        raise ValueError("max_concurrency must be at least 1")
    semaphore = asyncio.Semaphore(max_concurrency)

    async def bounded(item: Item) -> LookupOutcome[Item, Result]:
        try:
            async with semaphore:
                return LookupOutcome(item=item, value=await lookup(item))
        except Exception as exc:  # returned as a partial result to the caller
            return LookupOutcome(item=item, error=exc)

    return list(await asyncio.gather(*(bounded(item) for item in items)))

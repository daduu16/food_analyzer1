from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass
from typing import Generic, TypeVar


T = TypeVar("T")


@dataclass(frozen=True)
class _CacheEntry(Generic[T]):
    value: T
    expires_at: float


class NutritionCache(Generic[T]):
    """A lock-protected ingredient cache with a default 24-hour TTL."""

    def __init__(self, ttl_seconds: int = 86_400) -> None:
        self.ttl_seconds = ttl_seconds
        self._entries: dict[str, _CacheEntry[T]] = {}
        self._lock = asyncio.Lock()

    @staticmethod
    def normalize(ingredient_name: str) -> str:
        return " ".join(ingredient_name.casefold().strip().split())

    async def get(self, ingredient_name: str) -> T | None:
        key = self.normalize(ingredient_name)
        async with self._lock:
            entry = self._entries.get(key)
            if entry is None:
                return None
            if entry.expires_at <= time.monotonic():
                del self._entries[key]
                return None
            return entry.value

    async def set(self, ingredient_name: str, value: T) -> None:
        key = self.normalize(ingredient_name)
        async with self._lock:
            self._entries[key] = _CacheEntry(value, time.monotonic() + self.ttl_seconds)

    async def clear(self) -> None:
        async with self._lock:
            self._entries.clear()

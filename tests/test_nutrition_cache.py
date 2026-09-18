from __future__ import annotations

import asyncio

from foodanalyzer.services.nutrition_cache import NutritionCache


def test_cache_normalizes_ingredient_names():
    async def scenario():
        cache = NutritionCache[str]()
        await cache.set("  Chicken   Breast ", "cached")
        return await cache.get("chicken breast")

    assert asyncio.run(scenario()) == "cached"


def test_cache_expires_entries():
    async def scenario():
        cache = NutritionCache[str](ttl_seconds=0)
        await cache.set("tomato", "cached")
        return await cache.get("tomato")

    assert asyncio.run(scenario()) is None

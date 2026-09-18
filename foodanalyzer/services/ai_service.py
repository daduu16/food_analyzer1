from __future__ import annotations

import asyncio
import inspect
import logging
import random
from collections.abc import Callable
from typing import TypeVar

from ai import Ingredient, NutritionFacts, NutritionProvider, identify_ingredients
from ai.providers.base import ProviderError, VLMProvider

from foodanalyzer.services.nutrition_cache import NutritionCache
from foodanalyzer.services.nutrition_normalizer import normalize_energy_unit


T = TypeVar("T")
logger = logging.getLogger(__name__)


async def retry_call(
    operation: Callable[[], T], *, attempts: int = 3, base_delay: float = 0.25, timeout_seconds: float = 20
) -> T:
    """Run a blocking provider call with timeout and exponential-backoff retry."""
    if attempts < 1:
        raise ValueError("attempts must be at least 1")

    for attempt in range(1, attempts + 1):
        try:
            # The supplied ai package uses synchronous provider SDK calls, so do
            # not block FastAPI's event loop while waiting for a network response.
            result = await asyncio.wait_for(asyncio.to_thread(operation), timeout=timeout_seconds)
            if inspect.isawaitable(result):
                return await asyncio.wait_for(result, timeout=timeout_seconds)
            return result
        except (ProviderError, TimeoutError, asyncio.TimeoutError) as exc:
            if attempt == attempts:
                raise ProviderError(f"Provider unavailable after {attempts} attempt(s): {exc}") from exc
            delay = base_delay * (2 ** (attempt - 1)) + random.uniform(0, base_delay / 4)
            logger.warning("Provider call failed (attempt %d/%d); retrying in %.2fs", attempt, attempts, delay)
            await asyncio.sleep(delay)
    raise RuntimeError("unreachable")


class AIService:
    """Adapter around the supplied ai package with cache, retry and timeout behavior."""

    def __init__(
        self,
        nutrition_provider: NutritionProvider,
        *,
        vlm: VLMProvider | None = None,
        cache: NutritionCache[NutritionFacts] | None = None,
        attempts: int = 3,
        base_delay: float = 0.25,
        timeout_seconds: float = 20,
    ) -> None:
        self.nutrition_provider = nutrition_provider
        self.vlm = vlm
        self.cache = cache or NutritionCache()
        self.attempts = attempts
        self.base_delay = base_delay
        self.timeout_seconds = timeout_seconds

    async def identify(self, image_path: str) -> list[Ingredient]:
        return await retry_call(
            lambda: identify_ingredients(image_path, vlm=self.vlm),
            attempts=self.attempts,
            base_delay=self.base_delay,
            timeout_seconds=self.timeout_seconds,
        )

    async def nutrition_for(self, ingredient_name: str) -> NutritionFacts:
        cached = await self.cache.get(ingredient_name)
        if cached is not None:
            logger.debug("Nutrition cache hit for %s", ingredient_name)
            return cached
        value = await retry_call(
            lambda: self.nutrition_provider.lookup(ingredient_name),
            attempts=self.attempts,
            base_delay=self.base_delay,
            timeout_seconds=self.timeout_seconds,
        )
        value = normalize_energy_unit(value)
        await self.cache.set(ingredient_name, value)
        return value

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from ai import Ingredient
from ai.providers.base import ProviderError
from foodanalyzer.analyzer import Analyzer
from foodanalyzer.config import Settings
from foodanalyzer.dependencies import build_analyzer
from foodanalyzer.models import AnalysisStatus
from foodanalyzer.offline import OfflineNutritionProvider
from foodanalyzer.services.ai_service import AIService, retry_call
from foodanalyzer.services.cache import NutritionCache
from foodanalyzer.services.nutrition_normalizer import normalize_energy_unit
from foodanalyzer.services.food_insight import FoodInsightService
from foodanalyzer.storage.repository import MemoryRepository


@pytest.mark.asyncio
async def test_offline_pipeline(sample_image):
    source = Path("data/rice_chicken_broccoli.png")
    analyzer = build_analyzer(Settings(offline_mode=True, retry_base_delay=0), MemoryRepository())
    result = await analyzer.analyze(str(source))
    assert result.status == AnalysisStatus.completed
    assert len(result.ingredients) == 3
    assert round(result.totals.kcal) == 509
    assert result.food_insight is not None
    assert result.food_insight.count(".") == 5


@pytest.mark.asyncio
async def test_unknown_meal():
    analyzer = build_analyzer(Settings(offline_mode=True, retry_base_delay=0))
    result = await analyzer.analyze("data/no_meal_blue.png")
    assert result.status == AnalysisStatus.not_recognized
    assert result.totals.kcal == 0


@pytest.mark.asyncio
async def test_cache_normalizes_keys():
    cache = NutritionCache(60)
    facts = OfflineNutritionProvider.DB["broccoli"]
    await cache.set(" Broccoli ", facts)
    assert await cache.get("broccoli") == facts
    await cache.clear()
    assert await cache.get("broccoli") is None


@pytest.mark.asyncio
async def test_retry_recovers():
    calls = 0
    def flaky():
        nonlocal calls
        calls += 1
        if calls < 3:
            raise ProviderError("temporary")
        return 42
    assert await retry_call(flaky, attempts=3, base_delay=0) == 42


@pytest.mark.asyncio
async def test_memory_repository():
    repo = MemoryRepository()
    analyzer = build_analyzer(Settings(offline_mode=True, retry_base_delay=0), repo)
    result = await analyzer.analyze("data/rice_egg.png")
    assert (await repo.get(result.id)).id == result.id
    assert len(await repo.list()) == 1


def test_normalizer_converts_usda_kilojoules():
    facts = OfflineNutritionProvider.DB["grilled chicken breast"].model_copy(
        update={"kcal_per_100g": 1240, "protein_g_per_100g": 23, "fat_g_per_100g": 21.8}
    )
    assert round(normalize_energy_unit(facts).kcal_per_100g) == 296


def test_normalizer_preserves_kcal_values():
    facts = OfflineNutritionProvider.DB["broccoli"]
    assert normalize_energy_unit(facts).kcal_per_100g == 34


def test_offline_food_insight_has_five_sentences():
    summary = FoodInsightService._offline_summary([
        Ingredient(name="rice", estimated_grams=100, confidence=.9)
    ])
    assert FoodInsightService._sentence_count(summary) == 5
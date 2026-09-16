from __future__ import annotations

from ai import get_nutrition_provider

from foodanalyzer.analyzer import Analyzer
from foodanalyzer.config import Settings
from foodanalyzer.offline import OfflineNutritionProvider, OfflineVLM
from foodanalyzer.services.ai_service import AIService
from foodanalyzer.services.cache import NutritionCache
from foodanalyzer.services.food_insight import FoodInsightService
from foodanalyzer.storage.repository import AnalysisRepository


def build_analyzer(settings: Settings, repository: AnalysisRepository | None = None) -> Analyzer:
    nutrition = OfflineNutritionProvider() if settings.offline_mode else get_nutrition_provider()
    vlm = OfflineVLM() if settings.offline_mode else None
    service = AIService(
        nutrition, vlm=vlm, cache=NutritionCache(settings.cache_ttl_seconds),
        attempts=settings.retry_attempts, base_delay=settings.retry_base_delay,
        max_concurrency=settings.max_concurrency,
    )
    insight = FoodInsightService(offline=settings.offline_mode, attempts=settings.retry_attempts,
                                 base_delay=settings.retry_base_delay)
    return Analyzer(service, repository, insight)
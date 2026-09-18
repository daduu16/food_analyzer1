from __future__ import annotations

import asyncio
import logging
from pathlib import Path

from ai import Nutrition, compute_totals
from ai.providers.base import ProviderError

from foodanalyzer.models import AnalysisResponse, AnalysisStatus, IngredientResult
from foodanalyzer.services.ai_service import AIService
from foodanalyzer.services.food_insight import FoodInsightService
from foodanalyzer.storage.repository import AnalysisRepository

logger = logging.getLogger(__name__)


class Analyzer:
    def __init__(self, ai_service: AIService, repository: AnalysisRepository | None = None,
                 insight_service: FoodInsightService | None = None) -> None:
        self.ai_service = ai_service
        self.repository = repository
        self.insight_service = insight_service

    async def analyze(self, image_path: str, *, filename: str | None = None,
                      stored_image_path: str | None = None) -> AnalysisResponse:
        ingredients = await self.ai_service.identify(image_path)
        name = filename or Path(image_path).name
        if not ingredients:
            response = AnalysisResponse(filename=name, image_path=stored_image_path or image_path,
                                        status=AnalysisStatus.not_recognized,
                                        warnings=["Şəkildə yemək müəyyən edilmədi."])
            await self._save(response)
            return response

        outcomes = await asyncio.gather(
            *(self.ai_service.nutrition_for(item.name) for item in ingredients),
            return_exceptions=True,
        )
        facts_by_name = {}
        rows: list[IngredientResult] = []
        warnings: list[str] = []
        for ingredient, outcome in zip(ingredients, outcomes):
            if isinstance(outcome, BaseException):
                message = f"{ingredient.name} üçün qida məlumatı alınmadı"
                logger.warning(message, exc_info=outcome)
                warnings.append(message)
                rows.append(IngredientResult(ingredient=ingredient, error=message))
            else:
                facts_by_name[ingredient.name] = outcome
                rows.append(IngredientResult(
                    ingredient=ingredient,
                    nutrition=outcome.for_grams(ingredient.estimated_grams),
                    nutrition_source=outcome.source,
                ))

        totals = compute_totals(ingredients, facts_by_name)
        status = AnalysisStatus.completed if not warnings else AnalysisStatus.partial
        food_insight = await self.insight_service.describe(ingredients) if self.insight_service else None
        response = AnalysisResponse(
            filename=name, image_path=stored_image_path or image_path, status=status, ingredients=rows, totals=totals,
            total_weight_g=sum(i.estimated_grams for i in ingredients),
            food_insight=food_insight, warnings=warnings,
        )
        await self._save(response)
        return response

    async def _save(self, response: AnalysisResponse) -> None:
        if self.repository:
            await self.repository.save(response)

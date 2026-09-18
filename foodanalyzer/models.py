from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field

from ai import Ingredient, Nutrition


class AnalysisStatus(str, Enum):
    completed = "completed"
    not_recognized = "not_recognized"
    partial = "partial"


class IngredientResult(BaseModel):
    model_config = ConfigDict(extra="forbid")
    ingredient: Ingredient
    nutrition: Nutrition | None = None
    nutrition_source: str | None = None
    error: str | None = None


class AnalysisResponse(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    filename: str
    image_path: str = ""
    status: AnalysisStatus
    ingredients: list[IngredientResult] = Field(default_factory=list)
    totals: Nutrition = Field(default_factory=Nutrition)
    total_weight_g: float = 0
    food_insight: str | None = None
    warnings: list[str] = Field(default_factory=list)


class HealthResponse(BaseModel):
    status: str = "ok"
    service: str
    version: str

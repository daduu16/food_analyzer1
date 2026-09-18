"""Short Azerbaijani descriptions for an identified meal."""
from __future__ import annotations

import re

from ai import Ingredient


class FoodInsightService:
    def __init__(self, *, offline: bool, **_kwargs) -> None:
        self.offline = offline

    async def describe(self, ingredients: list[Ingredient]) -> str | None:
        return self._offline_summary(ingredients) if ingredients else None

    @staticmethod
    def _offline_summary(ingredients: list[Ingredient]) -> str:
        names = ", ".join(item.name for item in ingredients)
        return (f"Bu yemək əsasən {names} ingredientlərindən ibarətdir. "
                "Bu tip kombinasiya müxtəlif ölkələrin ev mətbəxlərində geniş istifadə olunur. "
                "Protein və tərəvəzlər toxluq hissini və qida müxtəlifliyini dəstəkləyə bilər. "
                "Porsiya ölçüsü, yağ, duz və əlavə souslar ümumi enerji dəyərini artıra bilər. "
                "Daha balanslı seçim üçün porsiyanı ehtiyacınıza uyğun saxlayın və tərəvəz payını artırın.")

    @staticmethod
    def _sentence_count(text: str) -> int:
        return len([part for part in re.split(r"[.!?]+", text) if part.strip()])

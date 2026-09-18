"""Normalize USDA energy values without editing the supplied ai package."""
from __future__ import annotations

from ai import NutritionFacts


def normalize_energy_unit(facts: NutritionFacts) -> NutritionFacts:
    macro_kcal = facts.protein_g_per_100g * 4 + facts.carbs_g_per_100g * 4 + facts.fat_g_per_100g * 9
    converted = facts.kcal_per_100g / 4.184
    if macro_kcal > 1 and abs(converted - macro_kcal) < abs(facts.kcal_per_100g - macro_kcal):
        return facts.model_copy(update={"kcal_per_100g": converted})
    return facts

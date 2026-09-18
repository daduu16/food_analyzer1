from __future__ import annotations

import argparse
import asyncio
import os
from pathlib import Path

from foodanalyzer.config import Settings
from foodanalyzer.dependencies import build_analyzer


def render(result) -> str:
    if not result.ingredients:
        return "Şəkildə yemək müəyyən edilmədi."
    lines = [f"Analiz: {result.filename}", "", f"{'Ingredient':28} {'qram':>6} {'kcal':>7} {'protein':>9} {'karb':>7} {'yağ':>7}", "-" * 70]
    for row in result.ingredients:
        n = row.nutrition
        values = (f"{n.kcal:.0f}", f"{n.protein_g:.1f}", f"{n.carbs_g:.1f}", f"{n.fat_g:.1f}") if n else ("—", "—", "—", "—")
        lines.append(f"{row.ingredient.name[:28]:28} {row.ingredient.estimated_grams:6.0f} {values[0]:>7} {values[1]:>9} {values[2]:>7} {values[3]:>7}")
    t = result.totals
    lines.extend(["-" * 70, f"{'TOTAL':28} {result.total_weight_g:6.0f} {t.kcal:7.0f} {t.protein_g:9.1f} {t.carbs_g:7.1f} {t.fat_g:7.1f}"])
    return "\n".join(lines)


async def run(path: Path, offline: bool) -> int:
    if not path.is_file():
        print(f"Fayl tapılmadı: {path}")
        return 2
    settings = Settings(offline_mode=offline)
    result = await build_analyzer(settings).analyze(
        str(path), filename=path.name, stored_image_path=str(path)
    )
    print(render(result))
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(prog="foodanalyzer")
    sub = parser.add_subparsers(dest="command", required=True)
    analyze = sub.add_parser("analyze", help="Yemək şəklini analiz et")
    analyze.add_argument("path", type=Path)
    analyze.add_argument("--offline", action="store_true")
    args = parser.parse_args()
    raise SystemExit(asyncio.run(run(args.path, args.offline)))


if __name__ == "__main__":
    main()

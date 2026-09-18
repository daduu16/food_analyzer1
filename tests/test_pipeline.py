from __future__ import annotations

import asyncio

from foodanalyzer.concurrency.pipeline import lookup_all


def test_pipeline_limits_concurrency_and_keeps_partial_errors():
    active = 0
    maximum = 0

    async def lookup(item: int) -> int:
        nonlocal active, maximum
        active += 1
        maximum = max(maximum, active)
        await asyncio.sleep(0.01)
        active -= 1
        if item == 3:
            raise RuntimeError("USDA down")
        return item * 2

    outcomes = asyncio.run(lookup_all([1, 2, 3, 4], lookup, max_concurrency=2))

    assert maximum <= 2
    assert [outcome.value for outcome in outcomes] == [2, 4, None, 8]
    assert isinstance(outcomes[2].error, RuntimeError)

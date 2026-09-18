from __future__ import annotations

import asyncio

import pytest

from ai.providers.base import ProviderError
from foodanalyzer.services.ai_service import retry_call


def test_retry_recovers_after_temporary_provider_error():
    calls = 0

    def operation():
        nonlocal calls
        calls += 1
        if calls < 3:
            raise ProviderError("temporary")
        return "ok"

    assert asyncio.run(retry_call(operation, attempts=3, base_delay=0, timeout_seconds=1)) == "ok"
    assert calls == 3


def test_retry_raises_clear_provider_error_after_final_attempt():
    def operation():
        raise ProviderError("USDA unavailable")

    with pytest.raises(ProviderError, match="after 2 attempt"):
        asyncio.run(retry_call(operation, attempts=2, base_delay=0, timeout_seconds=1))


def test_retry_times_out():
    async def slow_operation():
        await asyncio.sleep(0.03)
        return "late"

    with pytest.raises(ProviderError, match="unavailable"):
        asyncio.run(retry_call(slow_operation, attempts=1, timeout_seconds=0.001))

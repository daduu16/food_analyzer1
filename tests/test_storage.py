from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import uuid4

import pytest

from foodanalyzer.storage.repository import MemoryRepository, PostgresRepository


@dataclass
class FakeAnalysis:
    id: object
    created_at: datetime
    filename: str = "meal.png"
    image_path: str = "uploads/meal.png"

    def model_copy(self, *, deep: bool):
        return deepcopy(self) if deep else self

    def model_dump_json(self) -> str:
        return '{"filename":"meal.png"}'


@pytest.mark.asyncio
async def test_memory_repository_returns_a_copy_and_supports_history_paging():
    repository = MemoryRepository()
    first = FakeAnalysis(uuid4(), datetime.now(timezone.utc), filename="first.png")
    second = FakeAnalysis(uuid4(), datetime.now(timezone.utc), filename="second.png")

    await repository.save(first)
    await repository.save(second)

    history = await repository.list(limit=1)
    assert history[0].filename == "second.png"
    history[0].filename = "changed.png"
    assert (await repository.get(second.id)).filename == "second.png"
    assert (await repository.list(limit=1, offset=1))[0].filename == "first.png"


class FakePool:
    def __init__(self):
        self.calls = []

    async def execute(self, *args):
        self.calls.append(args)


@pytest.mark.asyncio
async def test_postgres_save_uses_parameterized_jsonb_insert():
    repository = PostgresRepository("postgresql://example")
    pool = FakePool()
    repository.pool = pool
    analysis = FakeAnalysis(uuid4(), datetime.now(timezone.utc))

    await repository.save(analysis)

    query, *arguments = pool.calls[0]
    assert "VALUES($1, $2, $3, $4, $5::jsonb)" in query
    assert arguments[-1] == '{"filename":"meal.png"}'


@pytest.mark.asyncio
async def test_postgres_operations_require_connection():
    with pytest.raises(RuntimeError, match="not connected"):
        await PostgresRepository("postgresql://example").list()

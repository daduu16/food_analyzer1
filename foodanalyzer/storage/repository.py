from __future__ import annotations

import abc
import asyncio
from typing import TYPE_CHECKING, Any
from uuid import UUID

if TYPE_CHECKING:
    from foodanalyzer.models import AnalysisResponse


class AnalysisRepository(abc.ABC):
    """Contract used by the analyzer to persist completed analyses."""

    @abc.abstractmethod
    async def save(self, analysis: AnalysisResponse) -> None: ...

    @abc.abstractmethod
    async def list(self, limit: int = 20, offset: int = 0) -> list[AnalysisResponse]: ...

    @abc.abstractmethod
    async def get(self, analysis_id: UUID) -> AnalysisResponse | None: ...


class MemoryRepository(AnalysisRepository):
    """Thread-safe development fallback when DATABASE_URL is not configured."""

    def __init__(self) -> None:
        self._items: list[Any] = []
        self._lock = asyncio.Lock()

    async def save(self, analysis: AnalysisResponse) -> None:
        async with self._lock:
            self._items.insert(0, analysis.model_copy(deep=True))

    async def list(self, limit: int = 20, offset: int = 0) -> list[AnalysisResponse]:
        async with self._lock:
            return [item.model_copy(deep=True) for item in self._items[offset : offset + limit]]

    async def get(self, analysis_id: UUID) -> AnalysisResponse | None:
        async with self._lock:
            item = next((item for item in self._items if item.id == analysis_id), None)
            return item.model_copy(deep=True) if item else None


class PostgresRepository(AnalysisRepository):
    """asyncpg connection-pool backed analysis-history repository."""

    def __init__(self, database_url: str) -> None:
        self.database_url = database_url
        self.pool: Any | None = None

    async def connect(self) -> None:
        import asyncpg

        self.pool = await asyncpg.create_pool(self.database_url, min_size=1, max_size=5)
        async with self.pool.acquire() as connection:
            await connection.execute(
                """
                CREATE TABLE IF NOT EXISTS analyses (
                    id UUID PRIMARY KEY,
                    created_at TIMESTAMPTZ NOT NULL,
                    filename TEXT NOT NULL,
                    image_path TEXT NOT NULL DEFAULT '',
                    payload JSONB NOT NULL
                )
                """
            )
            # Supports databases created before image uploads were persisted.
            await connection.execute(
                "ALTER TABLE analyses ADD COLUMN IF NOT EXISTS image_path TEXT NOT NULL DEFAULT ''"
            )

    async def close(self) -> None:
        if self.pool is not None:
            await self.pool.close()
            self.pool = None

    def _connected_pool(self) -> Any:
        if self.pool is None:
            raise RuntimeError("PostgreSQL repository is not connected")
        return self.pool

    async def save(self, analysis: AnalysisResponse) -> None:
        await self._connected_pool().execute(
            """
            INSERT INTO analyses(id, created_at, filename, image_path, payload)
            VALUES($1, $2, $3, $4, $5::jsonb)
            """,
            analysis.id,
            analysis.created_at,
            analysis.filename,
            analysis.image_path,
            analysis.model_dump_json(),
        )

    async def list(self, limit: int = 20, offset: int = 0) -> list[AnalysisResponse]:
        rows = await self._connected_pool().fetch(
            "SELECT payload FROM analyses ORDER BY created_at DESC LIMIT $1 OFFSET $2", limit, offset
        )
        return [self._from_json(row["payload"]) for row in rows]

    async def get(self, analysis_id: UUID) -> AnalysisResponse | None:
        row = await self._connected_pool().fetchrow("SELECT payload FROM analyses WHERE id = $1", analysis_id)
        return self._from_json(row["payload"]) if row else None

    @staticmethod
    def _from_json(payload: str) -> AnalysisResponse:
        from foodanalyzer.models import AnalysisResponse

        return AnalysisResponse.model_validate_json(payload)

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path
from uuid import UUID
from uuid import uuid4

from fastapi import FastAPI, File, HTTPException, Query, Request, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from ai.providers.base import ProviderError
from foodanalyzer import __version__
from foodanalyzer.config import get_settings
from foodanalyzer.dependencies import build_analyzer
from foodanalyzer.models import AnalysisResponse, HealthResponse
from foodanalyzer.storage.repository import MemoryRepository, PostgresRepository
from foodanalyzer.validation import read_valid_image

settings = get_settings()
logging.basicConfig(level=getattr(logging, settings.log_level.upper(), logging.INFO),
                    format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    upload_dir = Path(settings.upload_dir)
    upload_dir.mkdir(parents=True, exist_ok=True)
    app.state.upload_dir = upload_dir
    if settings.database_url:
        repository = PostgresRepository(settings.database_url)
        await repository.connect()
    else:
        repository = MemoryRepository()
        logger.warning("DATABASE_URL yoxdur; tarixçə yaddaşda saxlanılır")
    app.state.repository = repository
    app.state.analyzer = build_analyzer(settings, repository)
    yield
    if isinstance(repository, PostgresRepository):
        await repository.close()


app = FastAPI(title=settings.app_name, version=__version__, lifespan=lifespan)
static_dir = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=static_dir), name="static")


@app.exception_handler(ProviderError)
async def provider_error_handler(_request: Request, exc: ProviderError):
    logger.exception("Upstream provider failed", exc_info=exc)
    return JSONResponse(status_code=503, content={
        "error": "provider_unavailable",
        "detail": "AI və ya qida məlumatı xidməti müvəqqəti əlçatan deyil.",
    })


@app.get("/", include_in_schema=False)
async def index():
    return FileResponse(static_dir / "index.html", headers={"Cache-Control": "no-store"})


@app.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse(service=settings.app_name, version=__version__)


@app.post("/analyze", response_model=AnalysisResponse)
async def analyze(request: Request, image: UploadFile = File(...)) -> AnalysisResponse:
    data, suffix = await read_valid_image(image, settings.max_upload_bytes)
    safe_name = Path(image.filename or f"upload{suffix}").name
    safe_stem = "".join(char if char.isalnum() or char in "-_" else "_" for char in Path(safe_name).stem)
    stored_path = request.app.state.upload_dir / f"{uuid4().hex}_{safe_stem}{suffix}"
    stored_path.write_bytes(data)
    return await request.app.state.analyzer.analyze(
        str(stored_path), filename=safe_name, stored_image_path=str(stored_path)
    )


@app.get("/history", response_model=list[AnalysisResponse])
async def history(request: Request, limit: int = Query(20, ge=1, le=100),
                  offset: int = Query(0, ge=0)):
    return await request.app.state.repository.list(limit, offset)


@app.get("/history/{analysis_id}", response_model=AnalysisResponse)
async def history_item(analysis_id: UUID, request: Request):
    result = await request.app.state.repository.get(analysis_id)
    if result is None:
        raise HTTPException(404, "Analiz tapılmadı.")
    return result

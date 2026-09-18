from __future__ import annotations

import importlib
from pathlib import Path

from fastapi.testclient import TestClient


def make_client(monkeypatch):
    monkeypatch.setenv("OFFLINE_MODE", "true")
    # Override the developer's local .env database URL so API tests remain
    # fully offline and use the memory repository.
    monkeypatch.setenv("DATABASE_URL", "")
    from foodanalyzer.config import get_settings
    get_settings.cache_clear()
    import foodanalyzer.api as api
    importlib.reload(api)
    return TestClient(api.app)


def test_health_and_frontend(monkeypatch):
    with make_client(monkeypatch) as client:
        assert client.get("/health").json()["status"] == "ok"
        page = client.get("/")
        assert "FoodLens AI" in page.text
        assert "YEMƏK HAQQINDA" in page.text
        assert page.headers["cache-control"] == "no-store"


def test_analyze_and_history(monkeypatch):
    with make_client(monkeypatch) as client:
        data = open("data/rice_chicken_broccoli.png", "rb").read()
        response = client.post("/analyze", files={"image": ("rice_chicken_broccoli.png", data, "image/png")})
        assert response.status_code == 200
        payload = response.json()
        assert payload["status"] == "completed"
        assert Path(payload["image_path"]).is_file()
        assert len(payload["ingredients"]) == 3
        history = client.get("/history").json()
        assert history[0]["id"] == payload["id"]
        assert client.get(f"/history/{payload['id']}").status_code == 200


def test_upload_validation(monkeypatch):
    with make_client(monkeypatch) as client:
        unsupported = client.post("/analyze", files={"image": ("meal.txt", b"hello", "text/plain")})
        fake_png = client.post("/analyze", files={"image": ("meal.png", b"not png", "image/png")})
        assert unsupported.status_code == 415
        assert fake_png.status_code == 400


def test_missing_history(monkeypatch):
    with make_client(monkeypatch) as client:
        assert client.get("/history/00000000-0000-0000-0000-000000000001").status_code == 404

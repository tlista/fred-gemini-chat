"""Tests for the FastAPI endpoints."""

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_health_check_endpoint():
    """Verify health endpoint returns 200 and version metadata."""
    res = client.get("/api/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "healthy"
    assert "version" in data


def test_curated_indicators_endpoint():
    """Verify curated indicators endpoint returns popular series."""
    res = client.get("/api/fred/curated")
    assert res.status_code == 200
    series = res.json()
    assert len(series) >= 5
    ids = [s["id"] for s in series]
    assert "CPIAUCSL" in ids
    assert "FEDFUNDS" in ids


def test_fred_search_endpoint():
    """Verify FRED search endpoint returns results."""
    res = client.get("/api/fred/search", params={"q": "GDP"})
    assert res.status_code == 200
    data = res.json()
    assert data["count"] > 0
    assert any("GDP" in r["id"] for r in data["results"])


def test_fred_series_endpoint():
    """Verify observation endpoint returns historical data."""
    res = client.get("/api/fred/series/UNRATE")
    assert res.status_code == 200
    data = res.json()
    assert data["series_id"] == "UNRATE"
    assert len(data["observations"]) > 0


def test_chat_endpoint_demo():
    """Verify POST /api/chat works end-to-end with demo fallback."""
    payload = {
        "message": "What is the 30 year mortgage rate compared to the Fed rate?",
        "history": []
    }
    res = client.post("/api/chat", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert "reply" in data
    assert len(data["reply"]) > 0
    assert len(data["tool_calls"]) > 0
    assert len(data["charts"]) > 0


def test_list_models_endpoint():
    """Verify GET /api/gemini/models returns fallback or confirmed models."""
    res = client.get("/api/gemini/models")
    assert res.status_code == 200
    data = res.json()
    assert "models" in data
    assert data["count"] > 0
    ids = [m["id"] for m in data["models"]]
    assert any("flash" in mid for mid in ids)

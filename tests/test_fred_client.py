"""Tests for the FRED API client."""

import asyncio
from app.fred_client import FredClient, POPULAR_SERIES


def test_curated_series_definitions():
    """Verify curated series contain required fields."""
    assert "CPIAUCSL" in POPULAR_SERIES
    assert "FEDFUNDS" in POPULAR_SERIES
    assert "GDP" in POPULAR_SERIES
    assert "UNRATE" in POPULAR_SERIES

    for sid, info in POPULAR_SERIES.items():
        assert info["id"] == sid
        assert "title" in info
        assert "units" in info
        assert "frequency" in info


def test_fred_search_curated_fallback():
    """Verify search returns relevant series when offline or without API key."""
    async def _run():
        client = FredClient()
        results = await client.search_series("inflation", limit=5)
        assert len(results) > 0
        ids = [r["id"] for r in results]
        assert any(term in ids for term in ["CPIAUCSL", "CPILFESL", "PCEPILFE"])

        results_un = await client.search_series("unemployment", limit=3)
        assert any(r["id"] == "UNRATE" for r in results_un)

    asyncio.run(_run())


def test_fred_observations_fallback():
    """Verify observation retrieval returns valid dates and numerical values."""
    async def _run():
        client = FredClient()
        data = await client.get_series_observations("FEDFUNDS", limit=10)

        assert data["series_id"] == "FEDFUNDS"
        assert "observations" in data
        assert len(data["observations"]) > 0
        
        first = data["observations"][0]
        assert "date" in first
        assert isinstance(first["value"], float)
        assert data["units"] == "Percent"

    asyncio.run(_run())


def test_fred_metadata_retrieval():
    """Verify metadata retrieval returns title and units."""
    async def _run():
        client = FredClient()
        meta = await client.get_series_metadata("MORTGAGE30US")

        assert meta["id"] == "MORTGAGE30US"
        assert "Mortgage" in meta["title"]
        assert meta["units"] == "Percent"

    asyncio.run(_run())

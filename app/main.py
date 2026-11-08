"""FastAPI backend application for FRED + Gemini Chat."""

import logging
from pathlib import Path
from typing import Optional
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.fred_client import FredClient, POPULAR_SERIES
from app.gemini_agent import FredGeminiAgent, get_available_gemini_models
from app.models import (
    ChatRequest,
    ChatResponse,
    TestKeysRequest,
    TestKeysResponse,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Conversational macroeconomic chat assistant connecting Google Gemini to the St. Louis Fed FRED API."
)

# Enable CORS for external app integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

STATIC_DIR = Path(__file__).resolve().parent / "static"


@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "version": settings.VERSION,
        "default_model": settings.DEFAULT_GEMINI_MODEL,
        "has_gemini_env_key": bool(settings.GEMINI_API_KEY),
        "has_fred_env_key": bool(settings.FRED_API_KEY)
    }


@app.get("/api/gemini/models")
async def list_available_models(gemini_api_key: Optional[str] = Query(None)):
    """Fetch confirmed live Gemini models available for the provided key."""
    models = await get_available_gemini_models(api_key=gemini_api_key)
    return {"count": len(models), "models": models}


@app.post("/api/chat", response_model=ChatResponse)
async def chat_endpoint(req: ChatRequest):
    """Primary chat endpoint connecting user prompts to Gemini and FRED."""
    try:
        agent = FredGeminiAgent(
            gemini_api_key=req.gemini_api_key,
            fred_api_key=req.fred_api_key,
            model_name=req.model,
            temperature=req.temperature
        )
        response = await agent.chat(message=req.message, history=req.history)
        return response
    except Exception as e:
        logger.exception("Chat endpoint error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/fred/curated")
async def get_curated_indicators():
    """Return list of popular curated macroeconomic indicators."""
    return list(POPULAR_SERIES.values())


@app.get("/api/fred/search")
async def search_fred(
    q: str = Query(..., description="Search keyword"),
    limit: int = Query(10, ge=1, le=50),
    fred_api_key: Optional[str] = Query(None)
):
    """Direct search endpoint for FRED series."""
    client = FredClient(api_key=fred_api_key)
    results = await client.search_series(search_text=q, limit=limit)
    return {"query": q, "count": len(results), "results": results}


@app.get("/api/fred/series/{series_id}")
async def get_series_data(
    series_id: str,
    start: Optional[str] = Query(None, description="Start date YYYY-MM-DD"),
    end: Optional[str] = Query(None, description="End date YYYY-MM-DD"),
    units: Optional[str] = Query(None, description="Units transformation: lin, chg, pch, pc1"),
    limit: int = Query(100, ge=1, le=500),
    fred_api_key: Optional[str] = Query(None)
):
    """Direct observation endpoint for a specific FRED series."""
    client = FredClient(api_key=fred_api_key)
    data = await client.get_series_observations(
        series_id=series_id,
        observation_start=start,
        observation_end=end,
        units=units,
        limit=limit
    )
    return data


@app.post("/api/test-keys", response_model=TestKeysResponse)
async def test_api_keys(req: TestKeysRequest):
    """Verify Gemini and FRED API keys."""
    # Test FRED Key
    fred_client = FredClient(api_key=req.fred_api_key)
    fred_res = await fred_client.validate_key()

    # Test Gemini Key
    gemini_key = (req.gemini_api_key or settings.GEMINI_API_KEY).strip()
    if not gemini_key:
        gemini_valid = False
        gemini_msg = "Gemini API key is not configured"
    else:
        try:
            from google import genai
            client = genai.Client(api_key=gemini_key)
            # Lightweight test generation
            res = client.models.generate_content(
                model="gemini-2.5-flash",
                contents="Ping"
            )
            gemini_valid = bool(res.text)
            gemini_msg = "Gemini API key verified successfully"
        except Exception as e:
            gemini_valid = False
            gemini_msg = f"Gemini error: {str(e)}"

    return TestKeysResponse(
        gemini_valid=gemini_valid,
        gemini_message=gemini_msg,
        fred_valid=fred_res["valid"],
        fred_message=fred_res["message"]
    )


# Serve frontend static assets
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

    @app.get("/")
    async def serve_index():
        return FileResponse(str(STATIC_DIR / "index.html"))

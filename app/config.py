"""Application configuration and settings."""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env file from project root if present
load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

class Settings:
    PROJECT_NAME: str = "FRED + Gemini Economic Assistant"
    VERSION: str = "1.0.0"
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))
    
    # API Keys (can also be supplied per-request from UI)
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    FRED_API_KEY: str = os.getenv("FRED_API_KEY", "")
    
    # Defaults
    DEFAULT_GEMINI_MODEL: str = os.getenv("DEFAULT_GEMINI_MODEL", "gemini-2.5-flash")
    FRED_BASE_URL: str = "https://api.stlouisfed.org/fred"

settings = Settings()

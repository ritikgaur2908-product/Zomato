"""Application configuration loaded from environment variables."""

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

PROJECT_ROOT = Path(__file__).resolve().parent.parent

DATASET_NAME: str = os.getenv(
    "DATASET_NAME", "ManikaSaini/zomato-restaurant-recommendation"
)
DATASET_CACHE_PATH: Path = Path(
    os.getenv("DATASET_CACHE_PATH", "data/cache/restaurants.parquet")
)
if not DATASET_CACHE_PATH.is_absolute():
    DATASET_CACHE_PATH = PROJECT_ROOT / DATASET_CACHE_PATH

BUDGET_LOW_MAX: int = int(os.getenv("BUDGET_LOW_MAX", "500"))
BUDGET_MEDIUM_MAX: int = int(os.getenv("BUDGET_MEDIUM_MAX", "1500"))

DEFAULT_TOP_N: int = int(os.getenv("DEFAULT_TOP_N", "5"))
MAX_TOP_N: int = int(os.getenv("MAX_TOP_N", "20"))
CANDIDATE_LIMIT: int = int(os.getenv("CANDIDATE_LIMIT", "20"))
MAX_EXTRAS_LENGTH: int = int(os.getenv("MAX_EXTRAS_LENGTH", "500"))
EXTRAS_MATCH_MODE: str = os.getenv("EXTRAS_MATCH_MODE", "and")  # "and" | "or"
INCLUDE_UNKNOWN_BUDGET: bool = os.getenv("INCLUDE_UNKNOWN_BUDGET", "false").lower() == "true"

LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "groq")
LLM_MODEL: str = os.getenv("LLM_MODEL", "llama-3.3-70b-versatile")
LLM_API_KEY: str = os.getenv("LLM_API_KEY", "")
LLM_MAX_TOKENS: int = int(os.getenv("LLM_MAX_TOKENS", "2048"))
LLM_TEMPERATURE: float = float(os.getenv("LLM_TEMPERATURE", "0.2"))
LLM_MAX_PARSE_RETRIES: int = int(os.getenv("LLM_MAX_PARSE_RETRIES", "1"))

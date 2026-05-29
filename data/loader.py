"""Load Zomato dataset from Hugging Face or local cache."""

from __future__ import annotations

import json
import logging
import math
from pathlib import Path
from typing import Any

import pandas as pd

from app.config import DATASET_CACHE_PATH, DATASET_NAME, PROJECT_ROOT
from data.models import PreprocessStats, Restaurant
from data.preprocessor import preprocess_rows

logger = logging.getLogger(__name__)


def clean_nan_values(record: dict[str, Any]) -> dict[str, Any]:
    """
    Clean NaN values from a record before Pydantic validation.
    
    Converts pandas/numpy NaN values to None for optional numeric fields.
    This is a safety layer before Pydantic validation.
    
    Args:
        record: Dictionary record from pandas DataFrame
        
    Returns:
        Cleaned dictionary with NaN values converted to None
    """
    cleaned = {}
    for key, value in record.items():
        if isinstance(value, float) and math.isnan(value):
            cleaned[key] = None
        else:
            cleaned[key] = value
    return cleaned


class DatasetLoadError(Exception):
    """Raised when the dataset cannot be loaded."""


class DatasetLoader:
    """Fetches raw rows from Hugging Face and returns preprocessed restaurants."""

    def __init__(
        self,
        dataset_name: str = DATASET_NAME,
        cache_path: Path = DATASET_CACHE_PATH,
    ) -> None:
        self.dataset_name = dataset_name
        self.cache_path = cache_path

    def load(self, force_refresh: bool = False) -> tuple[list[Restaurant], PreprocessStats]:
        """
        Load restaurants from cache if available, otherwise Hugging Face.

        Returns:
            Tuple of (restaurants, preprocess_stats).
        """
        if not force_refresh and self._cache_exists():
            restaurants = self._load_from_cache()
            stats = PreprocessStats(
                input_rows=len(restaurants),
                valid_rows=len(restaurants),
                dropped_rows=0,
            )
            logger.info("Loaded %d restaurants from cache: %s", len(restaurants), self.cache_path)
            return restaurants, stats

        raw_rows = self._load_from_huggingface()
        restaurants, stats = preprocess_rows(raw_rows)

        if not restaurants:
            raise DatasetLoadError(
                f"No valid restaurants after preprocessing {stats.input_rows} rows. "
                f"Drop reasons: {stats.drop_reasons}"
            )

        self._save_to_cache(restaurants)
        return restaurants, stats

    def _cache_exists(self) -> bool:
        return self.cache_path.exists() and self.cache_path.stat().st_size > 0

    def _load_from_cache(self) -> list[Restaurant]:
        try:
            df = pd.read_parquet(self.cache_path)
        except Exception as exc:
            logger.warning("Corrupt cache at %s: %s. Will re-download.", self.cache_path, exc)
            self.cache_path.unlink(missing_ok=True)
            raise DatasetLoadError(f"Cache file corrupt: {self.cache_path}") from exc

        records = df.to_dict(orient="records")
        restaurants = []
        skipped_count = 0
        
        for r in records:
            try:
                # Clean NaN values before validation
                cleaned = clean_nan_values(r)
                restaurant = Restaurant.model_validate(cleaned)
                restaurants.append(restaurant)
            except Exception as exc:
                skipped_count += 1
                logger.debug("Skipping invalid record: %s. Error: %s", r.get("name", "unknown"), exc)
        
        if skipped_count > 0:
            logger.warning("Skipped %d invalid records during cache load", skipped_count)
        
        return restaurants

    def _save_to_cache(self, restaurants: list[Restaurant]) -> None:
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        rows = [r.model_dump(mode="json") for r in restaurants]
        df = pd.DataFrame(rows)
        df.to_parquet(self.cache_path, index=False)
        logger.info("Saved %d restaurants to cache: %s", len(restaurants), self.cache_path)

    def _load_from_huggingface(self) -> list[dict[str, Any]]:
        try:
            from datasets import load_dataset
        except ImportError as exc:
            raise DatasetLoadError(
                "Install dependencies: pip install -r requirements.txt"
            ) from exc

        logger.info("Downloading dataset from Hugging Face: %s", self.dataset_name)
        try:
            dataset = load_dataset(self.dataset_name, split="train")
        except Exception as exc:
            raise DatasetLoadError(
                f"Could not load dataset '{self.dataset_name}'. "
                "Check your internet connection or use cached data at "
                f"{self.cache_path}."
            ) from exc

        return [dict(row) for row in dataset]

    def load_raw_sample(self, n: int = 5) -> list[dict[str, Any]]:
        """Load first n raw rows (for exploration script)."""
        rows = self._load_from_huggingface()
        return rows[:n]


def export_stats_json(stats: PreprocessStats, path: Path | None = None) -> Path:
    """Write preprocess stats to JSON for debugging."""
    out = path or PROJECT_ROOT / "data" / "cache" / "preprocess_stats.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(stats.model_dump_json(indent=2), encoding="utf-8")
    return out

"""Domain models for the restaurant recommendation system."""

import math
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, field_validator


class BudgetTier(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    UNKNOWN = "unknown"


class Restaurant(BaseModel):
    id: str
    name: str
    location: str
    city: str
    cuisines: list[str] = Field(default_factory=list)
    rating: float = Field(ge=0.0, le=5.0)
    cost_for_two: int | None = None
    budget_tier: BudgetTier = BudgetTier.UNKNOWN
    raw: dict[str, Any] = Field(default_factory=dict)

    model_config = {"frozen": True}

    @field_validator("cost_for_two", mode="before")
    @classmethod
    def clean_nan_cost(cls, v: Any) -> Any:
        """Convert NaN values to None for cost_for_two field."""
        if isinstance(v, float) and math.isnan(v):
            return None
        return v

    @field_validator("rating", mode="before")
    @classmethod
    def clean_nan_rating(cls, v: Any) -> Any:
        """Convert NaN values to None for rating field (will fail validation if None)."""
        if isinstance(v, float) and math.isnan(v):
            raise ValueError("Rating cannot be NaN")
        return v


class PreprocessStats(BaseModel):
    input_rows: int = 0
    valid_rows: int = 0
    dropped_rows: int = 0
    duplicate_rows_removed: int = 0
    drop_reasons: dict[str, int] = Field(default_factory=dict)


class UserPreferences(BaseModel):
    """User search criteria for restaurant recommendations."""

    location: str
    budget: BudgetTier
    cuisine: list[str] = Field(default_factory=list)
    min_rating: float = 0.0
    extras: list[str] = Field(default_factory=list)
    top_n: int = 5

    model_config = {"frozen": True}

    @field_validator("location")
    @classmethod
    def location_not_empty(cls, v: str) -> str:
        text = v.strip()
        if not text:
            raise ValueError("Location is required.")
        return text

    @field_validator("budget")
    @classmethod
    def budget_must_be_tier(cls, v: BudgetTier) -> BudgetTier:
        if v == BudgetTier.UNKNOWN:
            raise ValueError("Budget must be one of: low, medium, high.")
        return v

    @field_validator("min_rating")
    @classmethod
    def clamp_min_rating(cls, v: float) -> float:
        return max(0.0, min(5.0, float(v)))

    @field_validator("top_n")
    @classmethod
    def normalize_top_n(cls, v: int) -> int:
        from app.config import DEFAULT_TOP_N, MAX_TOP_N

        if v <= 0:
            return DEFAULT_TOP_N
        return min(int(v), MAX_TOP_N)

    @field_validator("cuisine", mode="before")
    @classmethod
    def normalize_cuisine(cls, v: str | list[str] | None) -> list[str]:
        if v is None:
            return []
        if isinstance(v, list):
            return [str(c).strip().title() for c in v if str(c).strip()]
        text = str(v).strip()
        if not text or text == "*":
            return []
        parts = [c.strip().title() for c in text.split(",") if c.strip()]
        return parts if len(parts) > 1 else [text.title()]

    @field_validator("extras", mode="before")
    @classmethod
    def normalize_extras(cls, v: list[str] | None) -> list[str]:
        if not v:
            return []
        return [str(item).strip() for item in v if str(item).strip()]

    def cuisine_list(self) -> list[str]:
        return self.cuisine


class FilterStats(BaseModel):
    input_count: int = 0
    output_count: int = 0
    capped_to: int | None = None
    filters_applied: dict[str, Any] = Field(default_factory=dict)
    relaxed_filters: list[str] = Field(default_factory=list)
    suggestions: list[str] = Field(default_factory=list)


class RankedRecommendation(BaseModel):
    """A restaurant ranked and explained by the LLM layer."""

    restaurant: Restaurant
    rank: int = Field(ge=1)
    explanation: str
    match_highlights: list[str] = Field(default_factory=list)


class RecommendationMetadata(BaseModel):
    """Diagnostics and flags for a recommendation response."""

    total_candidates: int = 0
    filters_applied: dict[str, Any] = Field(default_factory=dict)
    ai_explanations_available: bool = True
    parse_used_fallback: bool = False
    llm_attempts: int = 1
    stripped_invalid_ids: int = 0


class RecommendationResponse(BaseModel):
    """Full recommendation payload returned by the orchestrator."""

    recommendations: list[RankedRecommendation] = Field(default_factory=list)
    summary: str | None = None
    metadata: RecommendationMetadata = Field(default_factory=RecommendationMetadata)
    message: str | None = None
    filter_stats: FilterStats | None = None

"""Orchestrates the end-to-end recommendation pipeline."""

from __future__ import annotations

import logging
import time
from typing import Any

from data.loader import DatasetLoadError
from data.models import (
    BudgetTier,
    FilterStats,
    RecommendationMetadata,
    RecommendationResponse,
    Restaurant,
    RankedRecommendation,
    UserPreferences,
)
from data.repository import RestaurantRepository
from filtering.engine import FilterEngine
from llm.client import LLMClient, LLMClientError
from llm.service import LLMRecommendationService

logger = logging.getLogger(__name__)


class RecommendationOrchestrator:
    """
    Phase 4 entry point: wires data, filtering, and LLM into a single pipeline.

    Handles empty candidates, LLM failures, and dataset load errors gracefully.
    """

    def __init__(
        self,
        repository: RestaurantRepository | None = None,
        filter_engine: FilterEngine | None = None,
        llm_service: LLMRecommendationService | None = None,
    ) -> None:
        """
        Initialize the orchestrator with optional injected dependencies.

        Args:
            repository: Restaurant data source (auto-loads if None)
            filter_engine: Filtering logic (uses defaults if None)
            llm_service: LLM ranking service (uses default client if None)
        """
        try:
            self.repository = repository or RestaurantRepository(auto_load=True)
        except DatasetLoadError as exc:
            # Task 4.4: Dataset load failure - fail fast with clear error
            logger.error("Failed to load dataset: %s", exc)
            raise RuntimeError(
                "Dataset load failed. Please check your internet connection, "
                "dataset configuration, and cache path."
            ) from exc

        self.filter_engine = filter_engine or FilterEngine()
        self.llm_service = llm_service or LLMRecommendationService()

    def recommend(self, preferences: UserPreferences) -> RecommendationResponse:
        """
        Generate restaurant recommendations based on user preferences.

        Pipeline:
        1. Load all restaurants from repository
        2. Apply deterministic filters
        3. If no candidates, return empty response with suggestions
        4. Call LLM to rank and explain candidates
        5. If LLM fails, use rating-sorted fallback
        6. Return top N recommendations with metadata

        Args:
            preferences: User search criteria

        Returns:
            RecommendationResponse with ranked recommendations and metadata
        """
        # Task 4.5: Log filter stats, candidate count, LLM latency
        start_time = time.time()

        # Step 1: Get all restaurants
        all_restaurants = self.repository.get_all()
        logger.info("Pipeline started with %d total restaurants", len(all_restaurants))

        # Step 2: Apply filters
        candidates, filter_stats = self.filter_engine.apply(preferences, all_restaurants)
        logger.info(
            "Filter output: %d candidates from %d input (location=%r, budget=%s, cuisine=%s)",
            len(candidates),
            filter_stats.input_count,
            preferences.location,
            preferences.budget.value,
            preferences.cuisine_list(),
        )

        # Task 4.2: Empty candidates branch
        if not candidates:
            logger.info("No candidates found - returning empty response")
            return RecommendationResponse(
                recommendations=[],
                message=self._build_empty_message(filter_stats),
                metadata=RecommendationMetadata(
                    total_candidates=0,
                    ai_explanations_available=False,
                    filters_applied=filter_stats.filters_applied,
                ),
                filter_stats=filter_stats,
            )

        # Step 3: Call LLM to rank and explain
        try:
            llm_start = time.time()
            parse_result, metadata = self.llm_service.rank_and_explain(
                preferences, candidates, filter_stats=filter_stats
            )
            llm_latency = time.time() - llm_start
            logger.info("LLM call completed in %.2fs", llm_latency)

            # Build final response
            recommendations = parse_result.recommendations[: preferences.top_n]
            metadata.total_candidates = len(candidates)

            return RecommendationResponse(
                recommendations=recommendations,
                summary=parse_result.summary,
                metadata=metadata,
                filter_stats=filter_stats,
            )

        # Task 4.3: LLM failure branch
        except LLMClientError as exc:
            logger.warning("LLM call failed: %s - using rating fallback", exc)
            return self._build_fallback_response(
                preferences, candidates, filter_stats, str(exc)
            )
        except Exception as exc:
            logger.error("Unexpected error during LLM call: %s", exc, exc_info=True)
            return self._build_fallback_response(
                preferences, candidates, filter_stats, f"Unexpected error: {exc}"
            )

    def _build_empty_message(self, filter_stats: FilterStats) -> str:
        """Build a helpful message when no candidates match."""
        if filter_stats.suggestions:
            suggestion_text = "\n".join(f"• {s}" for s in filter_stats.suggestions)
            return f"No restaurants match your criteria. Suggestions:\n{suggestion_text}"
        return "No restaurants match your criteria. Try adjusting your filters."

    def _build_fallback_response(
        self,
        preferences: UserPreferences,
        candidates: list[Restaurant],
        filter_stats: FilterStats,
        error_message: str,
    ) -> RecommendationResponse:
        """
        Build a rating-sorted fallback response when LLM fails.

        Task 4.3: Rating-sorted fallback + metadata.ai_explanations_available = false
        """
        # Sort by rating descending
        sorted_candidates = sorted(candidates, key=lambda r: (-r.rating, r.name.lower()))
        top_n = min(len(sorted_candidates), preferences.top_n)

        # Build generic recommendations
        recommendations = []
        for rank, restaurant in enumerate(sorted_candidates[:top_n], start=1):
            recommendations.append(
                RankedRecommendation(
                    restaurant=restaurant,
                    rank=rank,
                    explanation=f"Highly rated ({restaurant.rating}/5.0) {', '.join(restaurant.cuisines[:2])} restaurant in your area.",
                    match_highlights=["high rating"],
                )
            )

        return RecommendationResponse(
            recommendations=recommendations,
            message=f"AI ranking unavailable ({error_message}). Showing top-rated matches instead.",
            metadata=RecommendationMetadata(
                total_candidates=len(candidates),
                ai_explanations_available=False,
                filters_applied=filter_stats.filters_applied,
            ),
            filter_stats=filter_stats,
        )

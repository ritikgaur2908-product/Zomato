"""Orchestrates prompt → LLM → parse with retry on malformed JSON."""

from __future__ import annotations

import logging

from app.config import LLM_MAX_PARSE_RETRIES
from data.models import FilterStats, RecommendationMetadata, Restaurant, UserPreferences
from llm.client import LLMClient, LLMClientError, get_llm_client
from llm.parser import ParseResult, ResponseParser
from llm.prompts import PromptBuilder

logger = logging.getLogger(__name__)


class LLMRecommendationService:
    """
    Phase 3 entry point: rank and explain filtered candidates via LLM.

    Retries once when JSON parsing fails; then uses rating fallback.
    """

    def __init__(self, client: LLMClient | None = None) -> None:
        self._client = client

    @property
    def client(self) -> LLMClient:
        if self._client is None:
            self._client = get_llm_client()
        return self._client

    def rank_and_explain(
        self,
        preferences: UserPreferences,
        candidates: list[Restaurant],
        *,
        filter_stats: FilterStats | None = None,
    ) -> tuple[ParseResult, RecommendationMetadata]:
        """
        Call LLM to rank candidates; return parse result and metadata.

        Raises LLMClientError if the provider call fails (caller may fallback).
        """
        if not candidates:
            meta = RecommendationMetadata(
                total_candidates=0,
                ai_explanations_available=False,
            )
            return ParseResult(recommendations=[]), meta

        messages = PromptBuilder.build(preferences, candidates)
        max_attempts = 1 + LLM_MAX_PARSE_RETRIES
        last_result: ParseResult | None = None

        for attempt in range(1, max_attempts + 1):
            raw = self.client.complete(messages)
            last_result = ResponseParser.parse(
                raw,
                candidates,
                preferences.top_n,
                preferences,
            )

            if not last_result.used_fallback:
                meta = self._build_metadata(
                    candidates,
                    last_result,
                    attempt,
                    filter_stats,
                )
                return last_result, meta

            if attempt < max_attempts:
                logger.info("LLM parse failed; retrying (%d/%d)", attempt, max_attempts)
                messages = [*messages, PromptBuilder.build_retry_message()]

        assert last_result is not None
        meta = self._build_metadata(
            candidates,
            last_result,
            max_attempts,
            filter_stats,
            ai_available=False,
        )
        return last_result, meta

    @staticmethod
    def _build_metadata(
        candidates: list[Restaurant],
        result: ParseResult,
        attempts: int,
        filter_stats: FilterStats | None,
        *,
        ai_available: bool | None = None,
    ) -> RecommendationMetadata:
        filters_applied: dict = {}
        if filter_stats and filter_stats.filters_applied:
            filters_applied = dict(filter_stats.filters_applied)

        explanations = ai_available
        if explanations is None:
            explanations = not result.used_fallback

        return RecommendationMetadata(
            total_candidates=len(candidates),
            filters_applied=filters_applied,
            ai_explanations_available=explanations,
            parse_used_fallback=result.used_fallback,
            llm_attempts=attempts,
            stripped_invalid_ids=result.stripped_invalid_ids,
        )

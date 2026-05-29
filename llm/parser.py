"""Parse and validate structured LLM responses."""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from pydantic import BaseModel, Field

from data.models import RankedRecommendation, Restaurant, UserPreferences

logger = logging.getLogger(__name__)

FALLBACK_EXPLANATION = (
    "Top-rated option from your filtered results matching {location} "
    "and {budget} budget (AI explanation unavailable)."
)


class ParseResult(BaseModel):
    """Outcome of parsing an LLM response."""

    recommendations: list[RankedRecommendation] = Field(default_factory=list)
    summary: str | None = None
    used_fallback: bool = False
    stripped_invalid_ids: int = 0


class ResponseParser:
    """Validates LLM JSON and merges with dataset-backed restaurants."""

    @classmethod
    def parse(
        cls,
        raw: str,
        candidates: list[Restaurant],
        top_n: int,
        preferences: UserPreferences | None = None,
    ) -> ParseResult:
        """
        Parse LLM output into ranked recommendations.

        On JSON failure or empty valid results, falls back to rating-sorted top N.
        """
        by_id = {r.id: r for r in candidates}
        valid_ids = set(by_id)

        try:
            data = cls._extract_json(raw)
            summary = data.get("summary")
            if summary is not None:
                summary = str(summary).strip() or None

            items = data.get("recommendations") or []
            if not isinstance(items, list):
                raise ValueError("recommendations must be a list")

            ranked, stripped = cls._build_ranked(items, by_id, valid_ids)
            if ranked:
                ranked.sort(key=lambda x: x.rank)
                return ParseResult(
                    recommendations=ranked[:top_n],
                    summary=summary,
                    used_fallback=False,
                    stripped_invalid_ids=stripped,
                )

            logger.warning("LLM returned no valid restaurant ids; using fallback.")
        except (json.JSONDecodeError, ValueError, TypeError, KeyError) as exc:
            logger.warning("Failed to parse LLM JSON: %s", exc)

        return cls._fallback(candidates, top_n, preferences)

    @staticmethod
    def _extract_json(raw: str) -> dict[str, Any]:
        text = raw.strip()
        if text.startswith("```"):
            text = re.sub(r"^```(?:json)?\s*", "", text)
            text = re.sub(r"\s*```$", "", text)

        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            match = re.search(r"\{[\s\S]*\}", text)
            if not match:
                raise
            data = json.loads(match.group())

        if not isinstance(data, dict):
            raise ValueError("LLM output must be a JSON object")
        return data

    @classmethod
    def _build_ranked(
        cls,
        items: list[Any],
        by_id: dict[str, Restaurant],
        valid_ids: set[str],
    ) -> tuple[list[RankedRecommendation], int]:
        ranked: list[RankedRecommendation] = []
        stripped = 0
        seen_ids: set[str] = set()

        for item in items:
            if not isinstance(item, dict):
                continue
            rid = str(item.get("restaurant_id", "")).strip()
            if not rid or rid not in valid_ids:
                if rid:
                    stripped += 1
                continue
            if rid in seen_ids:
                continue
            seen_ids.add(rid)

            try:
                rank = int(item.get("rank", len(ranked) + 1))
            except (TypeError, ValueError):
                rank = len(ranked) + 1

            explanation = str(item.get("explanation", "")).strip()
            if not explanation:
                explanation = "Matches your search criteria."

            highlights = item.get("match_highlights") or []
            if not isinstance(highlights, list):
                highlights = []
            highlights = [str(h).strip() for h in highlights if str(h).strip()]

            ranked.append(
                RankedRecommendation(
                    restaurant=by_id[rid],
                    rank=max(1, rank),
                    explanation=explanation,
                    match_highlights=highlights,
                )
            )

        return ranked, stripped

    @classmethod
    def _fallback(
        cls,
        candidates: list[Restaurant],
        top_n: int,
        preferences: UserPreferences | None,
    ) -> ParseResult:
        sorted_candidates = sorted(
            candidates,
            key=lambda r: r.rating,
            reverse=True,
        )[:top_n]

        location = preferences.location if preferences else "your area"
        budget = preferences.budget.value if preferences else "selected"

        recommendations = [
            RankedRecommendation(
                restaurant=r,
                rank=i,
                explanation=FALLBACK_EXPLANATION.format(location=location, budget=budget),
                match_highlights=["high rating"],
            )
            for i, r in enumerate(sorted_candidates, start=1)
        ]

        return ParseResult(
            recommendations=recommendations,
            summary=None,
            used_fallback=True,
            stripped_invalid_ids=0,
        )

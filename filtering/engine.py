"""Deterministic restaurant filtering based on user preferences."""

from __future__ import annotations

import logging
from typing import Any

from app.config import (
    CANDIDATE_LIMIT,
    EXTRAS_MATCH_MODE,
    INCLUDE_UNKNOWN_BUDGET,
    MAX_EXTRAS_LENGTH,
)
from data.models import BudgetTier, FilterStats, Restaurant, UserPreferences

logger = logging.getLogger(__name__)

_BUDGET_ORDER = [BudgetTier.LOW, BudgetTier.MEDIUM, BudgetTier.HIGH]


class FilterEngine:
    """Apply hard filters before LLM ranking."""

    def __init__(
        self,
        candidate_limit: int = CANDIDATE_LIMIT,
        include_unknown_budget: bool = INCLUDE_UNKNOWN_BUDGET,
        extras_match_mode: str = EXTRAS_MATCH_MODE,
    ) -> None:
        self.candidate_limit = candidate_limit
        self.include_unknown_budget = include_unknown_budget
        self.extras_match_mode = extras_match_mode.lower()

    def apply(
        self,
        preferences: UserPreferences,
        restaurants: list[Restaurant],
    ) -> tuple[list[Restaurant], FilterStats]:
        """
        Filter restaurants and return capped candidates with stats.

        Does not call the LLM. Returns empty list when nothing matches.
        """
        input_count = len(restaurants)
        filtered = list(restaurants)

        filtered = self._filter_location(preferences, filtered)
        filtered = self._filter_cuisine(preferences, filtered)
        filtered = self._filter_rating(preferences, filtered)
        filtered = self._filter_budget(preferences, filtered)
        filtered = self._filter_extras(preferences, filtered)

        filtered = self._select_candidates(filtered)

        stats = FilterStats(
            input_count=input_count,
            output_count=len(filtered),
            capped_to=self.candidate_limit if len(filtered) == self.candidate_limit else None,
            filters_applied=self._filters_applied_dict(preferences),
        )

        if not filtered:
            stats.suggestions = self.suggest_relaxations(preferences, restaurants)
            logger.info(
                "No candidates for location=%r cuisine=%s budget=%s min_rating=%s",
                preferences.location,
                preferences.cuisine_list(),
                preferences.budget.value,
                preferences.min_rating,
            )

        return filtered, stats

    def suggest_relaxations(
        self,
        preferences: UserPreferences,
        restaurants: list[Restaurant],
    ) -> list[str]:
        """
        Suggest ways to widen filters when no matches (FLT-16).

        Never auto-relaxes; only returns human-readable hints.
        """
        suggestions: list[str] = []

        loc_only = self._filter_location(preferences, restaurants)
        if preferences.cuisine_list() and len(loc_only) > 0:
            without_cuisine = [
                r
                for r in loc_only
                if self._matches_rating(r, preferences.min_rating)
                and self._matches_budget(r, preferences.budget)
            ]
            if without_cuisine:
                suggestions.append(
                    f"Try a different cuisine — {len(without_cuisine)} places match "
                    "your location and budget."
                )

        if preferences.min_rating > 0:
            lower = preferences.min_rating - 0.5
            count = sum(
                1
                for r in restaurants
                if self._matches_location(r, preferences.location)
                and self._matches_cuisine(r, preferences.cuisine_list())
                and self._matches_budget(r, preferences.budget)
                and r.rating >= lower
            )
            if count > 0:
                suggestions.append(
                    f"Lower minimum rating to {lower:.1f} ({count} matches)."
                )

        adjacent = self._adjacent_budget_suggestion(preferences, restaurants)
        if adjacent:
            suggestions.append(adjacent)

        if not suggestions:
            suggestions.append(
                "Try a different location or cuisine from the available options."
            )

        return suggestions

    def _filter_location(
        self, preferences: UserPreferences, restaurants: list[Restaurant]
    ) -> list[Restaurant]:
        return [r for r in restaurants if self._matches_location(r, preferences.location)]

    def _filter_cuisine(
        self, preferences: UserPreferences, restaurants: list[Restaurant]
    ) -> list[Restaurant]:
        cuisines = preferences.cuisine_list()
        if not cuisines:
            return restaurants
        return [r for r in restaurants if self._matches_cuisine(r, cuisines)]

    def _filter_rating(
        self, preferences: UserPreferences, restaurants: list[Restaurant]
    ) -> list[Restaurant]:
        return [
            r for r in restaurants if self._matches_rating(r, preferences.min_rating)
        ]

    def _filter_budget(
        self, preferences: UserPreferences, restaurants: list[Restaurant]
    ) -> list[Restaurant]:
        return [r for r in restaurants if self._matches_budget(r, preferences.budget)]

    def _filter_extras(
        self, preferences: UserPreferences, restaurants: list[Restaurant]
    ) -> list[Restaurant]:
        keywords = self._normalize_extras_keywords(preferences.extras)
        if not keywords:
            return restaurants
        return [r for r in restaurants if self._matches_extras(r, keywords)]

    def _select_candidates(self, restaurants: list[Restaurant]) -> list[Restaurant]:
        """Sort by rating desc, then name; cap to candidate_limit (FLT-13, FLT-14)."""
        sorted_rows = sorted(
            restaurants,
            key=lambda r: (-r.rating, r.name.lower()),
        )
        return sorted_rows[: self.candidate_limit]

    @staticmethod
    def _matches_location(restaurant: Restaurant, query: str) -> bool:
        q = query.strip().lower()
        if not q:
            return False
        loc = restaurant.location.lower()
        city = restaurant.city.lower()
        return (
            q in loc
            or loc in q
            or q in city
            or city in q
            or loc == q
            or city == q
        )

    @staticmethod
    def _matches_cuisine(restaurant: Restaurant, user_cuisines: list[str]) -> bool:
        if not user_cuisines:
            return True
        restaurant_cuisines = {c.lower() for c in restaurant.cuisines}
        for uc in user_cuisines:
            u = uc.lower()
            if any(u in rc or rc in u for rc in restaurant_cuisines):
                return True
        return False

    @staticmethod
    def _matches_rating(restaurant: Restaurant, min_rating: float) -> bool:
        return restaurant.rating >= min_rating

    def _matches_budget(self, restaurant: Restaurant, budget: BudgetTier) -> bool:
        if restaurant.budget_tier == BudgetTier.UNKNOWN:
            return self.include_unknown_budget
        return restaurant.budget_tier == budget

    def _matches_extras(self, restaurant: Restaurant, keywords: list[str]) -> bool:
        haystack = self._extras_search_text(restaurant)
        if self.extras_match_mode == "or":
            return any(kw in haystack for kw in keywords)
        return all(kw in haystack for kw in keywords)

    @staticmethod
    def _extras_search_text(restaurant: Restaurant) -> str:
        parts = [restaurant.name]
        raw = restaurant.raw or {}
        for key in ("dish_liked", "rest_type", "address", "listed_in(type)"):
            val = raw.get(key)
            if val:
                parts.append(str(val))
        return " ".join(parts).lower()

    @staticmethod
    def _normalize_extras_keywords(extras: list[str]) -> list[str]:
        keywords: list[str] = []
        for item in extras:
            text = item.strip().lower()[:MAX_EXTRAS_LENGTH]
            if text:
                keywords.append(text)
        return keywords

    def _adjacent_budget_suggestion(
        self, preferences: UserPreferences, restaurants: list[Restaurant]
    ) -> str | None:
        for alt in _BUDGET_ORDER:
            if alt == preferences.budget:
                continue
            count = sum(
                1
                for r in restaurants
                if self._matches_location(r, preferences.location)
                and self._matches_cuisine(r, preferences.cuisine_list())
                and self._matches_rating(r, preferences.min_rating)
                and self._matches_budget(r, alt)
            )
            if count > 0:
                return f"Try budget '{alt.value}' instead ({count} matches)."
        return None

    @staticmethod
    def _filters_applied_dict(preferences: UserPreferences) -> dict[str, Any]:
        return {
            "location": preferences.location,
            "budget": preferences.budget.value,
            "cuisine": preferences.cuisine_list() or "any",
            "min_rating": preferences.min_rating,
            "extras": preferences.extras or "none",
        }

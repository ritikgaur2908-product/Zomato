"""Tests for LLM response parsing and fallback."""

import json

import pytest

from data.models import BudgetTier, Restaurant, UserPreferences
from llm.parser import ResponseParser


def _restaurant(**kwargs) -> Restaurant:
    defaults = dict(
        id="r1",
        name="Italian Bistro",
        location="Banashankari",
        city="Bangalore",
        cuisines=["Italian"],
        rating=4.5,
        cost_for_two=800,
        budget_tier=BudgetTier.MEDIUM,
    )
    defaults.update(kwargs)
    return Restaurant(**defaults)


def _prefs(**kwargs) -> UserPreferences:
    defaults = dict(
        location="Bangalore",
        budget=BudgetTier.MEDIUM,
        cuisine="Italian",
        min_rating=4.0,
        top_n=2,
    )
    defaults.update(kwargs)
    return UserPreferences(**defaults)


class TestResponseParser:
    def test_parses_valid_json(self):
        candidates = [
            _restaurant(id="r1", rating=4.5),
            _restaurant(id="r2", name="Other", rating=4.0),
        ]
        raw = json.dumps(
            {
                "summary": "Great Italian picks.",
                "recommendations": [
                    {
                        "restaurant_id": "r2",
                        "rank": 1,
                        "explanation": "Matches your Italian preference in Bangalore.",
                        "match_highlights": ["Italian"],
                    },
                    {
                        "restaurant_id": "r1",
                        "rank": 2,
                        "explanation": "Solid medium-budget option with 4.5 rating.",
                        "match_highlights": ["medium budget"],
                    },
                ],
            }
        )

        result = ResponseParser.parse(raw, candidates, top_n=2, preferences=_prefs())

        assert not result.used_fallback
        assert result.summary == "Great Italian picks."
        assert len(result.recommendations) == 2
        assert result.recommendations[0].restaurant.id == "r2"
        assert result.recommendations[0].rank == 1
        assert "Italian" in result.recommendations[0].explanation

    def test_strips_unknown_restaurant_ids(self):
        candidates = [_restaurant(id="r1")]
        raw = json.dumps(
            {
                "recommendations": [
                    {
                        "restaurant_id": "fake-id",
                        "rank": 1,
                        "explanation": "Should be dropped.",
                    },
                    {
                        "restaurant_id": "r1",
                        "rank": 2,
                        "explanation": "Valid pick for your Bangalore search.",
                    },
                ]
            }
        )

        result = ResponseParser.parse(raw, candidates, top_n=5, preferences=_prefs())

        assert not result.used_fallback
        assert result.stripped_invalid_ids == 1
        assert len(result.recommendations) == 1
        assert result.recommendations[0].restaurant.id == "r1"

    def test_malformed_json_uses_fallback(self):
        candidates = [
            _restaurant(id="r1", rating=3.0),
            _restaurant(id="r2", rating=4.8),
        ]

        result = ResponseParser.parse(
            "not json at all",
            candidates,
            top_n=2,
            preferences=_prefs(),
        )

        assert result.used_fallback
        assert len(result.recommendations) == 2
        assert result.recommendations[0].restaurant.id == "r2"
        assert "AI explanation unavailable" in result.recommendations[0].explanation

    def test_parses_json_inside_markdown_fence(self):
        candidates = [_restaurant(id="r1")]
        raw = """```json
{"recommendations": [{"restaurant_id": "r1", "rank": 1, "explanation": "Fits Italian cuisine in Bangalore."}]}
```"""

        result = ResponseParser.parse(raw, candidates, top_n=1, preferences=_prefs())

        assert not result.used_fallback
        assert result.recommendations[0].restaurant.name == "Italian Bistro"

    def test_empty_valid_recommendations_triggers_fallback(self):
        candidates = [_restaurant(id="r1", rating=4.0)]
        raw = json.dumps({"recommendations": []})

        result = ResponseParser.parse(raw, candidates, top_n=1, preferences=_prefs())

        assert result.used_fallback
        assert len(result.recommendations) == 1

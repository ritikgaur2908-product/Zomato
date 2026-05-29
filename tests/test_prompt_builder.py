"""Tests for LLM prompt assembly."""

import json

from data.models import BudgetTier, Restaurant, UserPreferences
from llm.prompts import PromptBuilder, SYSTEM_PROMPT


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


class TestPromptBuilder:
    def test_build_returns_system_and_user_messages(self):
        prefs = UserPreferences(
            location="Bangalore",
            budget=BudgetTier.MEDIUM,
            cuisine="Italian",
            min_rating=4.0,
            top_n=3,
        )
        candidates = [_restaurant(id="r1"), _restaurant(id="r2", name="Pizza Hub")]

        messages = PromptBuilder.build(prefs, candidates)

        assert len(messages) == 2
        assert messages[0]["role"] == "system"
        assert messages[1]["role"] == "user"
        assert "ONLY valid JSON" in messages[0]["content"]
        assert SYSTEM_PROMPT in messages[0]["content"]

    def test_user_message_contains_preferences_and_candidates(self):
        prefs = UserPreferences(
            location="Delhi",
            budget=BudgetTier.HIGH,
            cuisine=["Italian", "Pizza"],
            min_rating=4.2,
            extras=["family-friendly"],
            top_n=5,
        )
        candidates = [_restaurant(id="abc123")]

        payload = json.loads(PromptBuilder.build(prefs, candidates)[1]["content"])

        assert payload["user_preferences"]["location"] == "Delhi"
        assert payload["user_preferences"]["budget"] == "high"
        assert "Italian" in payload["user_preferences"]["cuisine"]
        assert payload["user_preferences"]["min_rating"] == 4.2
        assert payload["user_preferences"]["extras"] == ["family-friendly"]

        assert len(payload["candidates"]) == 1
        assert payload["candidates"][0]["id"] == "abc123"
        assert payload["candidates"][0]["rating"] == 4.5
        assert "name" in payload["candidates"][0]

    def test_grounding_rules_in_system_prompt(self):
        assert "Only use restaurant ids" in SYSTEM_PROMPT
        assert "Do not change factual fields" in SYSTEM_PROMPT

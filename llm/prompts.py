"""Prompt templates and builder for grounded LLM ranking."""

from __future__ import annotations

import json
from typing import Any

from data.models import Restaurant, UserPreferences

ChatMessage = dict[str, str]

SYSTEM_PROMPT = """You are a restaurant recommendation assistant for a Zomato-style discovery app.

Your job is to RE-RANK and EXPLAIN restaurants from a provided candidate list only.

STRICT RULES:
1. Only use restaurant ids present in the "candidates" array. Never invent restaurants or ids.
2. Do not change factual fields (rating, cost, cuisines) — explanations may reference them only.
3. Rank from 1 (best match) upward. Include at most the number of candidates given.
4. Each explanation must mention at least one user preference (location, budget, cuisine, min_rating, or extras).
5. Return ONLY valid JSON matching this schema (no markdown, no prose outside JSON):

{
  "summary": "optional one-sentence overview of the picks",
  "recommendations": [
    {
      "restaurant_id": "<id from candidates>",
      "rank": 1,
      "explanation": "Why this matches the user...",
      "match_highlights": ["Italian", "high rating"]
    }
  ]
}
"""


class PromptBuilder:
    """Builds chat messages for the LLM from preferences and candidates."""

    @staticmethod
    def build(
        preferences: UserPreferences,
        candidates: list[Restaurant],
    ) -> list[ChatMessage]:
        """Return system + user messages for chat completion APIs."""
        prefs_payload = _serialize_preferences(preferences)
        candidate_payload = [_compact_restaurant(r) for r in candidates]

        user_content = json.dumps(
            {
                "user_preferences": prefs_payload,
                "candidates": candidate_payload,
                "instructions": (
                    f"Rank up to {preferences.top_n} best matches and return JSON only."
                ),
            },
            indent=2,
        )

        return [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ]

    @staticmethod
    def build_retry_message() -> ChatMessage:
        """Extra user turn when the model returned invalid JSON."""
        return {
            "role": "user",
            "content": (
                "Your previous response was not valid JSON. "
                "Reply again with ONLY the JSON object matching the schema. "
                "Use only restaurant_id values from the candidates list."
            ),
        }


def _serialize_preferences(preferences: UserPreferences) -> dict[str, Any]:
    return {
        "location": preferences.location,
        "budget": preferences.budget.value,
        "cuisine": preferences.cuisine_list(),
        "min_rating": preferences.min_rating,
        "extras": preferences.extras,
        "top_n": preferences.top_n,
    }


def _compact_restaurant(restaurant: Restaurant) -> dict[str, Any]:
    return {
        "id": restaurant.id,
        "name": restaurant.name,
        "cuisines": restaurant.cuisines,
        "rating": restaurant.rating,
        "cost_for_two": restaurant.cost_for_two,
        "budget_tier": restaurant.budget_tier.value,
        "location": restaurant.location,
        "city": restaurant.city,
    }

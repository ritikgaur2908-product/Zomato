"""Tests for LLM service with MockLLMClient (no network)."""

import json

from data.models import BudgetTier, Restaurant, UserPreferences
from llm.client import MockLLMClient
from llm.service import LLMRecommendationService


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


class TestLLMRecommendationService:
    def test_mock_client_ranks_without_network(self):
        candidates = [
            _restaurant(id="r1", rating=4.0),
            _restaurant(id="r2", name="Top Spot", rating=4.9),
        ]
        service = LLMRecommendationService(client=MockLLMClient())

        result, meta = service.rank_and_explain(_prefs(), candidates)

        assert not result.used_fallback
        assert meta.ai_explanations_available
        assert len(result.recommendations) >= 1
        assert result.recommendations[0].restaurant.id == "r2"

    def test_retries_on_malformed_json_then_succeeds(self):
        candidates = [_restaurant(id="r1")]
        client = MockLLMClient(malformed=True)
        service = LLMRecommendationService(client=client)

        result, meta = service.rank_and_explain(_prefs(top_n=1), candidates)

        assert client.call_count == 2
        assert not result.used_fallback
        assert meta.llm_attempts == 2

    def test_fallback_after_repeated_parse_failure(self):
        candidates = [_restaurant(id="r1", rating=4.2)]

        class AlwaysBadClient(MockLLMClient):
            def complete(self, messages):
                self.call_count += 1
                return "still not json"

        client = AlwaysBadClient()
        service = LLMRecommendationService(client=client)

        result, meta = service.rank_and_explain(_prefs(top_n=1), candidates)

        assert result.used_fallback
        assert not meta.ai_explanations_available
        assert meta.parse_used_fallback
        assert client.call_count == 2

    def test_empty_candidates_skips_llm(self):
        service = LLMRecommendationService(client=MockLLMClient())

        result, meta = service.rank_and_explain(_prefs(), [])

        assert result.recommendations == []
        assert meta.total_candidates == 0
        assert not meta.ai_explanations_available

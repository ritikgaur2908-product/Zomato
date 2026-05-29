"""Integration tests for the RecommendationOrchestrator."""

from data.models import BudgetTier, Restaurant, UserPreferences
from filtering.engine import FilterEngine
from llm.client import MockLLMClient
from llm.service import LLMRecommendationService

from app.orchestrator import RecommendationOrchestrator
from data.repository import RestaurantRepository


def _restaurant(**kwargs) -> Restaurant:
    defaults = dict(
        id="r1",
        name="Test Restaurant",
        location="Test Location",
        city="Test City",
        cuisines=["Italian"],
        rating=4.5,
        cost_for_two=800,
        budget_tier=BudgetTier.MEDIUM,
    )
    defaults.update(kwargs)
    return Restaurant(**defaults)


def _prefs(**kwargs) -> UserPreferences:
    defaults = dict(
        location="Test Location",
        budget=BudgetTier.MEDIUM,
        cuisine=["Italian"],
        min_rating=4.0,
        top_n=2,
    )
    defaults.update(kwargs)
    return UserPreferences(**defaults)


class TestRecommendationOrchestrator:
    def test_end_to_end_with_mock_llm(self):
        """Test full pipeline with mock LLM (no network)."""
        # Setup test data
        restaurants = [
            _restaurant(id="r1", name="Italian Bistro", rating=4.8),
            _restaurant(id="r2", name="Pizza Place", rating=4.2),
            _restaurant(id="r3", name="Pasta House", rating=4.5),
        ]

        # Create dependencies
        repository = RestaurantRepository(restaurants=restaurants, auto_load=False)
        filter_engine = FilterEngine(candidate_limit=20)
        llm_service = LLMRecommendationService(client=MockLLMClient())

        # Create orchestrator
        orchestrator = RecommendationOrchestrator(
            repository=repository,
            filter_engine=filter_engine,
            llm_service=llm_service,
        )

        # Get recommendations
        response = orchestrator.recommend(_prefs())

        # Verify response
        assert response.recommendations is not None
        assert len(response.recommendations) > 0
        assert response.metadata.ai_explanations_available is True
        assert response.metadata.total_candidates == 3
        assert response.filter_stats is not None
        assert response.filter_stats.output_count == 3

    def test_empty_candidates_returns_empty_response(self):
        """Test that empty candidates returns appropriate empty response."""
        # Setup test data with no matching restaurants
        restaurants = [
            _restaurant(id="r1", name="Chinese Place", location="Different City", cuisines=["Chinese"]),
        ]

        repository = RestaurantRepository(restaurants=restaurants, auto_load=False)
        filter_engine = FilterEngine(candidate_limit=20)
        llm_service = LLMRecommendationService(client=MockLLMClient())

        orchestrator = RecommendationOrchestrator(
            repository=repository,
            filter_engine=filter_engine,
            llm_service=llm_service,
        )

        # Request with preferences that won't match
        response = orchestrator.recommend(
            UserPreferences(
                location="Test Location",
                budget=BudgetTier.MEDIUM,
                cuisine=["Italian"],
                min_rating=4.0,
                top_n=2,
            )
        )

        # Verify empty response
        assert len(response.recommendations) == 0
        assert response.message is not None
        assert response.metadata.ai_explanations_available is False
        assert response.metadata.total_candidates == 0

    def test_llm_failure_uses_fallback(self):
        """Test that LLM failure triggers rating-sorted fallback."""
        restaurants = [
            _restaurant(id="r1", name="Low Rated", rating=3.5),
            _restaurant(id="r2", name="High Rated", rating=4.8),
            _restaurant(id="r3", name="Medium Rated", rating=4.2),
        ]

        repository = RestaurantRepository(restaurants=restaurants, auto_load=False)
        filter_engine = FilterEngine(candidate_limit=20)

        # Create a mock client that always fails
        class FailingMockClient(MockLLMClient):
            def complete(self, messages):
                raise Exception("Simulated LLM failure")

        llm_service = LLMRecommendationService(client=FailingMockClient())

        orchestrator = RecommendationOrchestrator(
            repository=repository,
            filter_engine=filter_engine,
            llm_service=llm_service,
        )

        response = orchestrator.recommend(_prefs())

        # Verify fallback response
        assert len(response.recommendations) > 0
        assert response.metadata.ai_explanations_available is False
        assert response.message is not None
        # Verify rating-sorted order (highest first)
        ratings = [r.restaurant.rating for r in response.recommendations]
        assert ratings == sorted(ratings, reverse=True)

    def test_respects_top_n_limit(self):
        """Test that orchestrator respects the top_n parameter."""
        restaurants = [
            _restaurant(id=f"r{i}", name=f"Restaurant {i}", rating=4.0 + i * 0.1)
            for i in range(10)
        ]

        repository = RestaurantRepository(restaurants=restaurants, auto_load=False)
        filter_engine = FilterEngine(candidate_limit=20)
        llm_service = LLMRecommendationService(client=MockLLMClient())

        orchestrator = RecommendationOrchestrator(
            repository=repository,
            filter_engine=filter_engine,
            llm_service=llm_service,
        )

        # Request only 3 recommendations
        response = orchestrator.recommend(
            UserPreferences(
                location="Test Location",
                budget=BudgetTier.MEDIUM,
                cuisine=["Italian"],
                min_rating=4.0,
                top_n=3,
            )
        )

        # Verify limit is respected
        assert len(response.recommendations) <= 3

    def test_filter_stats_included_in_response(self):
        """Test that filter stats are properly included in response."""
        restaurants = [
            _restaurant(id="r1", name="Match 1", rating=4.5),
            _restaurant(id="r2", name="Match 2", rating=4.2),
        ]

        repository = RestaurantRepository(restaurants=restaurants, auto_load=False)
        filter_engine = FilterEngine(candidate_limit=20)
        llm_service = LLMRecommendationService(client=MockLLMClient())

        orchestrator = RecommendationOrchestrator(
            repository=repository,
            filter_engine=filter_engine,
            llm_service=llm_service,
        )

        response = orchestrator.recommend(_prefs())

        # Verify filter stats
        assert response.filter_stats is not None
        assert response.filter_stats.input_count == 2
        assert response.filter_stats.output_count == 2
        assert response.metadata.filters_applied is not None

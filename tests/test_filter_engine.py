"""Unit tests for FilterEngine."""

import pytest

from data.models import BudgetTier, Restaurant, UserPreferences
from filtering.engine import FilterEngine


def _restaurant(**kwargs) -> Restaurant:
    defaults = dict(
        id="r1",
        name="Test Place",
        location="Banashankari",
        city="Bangalore",
        cuisines=["Italian", "Pizza"],
        rating=4.2,
        cost_for_two=800,
        budget_tier=BudgetTier.MEDIUM,
        raw={"dish_liked": "family friendly pasta"},
    )
    defaults.update(kwargs)
    return Restaurant(**defaults)


def _prefs(**kwargs) -> UserPreferences:
    defaults = dict(
        location="Bangalore",
        budget=BudgetTier.MEDIUM,
        cuisine="Italian",
        min_rating=4.0,
    )
    defaults.update(kwargs)
    return UserPreferences(**defaults)


@pytest.fixture
def sample_restaurants() -> list[Restaurant]:
    return [
        _restaurant(
            id="r1",
            name="Italian Bistro",
            location="Banashankari",
            city="Bangalore",
            cuisines=["Italian"],
            rating=4.5,
            budget_tier=BudgetTier.MEDIUM,
        ),
        _restaurant(
            id="r2",
            name="Chinese Wok",
            location="Koramangala",
            city="Bangalore",
            cuisines=["Chinese"],
            rating=4.8,
            budget_tier=BudgetTier.MEDIUM,
        ),
        _restaurant(
            id="r3",
            name="Budget Italian",
            location="Indiranagar",
            city="Bangalore",
            cuisines=["Italian"],
            rating=3.5,
            budget_tier=BudgetTier.LOW,
        ),
        _restaurant(
            id="r4",
            name="Fine Italian",
            location="Banashankari",
            city="Bangalore",
            cuisines=["Italian"],
            rating=4.0,
            budget_tier=BudgetTier.HIGH,
            cost_for_two=2000,
        ),
        _restaurant(
            id="r5",
            name="Delhi Darbar",
            location="Connaught Place",
            city="Delhi",
            cuisines=["North Indian"],
            rating=4.6,
            budget_tier=BudgetTier.MEDIUM,
        ),
        _restaurant(
            id="r6",
            name="Unknown Cost Cafe",
            location="Banashankari",
            city="Bangalore",
            cuisines=["Italian"],
            rating=4.1,
            budget_tier=BudgetTier.UNKNOWN,
            cost_for_two=None,
        ),
    ]


class TestLocationFilter:
    def test_case_insensitive_city(self, sample_restaurants):
        engine = FilterEngine()
        prefs = _prefs(location="bangalore", cuisine=[])
        candidates, _ = engine.apply(prefs, sample_restaurants)
        assert all(r.city.lower() == "bangalore" or "bangalore" in r.city.lower() for r in candidates)
        assert len(candidates) >= 3

    def test_delhi_location(self, sample_restaurants):
        engine = FilterEngine()
        prefs = _prefs(location="Delhi", cuisine=[], min_rating=0)
        candidates, stats = engine.apply(prefs, sample_restaurants)
        assert len(candidates) == 1
        assert candidates[0].name == "Delhi Darbar"
        assert stats.output_count == 1


class TestCuisineFilter:
    def test_italian_overlap(self, sample_restaurants):
        engine = FilterEngine()
        prefs = _prefs(location="Bangalore", cuisine="Italian", min_rating=0, budget=BudgetTier.LOW)
        candidates, _ = engine.apply(prefs, sample_restaurants)
        assert all("Italian" in r.cuisines or any("italian" in c.lower() for c in r.cuisines) for r in candidates)

    def test_multiple_cuisines(self, sample_restaurants):
        engine = FilterEngine()
        prefs = _prefs(location="Bangalore", cuisine=["Italian", "Chinese"], min_rating=0, budget=BudgetTier.MEDIUM)
        candidates, _ = engine.apply(prefs, sample_restaurants)
        names = {c.name for c in candidates}
        assert "Italian Bistro" in names
        assert "Chinese Wok" in names

    def test_any_cuisine_when_empty(self, sample_restaurants):
        engine = FilterEngine()
        prefs = _prefs(location="Delhi", cuisine=[], min_rating=0)
        candidates, _ = engine.apply(prefs, sample_restaurants)
        assert len(candidates) == 1


class TestRatingFilter:
    def test_min_rating_inclusive(self, sample_restaurants):
        engine = FilterEngine()
        prefs = _prefs(location="Bangalore", cuisine="Italian", min_rating=4.0, budget=BudgetTier.MEDIUM)
        candidates, _ = engine.apply(prefs, sample_restaurants)
        assert all(r.rating >= 4.0 for r in candidates)
        assert any(r.name == "Fine Italian" for r in candidates)

    def test_excludes_below_min_rating(self, sample_restaurants):
        engine = FilterEngine()
        prefs = _prefs(location="Bangalore", cuisine="Italian", min_rating=4.0, budget=BudgetTier.LOW)
        candidates, _ = engine.apply(prefs, sample_restaurants)
        assert not any(r.name == "Budget Italian" for r in candidates)


class TestBudgetFilter:
    def test_medium_budget_only(self, sample_restaurants):
        engine = FilterEngine()
        prefs = _prefs(location="Bangalore", cuisine="Italian", min_rating=4.0, budget=BudgetTier.MEDIUM)
        candidates, _ = engine.apply(prefs, sample_restaurants)
        assert all(r.budget_tier == BudgetTier.MEDIUM for r in candidates)

    def test_unknown_budget_excluded_by_default(self, sample_restaurants):
        engine = FilterEngine(include_unknown_budget=False)
        prefs = _prefs(location="Banashankari", cuisine="Italian", min_rating=4.0, budget=BudgetTier.MEDIUM)
        candidates, _ = engine.apply(prefs, sample_restaurants)
        assert not any(r.name == "Unknown Cost Cafe" for r in candidates)

    def test_unknown_budget_included_when_flag_set(self, sample_restaurants):
        engine = FilterEngine(include_unknown_budget=True)
        prefs = _prefs(location="Banashankari", cuisine="Italian", min_rating=4.0, budget=BudgetTier.MEDIUM)
        candidates, _ = engine.apply(prefs, sample_restaurants)
        assert any(r.name == "Unknown Cost Cafe" for r in candidates)


class TestExtrasFilter:
    def test_extras_and_mode(self, sample_restaurants):
        engine = FilterEngine(extras_match_mode="and")
        r = _restaurant(
            id="x1",
            name="Family Cafe",
            location="Bangalore",
            city="Bangalore",
            cuisines=["Italian"],
            rating=4.5,
            budget_tier=BudgetTier.MEDIUM,
            raw={"dish_liked": "family friendly quick service"},
        )
        prefs = _prefs(
            location="Bangalore",
            cuisine=[],
            min_rating=0,
            extras=["family", "quick"],
        )
        candidates, _ = engine.apply(prefs, [r])
        assert len(candidates) == 1

    def test_extras_or_mode(self):
        engine = FilterEngine(extras_match_mode="or")
        r = _restaurant(raw={"dish_liked": "family friendly"})
        prefs = _prefs(location="Bangalore", cuisine=[], min_rating=0, extras=["quick", "delivery"])
        candidates, _ = engine.apply(prefs, [r])
        assert len(candidates) == 0


class TestCandidateCap:
    def test_caps_to_limit(self):
        engine = FilterEngine(candidate_limit=3)
        many = [
            _restaurant(
                id=f"r{i}",
                name=f"Place {i}",
                location="Bangalore",
                city="Bangalore",
                cuisines=["Italian"],
                rating=3.0 + i * 0.1,
                budget_tier=BudgetTier.MEDIUM,
            )
            for i in range(10)
        ]
        prefs = _prefs(location="Bangalore", cuisine=[], min_rating=0)
        candidates, stats = engine.apply(prefs, many)
        assert len(candidates) == 3
        assert candidates[0].rating >= candidates[1].rating >= candidates[2].rating
        assert stats.capped_to == 3


class TestEmptyResults:
    def test_zero_candidates(self, sample_restaurants):
        engine = FilterEngine()
        prefs = _prefs(location="Tokyo", cuisine="Italian")
        candidates, stats = engine.apply(prefs, sample_restaurants)
        assert candidates == []
        assert stats.output_count == 0
        assert len(stats.suggestions) > 0

    def test_combined_delhi_italian_medium(self, sample_restaurants):
        engine = FilterEngine()
        prefs = _prefs(location="Delhi", cuisine="Italian", budget=BudgetTier.MEDIUM, min_rating=4.0)
        candidates, stats = engine.apply(prefs, sample_restaurants)
        # Delhi restaurant is North Indian, not Italian
        assert candidates == []
        assert stats.output_count == 0


class TestUserPreferencesValidation:
    def test_rejects_empty_location(self):
        with pytest.raises(ValueError):
            UserPreferences(location="  ", budget="medium", cuisine="Italian")

    def test_rejects_unknown_budget(self):
        with pytest.raises(ValueError):
            UserPreferences(location="Delhi", budget="unknown", cuisine="Italian")

    def test_clamps_min_rating(self):
        prefs = UserPreferences(location="Delhi", budget="medium", cuisine="Italian", min_rating=10)
        assert prefs.min_rating == 5.0

    def test_normalizes_top_n(self):
        prefs = UserPreferences(location="Delhi", budget="medium", cuisine="Italian", top_n=0)
        assert prefs.top_n == 5

    def test_parses_comma_separated_cuisine(self):
        prefs = UserPreferences(location="Delhi", budget="medium", cuisine="Italian, Chinese")
        assert "Italian" in prefs.cuisine_list()
        assert "Chinese" in prefs.cuisine_list()

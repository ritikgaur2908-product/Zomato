"""Unit tests for data preprocessing."""

import pytest

from data.models import BudgetTier
from data.preprocessor import preprocess_rows, row_to_restaurant
from filtering.budget import derive_budget_tier


def _sample_row(**overrides):
    base = {
        "name": "Test Bistro",
        "location": "Banashankari",
        "cuisines": "Italian, Pizza, Fast Food",
        "rate": "4.1/5",
        "approx_cost(for two people)": "800",
        "address": "21st Main Road, Banashankari, Bangalore",
        "listed_in(city)": "Banashankari",
    }
    base.update(overrides)
    return base


class TestBudgetTier:
    def test_low(self):
        assert derive_budget_tier(300) == BudgetTier.LOW

    def test_medium(self):
        assert derive_budget_tier(500) == BudgetTier.MEDIUM
        assert derive_budget_tier(800) == BudgetTier.MEDIUM

    def test_high(self):
        assert derive_budget_tier(1500) == BudgetTier.HIGH
        assert derive_budget_tier(2000) == BudgetTier.HIGH

    def test_unknown(self):
        assert derive_budget_tier(None) == BudgetTier.UNKNOWN
        assert derive_budget_tier(0) == BudgetTier.UNKNOWN


class TestRowToRestaurant:
    def test_valid_row(self):
        r = row_to_restaurant(_sample_row(), index=0)
        assert r is not None
        assert r.name == "Test Bistro"
        assert r.location == "Banashankari"
        assert r.rating == 4.1
        assert r.cost_for_two == 800
        assert r.budget_tier == BudgetTier.MEDIUM
        assert "Italian" in r.cuisines
        assert "Pizza" in r.cuisines

    def test_missing_name(self):
        assert row_to_restaurant(_sample_row(name="")) is None

    def test_missing_location(self):
        assert row_to_restaurant(_sample_row(location=None)) is None

    def test_invalid_rating_dash(self):
        assert row_to_restaurant(_sample_row(rate="-")) is None

    def test_invalid_rating_new(self):
        assert row_to_restaurant(_sample_row(rate="NEW")) is None

    def test_null_cuisine_becomes_empty_list(self):
        r = row_to_restaurant(_sample_row(cuisines=None))
        assert r is not None
        assert r.cuisines == []

    def test_cost_range_parsed_as_average(self):
        r = row_to_restaurant(_sample_row(**{"approx_cost(for two people)": "300-500"}))
        assert r is not None
        assert r.cost_for_two == 400

    def test_rating_out_of_range_rejected(self):
        assert row_to_restaurant(_sample_row(rate="6.0/5")) is None

    def test_stable_id_with_index(self):
        r1 = row_to_restaurant(_sample_row(), index=1)
        r2 = row_to_restaurant(_sample_row(), index=2)
        assert r1 is not None and r2 is not None
        assert r1.id != r2.id


class TestPreprocessBatch:
    def test_deduplication_keeps_higher_rating(self):
        rows = [
            _sample_row(name="Dup Place", rate="3.0/5"),
            _sample_row(name="Dup Place", rate="4.5/5"),
        ]
        restaurants, stats = preprocess_rows(rows)
        assert len(restaurants) == 1
        assert restaurants[0].rating == 4.5
        assert stats.duplicate_rows_removed == 1

    def test_drop_stats(self):
        rows = [
            _sample_row(),
            _sample_row(name=""),
            _sample_row(rate="-"),
        ]
        restaurants, stats = preprocess_rows(rows)
        assert len(restaurants) == 1
        assert stats.input_rows == 3
        assert stats.valid_rows == 1
        assert stats.dropped_rows == 2

    def test_high_valid_rate_on_good_batch(self):
        rows = [_sample_row(name=f"R{i}") for i in range(20)]
        restaurants, stats = preprocess_rows(rows)
        assert stats.valid_rows / stats.input_rows >= 0.9

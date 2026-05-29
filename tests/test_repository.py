"""Unit tests for RestaurantRepository (in-memory, no Hugging Face)."""

from data.models import BudgetTier, Restaurant
from data.repository import RestaurantRepository


def _make_restaurant(**kwargs) -> Restaurant:
    defaults = dict(
        id="rest_abc123",
        name="Cafe A",
        location="Koramangala",
        city="Bangalore",
        cuisines=["Italian"],
        rating=4.2,
        cost_for_two=600,
        budget_tier=BudgetTier.MEDIUM,
    )
    defaults.update(kwargs)
    return Restaurant(**defaults)


class TestRestaurantRepository:
    def test_get_all(self):
        items = [
            _make_restaurant(id="r1", location="Indiranagar", cuisines=["Chinese"]),
            _make_restaurant(id="r2", location="Koramangala", cuisines=["Italian", "Mexican"]),
        ]
        repo = RestaurantRepository(items, auto_load=False)
        assert len(repo.get_all()) == 2

    def test_get_by_id(self):
        repo = RestaurantRepository([_make_restaurant()], auto_load=False)
        assert repo.get_by_id("rest_abc123") is not None
        assert repo.get_by_id("missing") is None

    def test_get_locations_sorted(self):
        items = [
            _make_restaurant(id="r1", location="Zeta"),
            _make_restaurant(id="r2", location="Alpha"),
        ]
        repo = RestaurantRepository(items, auto_load=False)
        assert repo.get_locations() == ["Alpha", "Zeta"]

    def test_get_cuisines_distinct(self):
        items = [
            _make_restaurant(id="r1", cuisines=["Italian", "Pizza"]),
            _make_restaurant(id="r2", cuisines=["Chinese"]),
        ]
        repo = RestaurantRepository(items, auto_load=False)
        cuisines = repo.get_cuisines()
        assert cuisines == ["Chinese", "Italian", "Pizza"]

    def test_get_cities(self):
        items = [
            _make_restaurant(id="r1", city="Bangalore"),
            _make_restaurant(id="r2", city="Delhi"),
        ]
        repo = RestaurantRepository(items, auto_load=False)
        assert repo.get_cities() == ["Bangalore", "Delhi"]

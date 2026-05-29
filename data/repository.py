"""In-memory store of preprocessed restaurants."""

from __future__ import annotations

import logging

from data.loader import DatasetLoader, DatasetLoadError
from data.models import Restaurant

logger = logging.getLogger(__name__)


class RestaurantRepository:
    """Provides read access to preprocessed restaurant data."""

    def __init__(
        self,
        restaurants: list[Restaurant] | None = None,
        *,
        auto_load: bool = True,
        force_refresh: bool = False,
    ) -> None:
        if restaurants is not None:
            self._restaurants = restaurants
            self._by_id = {r.id: r for r in restaurants}
        elif auto_load:
            loader = DatasetLoader()
            loaded, stats = loader.load(force_refresh=force_refresh)
            self._restaurants = loaded
            self._by_id = {r.id: r for r in loaded}
            logger.info(
                "Repository ready: %d restaurants (dropped %d during preprocess)",
                len(self._restaurants),
                stats.dropped_rows,
            )
        else:
            self._restaurants = []
            self._by_id = {}

        if auto_load and restaurants is None and not self._restaurants:
            raise DatasetLoadError("Repository initialized with zero restaurants.")

    def get_all(self) -> list[Restaurant]:
        return list(self._restaurants)

    def get_by_id(self, restaurant_id: str) -> Restaurant | None:
        return self._by_id.get(restaurant_id)

    def get_locations(self) -> list[str]:
        """Distinct localities/neighborhoods for UI dropdowns."""
        locations = sorted({r.location for r in self._restaurants})
        return locations

    def get_cities(self) -> list[str]:
        """Distinct cities extracted from addresses."""
        cities = sorted({r.city for r in self._restaurants})
        return cities

    def get_cuisines(self) -> list[str]:
        """Distinct cuisine types across all restaurants."""
        cuisine_set: set[str] = set()
        for r in self._restaurants:
            cuisine_set.update(r.cuisines)
        return sorted(cuisine_set)

    def __len__(self) -> int:
        return len(self._restaurants)

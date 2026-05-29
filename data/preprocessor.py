"""Transform raw Hugging Face rows into canonical Restaurant entities."""

from __future__ import annotations

import hashlib
import logging
import re
from typing import Any

from filtering.budget import derive_budget_tier
from data.models import BudgetTier, PreprocessStats, Restaurant

logger = logging.getLogger(__name__)

# Known column names in ManikaSaini/zomato-restaurant-recommendation
COL_NAME = "name"
COL_LOCATION = "location"
COL_CUISINES = "cuisines"
COL_RATE = "rate"
COL_COST = "approx_cost(for two people)"
COL_ADDRESS = "address"
COL_LISTED_CITY = "listed_in(city)"

LOCATION_ALIASES: dict[str, str] = {
    "new delhi": "Delhi",
    "delhi ncr": "Delhi",
    "bengaluru": "Bangalore",
    "bangalore": "Bangalore",
}


def _get_field(row: dict[str, Any], *keys: str) -> Any:
    """Return first matching key from row (case-insensitive fallback)."""
    lower_map = {k.lower(): k for k in row}
    for key in keys:
        if key in row:
            return row[key]
        found = lower_map.get(key.lower())
        if found is not None:
            return row[found]
    return None


def _normalize_string(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text if text else None


def _title_location(value: str) -> str:
    text = value.strip().title()
    return LOCATION_ALIASES.get(text.lower(), text)


def _parse_cuisines(value: Any) -> list[str]:
    text = _normalize_string(value)
    if not text:
        return []
    parts = [c.strip().title() for c in re.split(r"[,/]", text) if c.strip()]
    seen: set[str] = set()
    result: list[str] = []
    for part in parts:
        key = part.lower()
        if key not in seen:
            seen.add(key)
            result.append(part)
    return result


def _parse_rating(value: Any) -> float | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text or text in {"-", "NEW", "new", "nan", "None"}:
        return None
    # Formats: "4.1/5", "4.1", "Rated 4.1"
    match = re.search(r"(\d+(?:\.\d+)?)\s*/\s*5", text)
    if match:
        rating = float(match.group(1))
    else:
        match = re.search(r"(\d+(?:\.\d+)?)", text)
        if not match:
            return None
        rating = float(match.group(1))
    if rating < 0 or rating > 5:
        return None
    return round(rating, 2)


def _parse_cost(value: Any) -> int | None:
    if value is None:
        return None
    # Handle NaN float values
    try:
        if isinstance(value, float) and (value != value):  # NaN check
            return None
    except (TypeError, ValueError):
        pass
    text = str(value).strip().replace(",", "")
    if not text or text.lower() in {"-", "nan", "none"}:
        return None
    # Handle ranges like "300-400" or "300 - 400"
    range_match = re.match(r"^(\d+)\s*[-–]\s*(\d+)$", text)
    if range_match:
        low, high = int(range_match.group(1)), int(range_match.group(2))
        return (low + high) // 2
    digits = re.sub(r"[^\d]", "", text)
    if not digits:
        return None
    cost = int(digits)
    if cost <= 0 or cost > 1_000_000:
        return None
    return cost


def _extract_city(address: str | None, listed_city: str | None, location: str) -> str:
    if address:
        parts = [p.strip() for p in address.split(",") if p.strip()]
        if parts:
            city = _title_location(parts[-1])
            if city:
                return city
    if listed_city:
        return _title_location(listed_city)
    return _title_location(location)


def _make_id(name: str, location: str, index: int) -> str:
    base = f"{name}|{location}|{index}"
    digest = hashlib.md5(base.encode("utf-8")).hexdigest()[:12]
    return f"rest_{digest}"


def row_to_restaurant(row: dict[str, Any], index: int = 0) -> Restaurant | None:
    """Convert a single raw dataset row to Restaurant, or None if invalid."""
    name = _normalize_string(_get_field(row, COL_NAME))
    location_raw = _normalize_string(_get_field(row, COL_LOCATION))
    if not name:
        return None
    if not location_raw:
        return None

    location = _title_location(location_raw)
    address = _normalize_string(_get_field(row, COL_ADDRESS))
    listed_city = _normalize_string(_get_field(row, COL_LISTED_CITY))
    city = _extract_city(address, listed_city, location)

    rating = _parse_rating(_get_field(row, COL_RATE))
    if rating is None:
        return None

    cost = _parse_cost(_get_field(row, COL_COST))
    cuisines = _parse_cuisines(_get_field(row, COL_CUISINES))
    budget_tier = derive_budget_tier(cost)

    restaurant_id = _make_id(name, location, index)

    return Restaurant(
        id=restaurant_id,
        name=name,
        location=location,
        city=city,
        cuisines=cuisines,
        rating=rating,
        cost_for_two=cost,
        budget_tier=budget_tier,
        raw={k: v for k, v in row.items() if v is not None},
    )


def _deduplicate_by_name_location(restaurants: list[Restaurant]) -> tuple[list[Restaurant], int]:
    """Keep highest-rated row per (name, location) pair."""
    best: dict[tuple[str, str], Restaurant] = {}
    for r in restaurants:
        key = (r.name.lower(), r.location.lower())
        existing = best.get(key)
        if existing is None or r.rating > existing.rating:
            best[key] = r
    removed = len(restaurants) - len(best)
    return list(best.values()), removed


def preprocess_rows(rows: list[dict[str, Any]]) -> tuple[list[Restaurant], PreprocessStats]:
    """Preprocess a batch of raw rows into Restaurant entities."""
    stats = PreprocessStats(input_rows=len(rows))
    drop_reasons: dict[str, int] = {}
    valid: list[Restaurant] = []

    for i, row in enumerate(rows):
        try:
            restaurant = row_to_restaurant(row, index=i)
        except (ValueError, TypeError) as exc:
            drop_reasons["parse_error"] = drop_reasons.get("parse_error", 0) + 1
            logger.debug("Row %d parse error: %s", i, exc)
            continue

        if restaurant is None:
            if not _normalize_string(_get_field(row, COL_NAME)):
                key = "missing_name"
            elif not _normalize_string(_get_field(row, COL_LOCATION)):
                key = "missing_location"
            else:
                key = "invalid_rating"
            drop_reasons[key] = drop_reasons.get(key, 0) + 1
            continue

        valid.append(restaurant)

    deduped, dup_removed = _deduplicate_by_name_location(valid)
    stats.duplicate_rows_removed = dup_removed
    stats.valid_rows = len(deduped)
    stats.dropped_rows = stats.input_rows - len(valid)
    stats.drop_reasons = drop_reasons

    if stats.input_rows > 0:
        pct = 100.0 * stats.valid_rows / stats.input_rows
        logger.info(
            "Preprocessed %d rows: %d valid (%.1f%%), %d dropped, %d duplicates removed",
            stats.input_rows,
            stats.valid_rows,
            pct,
            stats.dropped_rows,
            stats.duplicate_rows_removed,
        )
        if pct < 90:
            logger.warning(
                "Valid row rate %.1f%% is below 90%% target; check drop_reasons: %s",
                pct,
                drop_reasons,
            )

    return deduped, stats

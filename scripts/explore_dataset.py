"""Explore raw Zomato dataset schema and cost distribution."""

from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from data.loader import DatasetLoader
from data.preprocessor import _parse_cost, _parse_rating, preprocess_rows


def main() -> None:
    loader = DatasetLoader()
    print(f"Dataset: {loader.dataset_name}\n")

    print("Loading raw sample (first 100 rows)...")
    try:
        raw = loader._load_from_huggingface()  # noqa: SLF001
    except Exception as exc:
        print(f"ERROR: {exc}")
        sys.exit(1)

    print(f"Total rows: {len(raw)}")
    if raw:
        print(f"\nColumns ({len(raw[0])}):")
        for col in sorted(raw[0].keys()):
            print(f"  - {col}")

        print("\nSample row:")
        sample = raw[0]
        for key in ["name", "location", "cuisines", "rate", "approx_cost(for two people)", "address"]:
            if key in sample:
                print(f"  {key}: {sample[key]!r}")

    sample_size = min(5000, len(raw))
    costs: list[int] = []
    ratings: list[float] = []
    for row in raw[:sample_size]:
        c = _parse_cost(row.get("approx_cost(for two people)"))
        if c is not None:
            costs.append(c)
        r = _parse_rating(row.get("rate"))
        if r is not None:
            ratings.append(r)

    if costs:
        costs.sort()
        print(f"\nCost for two (parsed, n={len(costs)}):")
        print(f"  min={costs[0]}, median={costs[len(costs)//2]}, max={costs[-1]}")
        buckets = Counter()
        for c in costs:
            if c < 500:
                buckets["low (<500)"] += 1
            elif c < 1500:
                buckets["medium (500-1499)"] += 1
            else:
                buckets["high (>=1500)"] += 1
        print("  budget distribution:", dict(buckets))

    print("\nRunning full preprocess on sample...")
    restaurants, stats = preprocess_rows(raw[:sample_size])
    print(stats.model_dump_json(indent=2))
    print(f"\nValid restaurants in sample: {len(restaurants)}")

    if restaurants:
        print("\nExample preprocessed restaurant:")
        r = restaurants[0]
        print(r.model_dump_json(indent=2))


if __name__ == "__main__":
    main()

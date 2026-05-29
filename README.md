# Zomato AI Restaurant Recommendation System

AI-powered restaurant recommendations using the Zomato Hugging Face dataset and LLM-based ranking (later phases).

## Documentation

- [Context](docs/context.md)
- [Architecture](docs/architecture.md)
- [Implementation plan](docs/implementation-plan.md)
- [Edge cases](docs/edge-cases.md)

## Setup

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
pip install -r requirements.txt
copy .env.example .env          # optional overrides
```

## Phase 3: LLM layer (Groq)

Set `LLM_API_KEY` in `.env` (copy from `.env.example`). Tests use `MockLLMClient` only—no API key needed for pytest.

```python
from data.models import BudgetTier, UserPreferences
from data.repository import RestaurantRepository
from filtering.engine import FilterEngine
from llm.service import LLMRecommendationService
from llm.client import MockLLMClient  # or omit for live Groq

repo = RestaurantRepository()
prefs = UserPreferences(
    location="Bangalore",
    budget=BudgetTier.MEDIUM,
    cuisine="Italian",
    min_rating=4.0,
    top_n=3,
)
candidates, stats = FilterEngine().apply(prefs, repo.get_all())

# Mock for local dev without API key; use LLMRecommendationService() for Groq
service = LLMRecommendationService(client=MockLLMClient())
result, meta = service.rank_and_explain(prefs, candidates, filter_stats=stats)

for rec in result.recommendations:
    print(rec.rank, rec.restaurant.name, rec.explanation)
print(meta.ai_explanations_available, result.summary)
```

## Phase 2: Filtering layer

```python
from data.models import BudgetTier, UserPreferences
from data.repository import RestaurantRepository
from filtering.engine import FilterEngine

repo = RestaurantRepository()
prefs = UserPreferences(
    location="Bangalore",
    budget=BudgetTier.MEDIUM,
    cuisine="Italian",
    min_rating=4.0,
)
candidates, stats = FilterEngine().apply(prefs, repo.get_all())
print(stats.output_count, [c.name for c in candidates[:5]])
```

## Phase 1: Data layer

Load and preprocess restaurants:

```bash
python -c "from data.repository import RestaurantRepository; r = RestaurantRepository(); print(len(r.get_all()))"
```

Explore raw dataset schema and cost distribution:

```bash
python scripts/explore_dataset.py
```

First run downloads from Hugging Face (~574 MB) and caches to `data/cache/restaurants.parquet`. Subsequent runs use the cache.

## Tests

```bash
python -m pytest tests/ -v
```

Tests use fixtures only—no network or LLM API key required.

## Project structure

```
app/           # Config (orchestrator in later phases)
data/          # Loader, preprocessor, models, repository
filtering/     # Filter engine and budget tier logic
llm/           # Prompts, Groq client, parser, LLM service
scripts/       # Dataset exploration
tests/         # Unit tests
docs/          # Design documents
```

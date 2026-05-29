# Phase-Wise Implementation Plan

> **AI-Powered Restaurant Recommendation System (Zomato Use Case)**  
> Derived from [`docs/context.md`](./context.md) and [`docs/architecture.md`](./architecture.md).

---

## Plan Overview

| Phase | Name | Primary outcome | Est. effort |
|-------|------|-----------------|-------------|
| **0** | Project setup | Runnable repo, config, dependencies | 0.5–1 day |
| **1** | Data layer | HF dataset loaded, preprocessed, cached | 1–2 days |
| **2** | Filtering layer | Deterministic candidate selection | 1–2 days |
| **3** | LLM layer | Rank, explain, parse with grounding | 2–3 days |
| **4** | Orchestration | End-to-end pipeline without UI | 1 day |
| **5** | Presentation | User-facing app (Streamlit or FastAPI) | 2–3 days |
| **6** | Hardening & delivery | Tests, docs, fallbacks, demo-ready | 1–2 days |

**Total estimate:** ~9–14 days for a solo developer (MVP scope).

**Design principle (all phases):** Filter first, LLM second—never recommend restaurants outside the dataset.

---

## Phase 0: Project Setup & Foundation

### Goal

Establish repository structure, dependencies, configuration, and development conventions so later phases plug in cleanly.

### Tasks

| # | Task | Details |
|---|------|---------|
| 0.1 | Initialize project layout | Create folders per architecture: `app/`, `data/`, `filtering/`, `llm/`, `presentation/`, `tests/` |
| 0.2 | Dependency management | `requirements.txt` or `pyproject.toml`: `datasets`, `pydantic`, `python-dotenv`, `pytest`; add `groq` before Phase 3 |
| 0.3 | Configuration module | `app/config.py`: dataset name, cache path, budget thresholds, `CANDIDATE_LIMIT`, `DEFAULT_TOP_N` |
| 0.4 | Environment template | `.env.example` with `LLM_API_KEY` (Groq), `LLM_PROVIDER=groq`, `LLM_MODEL` (e.g. `llama-3.3-70b-versatile`); no secrets committed |
| 0.5 | Git ignore | Exclude `.env`, `data/cache/`, `__pycache__/`, virtualenv |
| 0.6 | README skeleton | Project title, setup steps, link to `docs/` |

### Deliverables

- [ ] Repository structure matches architecture §4.2
- [ ] `pip install -r requirements.txt` succeeds
- [ ] `app/config.py` reads env with sensible defaults
- [ ] `.env.example` documented in README

### Acceptance criteria

- Virtual environment activates and imports core packages without error
- Config loads from environment; missing LLM key does not break data-only phases

### Dependencies

- None (first phase)

---

## Phase 1: Data Layer

### Goal

Load the Zomato dataset from Hugging Face, preprocess into canonical `Restaurant` entities, and expose them via an in-memory repository with optional disk cache.

### Maps to context

- Workflow step **1 — Data Ingestion**
- Requirements: load dataset, preprocess structured fields

### Tasks

| # | Task | File(s) | Details |
|---|------|---------|---------|
| 1.1 | Domain models | `data/models.py` | `Restaurant`, `BudgetTier` enum; Pydantic or dataclasses |
| 1.2 | Dataset loader | `data/loader.py` | `DatasetLoader.load()` using `datasets.load_dataset("ManikaSaini/zomato-restaurant-recommendation")` |
| 1.3 | Field mapping | `data/preprocessor.py` | Map raw HF columns → canonical fields; inspect dataset schema first |
| 1.4 | Normalization | `data/preprocessor.py` | Trim strings, title-case location, split cuisines on comma |
| 1.5 | Rating coercion | `data/preprocessor.py` | Parse float; drop or flag rows with invalid rating |
| 1.6 | Budget tier derivation | `filtering/budget.py` | Map `cost_for_two` → `low` / `medium` / `high` via config thresholds |
| 1.7 | Stable IDs | `data/preprocessor.py` | Hash `name + location` or use dataset index |
| 1.8 | Repository | `data/repository.py` | `get_all()`, `get_by_id()`, `get_locations()`, `get_cuisines()` |
| 1.9 | Disk cache (optional) | `data/loader.py` | Save preprocessed Parquet/JSON to `data/cache/`; skip HF on subsequent runs |
| 1.10 | Exploration script | `scripts/explore_dataset.py` | Print columns, sample rows, cost distribution for threshold tuning |

### Deliverables

- [ ] `Restaurant` model with: `id`, `name`, `location`, `cuisines`, `rating`, `cost_for_two`, `budget_tier`
- [ ] `RestaurantRepository` populated on startup
- [ ] Helper methods for distinct locations and cuisines (for UI dropdowns later)

### Acceptance criteria

- Loader fetches dataset from Hugging Face (or cache) without manual download steps
- ≥ 90% of rows produce valid `Restaurant` records (log dropped count)
- Budget tiers assigned consistently; spot-check 10 random rows manually
- `repository.get_all()` returns non-empty list
- Unit tests: `test_preprocessor.py` covers null cuisine, invalid rating, budget mapping

### Dependencies

- Phase 0 complete

### Verification command (example)

```bash
python -c "from data.repository import RestaurantRepository; r = RestaurantRepository(); print(len(r.get_all()))"
```

---

## Phase 2: Filtering Layer

### Goal

Implement deterministic filtering so only dataset-backed candidates reach the LLM, with stats, candidate capping, and empty-result handling.

### Maps to context

- Workflow step **3 — Integration Layer** (filter portion)
- Constraint: grounded recommendations

### Tasks

| # | Task | File(s) | Details |
|---|------|---------|---------|
| 2.1 | User preferences model | `data/models.py` | `UserPreferences`: location, budget, cuisine, min_rating, extras, top_n |
| 2.2 | Location filter | `filtering/engine.py` | Case-insensitive match (exact city or substring) |
| 2.3 | Cuisine filter | `filtering/engine.py` | User cuisine overlaps any restaurant cuisine |
| 2.4 | Rating filter | `filtering/engine.py` | `restaurant.rating >= preferences.min_rating` |
| 2.5 | Budget filter | `filtering/engine.py` | `restaurant.budget_tier == preferences.budget` |
| 2.6 | Extras filter (optional) | `filtering/engine.py` | Keyword scan on name/raw fields if available in dataset |
| 2.7 | Candidate selector | `filtering/engine.py` | After filters, sort by rating desc, take top `CANDIDATE_LIMIT` (default 20) |
| 2.8 | Filter stats | `filtering/engine.py` | Return `FilterStats`: input_count, output_count |
| 2.9 | Empty-result path | `filtering/engine.py` | Return empty list + stats; no LLM call from this layer |
| 2.10 | Relaxation helper (optional) | `filtering/engine.py` | Suggest widening budget or lowering min_rating when output is 0 |

### Deliverables

- [ ] `FilterEngine.apply(preferences, restaurants) -> (candidates, stats)`
- [ ] Configurable `CANDIDATE_LIMIT` in `app/config.py`
- [ ] Unit tests for each filter and combined pipeline

### Acceptance criteria

- Given Delhi + Italian + medium + min_rating 4.0, output only matching restaurants from repository
- No candidate has `rating` below `min_rating` or wrong `budget_tier`
- Candidate count ≤ `CANDIDATE_LIMIT`
- Empty preferences edge case handled (validation deferred to Phase 5)
- `test_filter_engine.py` passes in CI without LLM

### Dependencies

- Phase 1 complete (`Restaurant`, `RestaurantRepository`)

### Manual test (CLI snippet)

```python
prefs = UserPreferences(location="Delhi", budget="medium", cuisine="Italian", min_rating=4.0)
candidates, stats = FilterEngine().apply(prefs, repo.get_all())
print(stats, [c.name for c in candidates[:5]])
```

---

## Phase 3: LLM Layer

### Goal

Build prompt assembly, pluggable LLM client, structured JSON response parsing, and validation so the model ranks and explains only provided candidates. **Phase 3 uses [Groq](https://console.groq.com/)** (not OpenAI) as the live LLM provider.

### Maps to context

- Workflow step **4 — Recommendation Engine (LLM)**
- Requirements: LLM ranking, explanations, optional summary

### Tasks

| # | Task | File(s) | Details |
|---|------|---------|---------|
| 3.1 | Output models | `data/models.py` | `RankedRecommendation`, `RecommendationResponse` |
| 3.2 | Prompt templates | `llm/prompts.py` | System prompt: role, JSON schema, grounding rules (ADR-001, ADR-002) |
| 3.3 | Prompt builder | `llm/prompts.py` | Inject `UserPreferences` + compact candidate JSON (id, name, cuisines, rating, cost, budget_tier) |
| 3.4 | LLM client interface | `llm/client.py` | Abstract `complete(prompt) -> str` |
| 3.5 | Provider implementation | `llm/client.py` | `GroqClient` using `groq` SDK + Chat Completions; `LLM_PROVIDER=groq`, `LLM_API_KEY` from Groq console (ADR-004) |
| 3.6 | Mock client | `llm/client.py` | `MockLLMClient` returning fixed JSON for tests |
| 3.7 | Response parser | `llm/parser.py` | Parse JSON; validate `restaurant_id` ∈ candidate ids |
| 3.8 | Merge logic | `llm/parser.py` | Attach `Restaurant` entity to each ranked item; preserve factual fields from dataset |
| 3.9 | Fallback ranking | `llm/parser.py` | On parse failure: rating-sorted top N + generic explanation string |
| 3.10 | Retry policy | `llm/client.py` | One retry on malformed JSON; then fallback |
| 3.11 | Prompt iteration | manual | Test 3–5 preference combos; refine system prompt for consistent JSON |

### Deliverables

- [ ] `PromptBuilder.build(preferences, candidates) -> messages`
- [ ] `LLMClient` + `GroqClient` + `MockLLMClient`
- [ ] `ResponseParser.parse(raw, candidates) -> list[RankedRecommendation]`
- [ ] Tests: `test_prompt_builder.py`, `test_parser.py` (no live API)

### Acceptance criteria

- LLM output never introduces unknown `restaurant_id` values (parser rejects or strips)
- Each explanation references at least one user preference (manual review on 5 samples)
- `MockLLMClient` tests pass without network
- Malformed JSON triggers fallback, not crash
- Temperature ≤ 0.3 for ranking consistency

### Dependencies

- Phase 2 complete (`UserPreferences`, candidate list shape)

### Grounding checklist (prompt must enforce)

- [ ] Only ids from `candidates` array
- [ ] Do not modify rating or cost values
- [ ] Output valid JSON matching schema in architecture §7.3

---

## Phase 4: Orchestration Layer

### Goal

Wire data, filtering, and LLM into a single `RecommendationOrchestrator` entry point with unified error handling—runnable without UI.

### Maps to context

- Full workflow: ingestion → filter → LLM → structured response

### Tasks

| # | Task | File(s) | Details |
|---|------|---------|---------|
| 4.1 | Orchestrator class | `app/orchestrator.py` | Implement `recommend(preferences) -> RecommendationResponse` per architecture §8.1 |
| 4.2 | Empty candidates branch | `app/orchestrator.py` | Return `RecommendationResponse` with empty list + helpful message + stats |
| 4.3 | LLM failure branch | `app/orchestrator.py` | Rating-sorted fallback + `metadata.ai_explanations_available = false` |
| 4.4 | Dataset load failure | `app/orchestrator.py` | Fail fast with clear error before filtering |
| 4.5 | Logging | `app/orchestrator.py` | Log filter stats, candidate count, LLM latency |
| 4.6 | CLI entry point | `app/main.py` | Accept prefs via argparse or JSON file; print formatted results |
| 4.7 | Integration test | `tests/test_orchestrator.py` | Full pipeline with `MockLLMClient` |

### Deliverables

- [ ] `RecommendationOrchestrator.recommend()` working end-to-end
- [ ] CLI: `python -m app.main --location Delhi --budget medium --cuisine Italian --min-rating 4.0`

### Acceptance criteria

- CLI returns top N recommendations with name, cuisine, rating, cost, explanation
- Zero candidates → no LLM API call (verify via mock or log)
- LLM down → still returns rating-sorted results with notice
- Integration test passes with mock LLM only

### Dependencies

- Phases 1, 2, 3 complete

### Pipeline diagram

```
UserPreferences
    → Repository.get_all()
    → FilterEngine.apply()
    → [empty?] → empty RecommendationResponse
    → PromptBuilder.build()
    → LLMClient.complete()
    → ResponseParser.parse()
    → RecommendationResponse[:top_n]
```

---

## Phase 5: Presentation Layer

### Goal

Expose the orchestrator through a user-friendly interface: preference collection, metadata dropdowns, and recommendation cards.

### Maps to context

- Workflow step **2 — User Input**
- Workflow step **5 — Output Display**
- Requirements: UI, formatted output fields

### Option A: Streamlit (recommended for MVP)

| # | Task | File(s) | Details |
|---|------|---------|---------|
| 5A.1 | Streamlit app | `app/streamlit_app.py` | Sidebar or form for all preference fields |
| 5A.2 | Dropdowns | `app/streamlit_app.py` | Locations/cuisines from `repository.get_locations()` / `get_cuisines()` |
| 5A.3 | Submit handler | `app/streamlit_app.py` | Call orchestrator; show spinner during LLM call |
| 5A.4 | Result cards | `app/streamlit_app.py` | Name, cuisine, rating, cost, rank badge, explanation |
| 5A.5 | Summary section | `app/streamlit_app.py` | Collapsible LLM `summary` if present |
| 5A.6 | Empty state | `app/streamlit_app.py` | Friendly message + filter relaxation hints |

### Option B: FastAPI + optional frontend

| # | Task | File(s) | Details |
|---|------|---------|---------|
| 5B.1 | API schemas | `presentation/schemas.py` | Request/response Pydantic models |
| 5B.2 | Endpoints | `app/main.py` | `GET /health`, `GET /meta/locations`, `GET /meta/cuisines`, `POST /recommendations` |
| 5B.3 | Validation | `app/main.py` | 400 on invalid budget enum, rating out of range |
| 5B.4 | Formatter | `presentation/formatter.py` | Optional plain-text formatting for CLI |

### Deliverables (either option)

- [ ] User can submit: location, budget, cuisine, min rating, extras, top_n
- [ ] Results show: restaurant name, cuisine, rating, estimated cost, AI explanation
- [ ] Invalid input shows field-level errors (FastAPI) or inline validation (Streamlit)

### Acceptance criteria

- Non-technical user can get recommendations in &lt; 3 clicks (Streamlit) or 1 API call (FastAPI)
- UI dropdown values come from actual dataset (no free-text cities that never match)
- Loading state visible during LLM call
- Matches context checklist items for UI and formatted output

### Dependencies

- Phase 4 complete

### Suggested default

Start with **Streamlit** for speed; add FastAPI in Phase 6 or as stretch if time permits.

---

## Phase 6: Hardening, Testing & Delivery

### Goal

Make the project demo-ready: comprehensive tests, documentation, error fallbacks verified, and repeatable setup.

### Tasks

| # | Task | Details |
|---|------|---------|
| 6.1 | Test coverage | Preprocessor, FilterEngine, PromptBuilder, ResponseParser, Orchestrator (mock LLM) |
| 6.2 | E2E golden test (optional) | Record one real LLM response; assert parser + merge |
| 6.3 | README completion | Setup, env vars, run Streamlit/CLI, architecture link |
| 6.4 | Update context checklist | Mark completed items in `docs/context.md` or project README |
| 6.5 | Error path audit | Dataset fail, empty filter, LLM timeout, bad JSON—all handled |
| 6.6 | Budget threshold tuning | Revisit Phase 1 thresholds using dataset distribution |
| 6.7 | `.env.example` + security review | No keys in repo; document Groq `LLM_API_KEY` and `LLM_PROVIDER=groq` |
| 6.8 | Demo script | 2–3 example preference sets that produce good output |
| 6.9 | Docker (optional) | Dockerfile + volume for `data/cache` |
| 6.10 | CI (optional) | GitHub Actions: `pytest` on push (no live LLM in CI) |

### Deliverables

- [ ] `pytest` passes locally and in CI (if configured)
- [ ] README: install, configure, run, test
- [ ] Demo scenarios documented
- [ ] All context.md requirements checked off

### Acceptance criteria

- Fresh clone + `pip install` + `.env` → working demo in &lt; 15 minutes
- Tests run without `LLM_API_KEY` (mocks only)
- No restaurant in output lacks a corresponding dataset `id`

### Dependencies

- Phases 0–5 complete

---

## Cross-Phase Requirements Traceability

| Context / architecture requirement | Phase |
|-----------------------------------|-------|
| Load Zomato dataset from Hugging Face | 1 |
| Preprocess name, location, cuisine, cost, rating | 1 |
| User preference collection | 5 |
| Filtering aligned with user inputs | 2 |
| LLM ranking + explanation prompt | 3 |
| Output: name, cuisine, rating, cost, AI explanation | 4, 5 |
| Filter before LLM (grounding) | 2, 3, 4 |
| Budget low / medium / high | 1, 2 |
| Personalized explanations | 3 |
| Zomato-style discovery flow | 5 |

---

## Milestone Timeline (Suggested)

```
Week 1
├── Day 1–2: Phase 0 + Phase 1 (data loading & preprocessing)
├── Day 3–4: Phase 2 (filtering)
└── Day 5:   Phase 3 start (prompts + mock LLM)

Week 2
├── Day 1–2: Phase 3 complete (real LLM + parser)
├── Day 3:   Phase 4 (orchestrator + CLI)
├── Day 4–5: Phase 5 (Streamlit UI)
└── Day 6–7: Phase 6 (tests, README, demo)
```

---

## Risk Register & Mitigations

| Risk | Impact | Mitigation | Phase |
|------|--------|------------|-------|
| HF dataset schema differs from assumptions | Blocked preprocessing | Run `explore_dataset.py` first; adjust field mapping | 1 |
| Too few candidates after strict filters | Poor UX | Relaxation hints; optional filter widening | 2 |
| LLM hallucinates restaurants | Wrong recommendations | Filter-first + id validation in parser | 2, 3 |
| High LLM cost / latency | Slow demo | Cap candidates at 20; use a smaller Groq model (e.g. `llama-3.1-8b-instant`) | 3 |
| Groq rate limits / API errors | Failed ranking | Retry once; rating fallback; document free-tier limits | 3, 4 |
| Invalid JSON from LLM | Crashes | Retry once + rating fallback | 3, 4 |
| Missing API key at demo time | No AI explanations | Mock client + filter-only fallback | 3, 4, 6 |

---

## Definition of Done (Project MVP)

The MVP is complete when all of the following are true:

1. **Data:** Zomato dataset loads from Hugging Face (or cache) into structured `Restaurant` records.
2. **Filter:** User preferences deterministically reduce the set to grounded candidates.
3. **LLM:** Top recommendations are ranked and explained with preference-aware copy.
4. **UI:** User can submit preferences and view results without using the CLI.
5. **Grounding:** Every displayed restaurant exists in the dataset with matching id, rating, and cost.
6. **Resilience:** Empty results and LLM failures degrade gracefully with clear messaging.
7. **Tests:** Core logic covered by unit/integration tests without live LLM in CI.
8. **Docs:** README explains setup and links to `context.md` and `architecture.md`.

---

## Post-MVP Enhancements (Backlog)

| Enhancement | Value |
|-------------|-------|
| FastAPI + React frontend | Production-style UX |
| Filter relaxation automation | Better empty-result recovery |
| LLM response caching | Lower cost for repeated queries |
| Extras via embeddings | Smarter “family-friendly” matching |
| Docker Compose deployment | One-command demo |
| Rate limiting on API | Public deployment safety |
| Analytics dashboard | Track popular cuisines/locations |

---

## Related Documents

| Document | Role |
|----------|------|
| [`docs/context.md`](./context.md) | Product goals, workflow, constraints |
| [`docs/architecture.md`](./architecture.md) | Components, APIs, ADRs, data models |
| [`docs/problemStatement.txt`](./problemStatement.txt) | Original assignment spec |

---

## Quick Start Checklist (for implementers)

- [ ] Read `context.md` and `architecture.md`
- [ ] Complete Phase 0 setup
- [ ] Run dataset exploration script (Phase 1)
- [ ] Implement phases 1 → 6 in order; do not skip filtering before LLM
- [ ] Use `MockLLMClient` until Phase 4 integration test passes
- [ ] Add Groq API key (`LLM_API_KEY`) only when testing Phase 3+ manually
- [ ] Mark requirements done in README as each phase completes

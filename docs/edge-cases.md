# Edge Cases & Handling Guide

> **AI-Powered Restaurant Recommendation System (Zomato Use Case)**  
> Companion to [`context.md`](./context.md), [`architecture.md`](./architecture.md), and [`implementation-plan.md`](./implementation-plan.md).

---

## How to Use This Document

Each edge case includes:

| Column | Meaning |
|--------|---------|
| **ID** | Unique reference (e.g. `DATA-01`) |
| **Scenario** | What can go wrong |
| **Expected behavior** | What the system must do |
| **Layer** | Where to implement the fix |
| **Priority** | `P0` critical · `P1` high · `P2` medium · `P3` low |

**Golden rule:** Never show a restaurant that is not in the dataset. When in doubt, fail safe with a clear message—not silent wrong data.

---

## 1. Data Ingestion & External Dependencies

### 1.1 Hugging Face / Network

| ID | Scenario | Expected behavior | Layer | Priority |
|----|----------|-------------------|-------|----------|
| **DATA-01** | Hugging Face unreachable (no internet, DNS failure) | Fail fast at startup with message: *"Could not load dataset. Check connection or use cached data at {path}."* Do not start with empty repository silently. | `data/loader.py` | P0 |
| **DATA-02** | HF dataset renamed, removed, or schema changed | Catch load/KeyError; log actual columns received; fail with actionable error. Version-pin dataset revision if possible. | `data/loader.py` | P0 |
| **DATA-03** | Download interrupted (partial cache file) | Detect corrupt cache (checksum or parse failure); delete bad cache and retry once; then surface error. | `data/loader.py` | P1 |
| **DATA-04** | Very slow download on first run | Show progress in UI/CLI; allow cached subsequent runs. Document first-run wait in README. | `data/loader.py`, UI | P2 |
| **DATA-05** | Disk full while writing cache | Catch `OSError`; continue in-memory for session if possible; warn that cache was not saved. | `data/loader.py` | P2 |
| **DATA-06** | Cached data stale but HF has updates | Use cache mtime or dataset revision in config; optional `--refresh-cache` flag to force reload. | `data/loader.py` | P3 |

### 1.2 Dataset Content

| ID | Scenario | Expected behavior | Layer | Priority |
|----|----------|-------------------|-------|----------|
| **DATA-07** | Empty dataset (0 rows after load) | Abort startup; do not expose recommendation API/UI. | `data/repository.py` | P0 |
| **DATA-08** | Dataset has unexpected column names | Map via configurable column aliases in `config.py`; log unmapped columns once. | `data/preprocessor.py` | P0 |
| **DATA-09** | Duplicate rows (same name + location) | Deduplicate on `id` generation; keep highest-rated row or first occurrence; log duplicate count. | `data/preprocessor.py` | P1 |
| **DATA-10** | Extremely large dataset (memory pressure) | Stream/batch preprocess; persist Parquet cache; lazy-load only preprocessed cache in production. | `data/loader.py` | P2 |

---

## 2. Preprocessing & Data Quality

### 2.1 Missing or Invalid Fields

| ID | Scenario | Expected behavior | Layer | Priority |
|----|----------|-------------------|-------|----------|
| **PRE-01** | `name` is null or empty | Skip row; increment `dropped_rows` counter. | `data/preprocessor.py` | P0 |
| **PRE-02** | `location` is null or empty | Skip row (cannot filter by city). | `data/preprocessor.py` | P0 |
| **PRE-03** | `rating` is null, `"-"`, `"NEW"`, or non-numeric | Try parse; if fail, skip row OR assign `rating=0.0` and exclude from rating-based sort (document choice). Prefer **skip** for recommendation quality. | `data/preprocessor.py` | P0 |
| **PRE-04** | `rating` out of range (e.g. 6.5, negative) | Clamp to `[0.0, 5.0]` or skip row; log anomaly count. | `data/preprocessor.py` | P1 |
| **PRE-05** | `cuisine` is null or empty | Set `cuisines=[]`; row may still match location-only queries but excluded from cuisine filter. | `data/preprocessor.py` | P1 |
| **PRE-06** | `cost_for_two` is null, 0, or non-numeric | Set `cost_for_two=null`, `budget_tier=unknown`; exclude from strict budget filter OR map `unknown` to nearest tier via config flag. | `data/preprocessor.py`, `filtering/budget.py` | P0 |
| **PRE-07** | `cost_for_two` extreme outlier (e.g. 999999) | Cap or winsorize using percentile config; re-derive budget tier. | `data/preprocessor.py` | P2 |

### 2.2 String Normalization

| ID | Scenario | Expected behavior | Layer | Priority |
|----|----------|-------------------|-------|----------|
| **PRE-08** | Cuisine string `"Italian, Pizza, Fast Food"` | Split on comma; trim; dedupe; case-insensitive storage for matching. | `data/preprocessor.py` | P0 |
| **PRE-09** | Location `"  delhi  "` vs `"Delhi"` vs `"New Delhi"` | Normalize: trim, title-case; maintain alias map (`{"new delhi": "Delhi"}`) in config for known variants. | `data/preprocessor.py` | P1 |
| **PRE-10** | Location contains area + city (`"Connaught Place, Delhi"`) | Substring match in filter OR extract city via regex/alias table. | `filtering/engine.py` | P1 |
| **PRE-11** | Special characters in name (unicode, emoji) | Preserve UTF-8; do not strip unless breaking JSON; ensure LLM prompt escapes properly. | `data/preprocessor.py`, `llm/prompts.py` | P2 |
| **PRE-12** | Extremely long restaurant name (>500 chars) | Truncate in LLM prompt only; keep full name in UI. | `llm/prompts.py` | P3 |

### 2.3 IDs & Budget Tiers

| ID | Scenario | Expected behavior | Layer | Priority |
|----|----------|-------------------|-------|----------|
| **PRE-13** | Hash collision on `name + location` | Append row index to hash input; guarantee unique `id`. | `data/preprocessor.py` | P1 |
| **PRE-14** | `cost_for_two` exactly on tier boundary (500, 1500) | Define inclusive/exclusive rules in config and apply consistently (e.g. 500 → medium). | `filtering/budget.py` | P1 |
| **PRE-15** | All restaurants map to one budget tier | Log warning at preprocess; still functional; suggest threshold tuning in ops logs. | `data/preprocessor.py` | P2 |

---

## 3. User Input & Validation

### 3.1 Required Fields

| ID | Scenario | Expected behavior | Layer | Priority |
|----|----------|-------------------|-------|----------|
| **INP-01** | Missing `location` | Reject request with 400 / inline error: *"Location is required."* | `presentation/schemas.py`, UI | P0 |
| **INP-02** | Missing `budget` | Reject or default to `medium` with UI warning (prefer explicit user choice). | Validation | P1 |
| **INP-03** | Missing `cuisine` | Reject OR treat as "any cuisine" if product allows—document as explicit `cuisine=*` mode. | Validation, `filtering/engine.py` | P1 |
| **INP-04** | Missing `min_rating` | Default to `0.0` (no rating filter). | Validation | P1 |

### 3.2 Invalid Values

| ID | Scenario | Expected behavior | Layer | Priority |
|----|----------|-------------------|-------|----------|
| **INP-05** | `budget` not in `{low, medium, high}` | 400 with allowed values list. | Validation | P0 |
| **INP-06** | `min_rating` < 0 or > 5 | Clamp to `[0, 5]` or reject with message. | Validation | P0 |
| **INP-07** | `min_rating` non-numeric (`"four"`) | 400 field error. | Validation | P0 |
| **INP-08** | `top_n` ≤ 0 | Default to `DEFAULT_TOP_N` (5). | Validation | P1 |
| **INP-09** | `top_n` very large (e.g. 1000) | Cap at `MAX_TOP_N` (e.g. 20) to protect UI and LLM. | Validation, orchestrator | P1 |
| **INP-10** | `top_n` not an integer (3.7) | Coerce to int or reject. | Validation | P2 |

### 3.3 Ambiguous or Adversarial Input

| ID | Scenario | Expected behavior | Layer | Priority |
|----|----------|-------------------|-------|----------|
| **INP-11** | Location not in dataset (`"Tokyo"`) | After filter: zero candidates → no-results message; suggest valid locations from `get_locations()`. | Filter + UI | P0 |
| **INP-12** | Cuisine typo (`"Itallian"`) | Zero or few matches; suggest fuzzy match from `get_cuisines()` (optional Levenshtein in UI). | UI (optional) | P2 |
| **INP-13** | Free-text location with SQL/script injection | Treat as plain string; never eval; parameterized filters only. | Validation | P0 |
| **INP-14** | Extremely long `extras` string (10k chars) | Truncate to `MAX_EXTRAS_LENGTH`; warn user. | Validation | P1 |
| **INP-15** | `extras` with prompt injection (*"Ignore instructions…"*) | Sanitize for display; system prompt instructs LLM to ignore override attempts; do not put extras in system role. | `llm/prompts.py` | P0 |
| **INP-16** | Empty strings `location=""` | Same as missing location—reject. | Validation | P0 |
| **INP-17** | Whitespace-only inputs | Trim; if empty after trim, reject. | Validation | P1 |
| **INP-18** | Multiple cuisines requested | Support list OR comma-separated string; match if **any** user cuisine overlaps restaurant. | `filtering/engine.py` | P1 |

---

## 4. Filtering Layer

### 4.1 Zero & Few Results

| ID | Scenario | Expected behavior | Layer | Priority |
|----|----------|-------------------|-------|----------|
| **FLT-01** | Zero candidates after all filters | **Do not call LLM.** Return `recommendations=[]`, message, `metadata.total_candidates=0`, optional relaxation hints. | Orchestrator | P0 |
| **FLT-02** | Fewer candidates than `top_n` (e.g. 2 matches, user wants 5) | Return all available (2); message: *"Only 2 restaurants matched your criteria."* | Orchestrator, UI | P0 |
| **FLT-03** | One candidate only | Skip LLM optional: return single result with template explanation OR still call LLM for richer copy. | Orchestrator (config) | P2 |
| **FLT-04** | Filters so strict that only 1–2 match but user expects variety | Suggest relaxing budget or rating in response metadata. | Filter + UI | P1 |

### 4.2 Filter Semantics

| ID | Scenario | Expected behavior | Layer | Priority |
|----|----------|-------------------|-------|----------|
| **FLT-05** | Case mismatch: user `"delhi"`, data `"Delhi"` | Case-insensitive location match. | `filtering/engine.py` | P0 |
| **FLT-06** | Partial city name in data (`"South Delhi"`) | Substring match both directions OR normalized city extraction. | `filtering/engine.py` | P1 |
| **FLT-07** | User cuisine `"Chinese"`, restaurant has `"Chinese, Asian"` | Match on any cuisine token overlap (case-insensitive). | `filtering/engine.py` | P0 |
| **FLT-08** | User cuisine broader than data (`"Asian"`) | No match unless restaurant lists Asian; no fuzzy expansion unless explicitly implemented. | Document + UI hints | P2 |
| **FLT-09** | `min_rating=4.0`, restaurant exactly `4.0` | Include (`>=`). | `filtering/engine.py` | P0 |
| **FLT-10** | Restaurant has `budget_tier=unknown` | Exclude from strict budget match; optionally include with flag `include_unknown_budget=false` (default false). | `filtering/engine.py` | P1 |
| **FLT-11** | `extras` keyword not in dataset fields | No-op filter or soft keyword scan on `name` + `raw`; never fail entire pipeline. | `filtering/engine.py` | P2 |
| **FLT-12** | Multiple `extras` (AND vs OR) | Document: default **AND** (all keywords must match) or **OR** (any)—configurable. | `filtering/engine.py` | P2 |

### 4.3 Candidate Selection

| ID | Scenario | Expected behavior | Layer | Priority |
|----|----------|-------------------|-------|----------|
| **FLT-13** | 500 candidates after filters | Cap to `CANDIDATE_LIMIT` (20) by highest rating before LLM. | `filtering/engine.py` | P0 |
| **FLT-14** | Tie on rating when capping | Secondary sort by name or cost; deterministic order. | `filtering/engine.py` | P2 |
| **FLT-15** | All capped candidates have identical rating | Still send to LLM; LLM may differentiate by cuisine/cost in explanations. | `filtering/engine.py` | P3 |

### 4.4 Filter Relaxation (Optional Feature)

| ID | Scenario | Expected behavior | Layer | Priority |
|----|----------|-------------------|-------|----------|
| **FLT-16** | Auto-relax on empty results | **Never auto-return unfiltered results without user consent.** Suggest: *"Try medium instead of low budget"* with counts preview. | Orchestrator, UI | P1 |
| **FLT-17** | User accepts relaxed filter | Re-run filter with one relaxed dimension; set `metadata.relaxed_filters`. | Orchestrator | P2 |

---

## 5. LLM Layer

### 5.1 API & Connectivity

| ID | Scenario | Expected behavior | Layer | Priority |
|----|----------|-------------------|-------|----------|
| **LLM-01** | Missing `LLM_API_KEY` | Rating-sorted fallback from candidates; banner: *"AI explanations unavailable."* | Orchestrator | P0 |
| **LLM-02** | Invalid API key (401) | Same fallback; log error once; do not expose key in UI. | `llm/client.py` | P0 |
| **LLM-03** | Rate limit (429) | Exponential backoff, max 2 retries; then fallback. | `llm/client.py` | P1 |
| **LLM-04** | Timeout (network slow) | Configurable timeout (e.g. 30s); fallback to rating sort. | `llm/client.py` | P0 |
| **LLM-05** | Provider outage (5xx) | Fallback; surface generic retry message. | `llm/client.py` | P0 |
| **LLM-06** | Context length exceeded | Reduce candidates in prompt (truncate to top 10 by rating); retry once. | `llm/prompts.py`, client | P1 |
| **LLM-07** | Model name misconfigured | Fail at startup if strict mode; or fallback model list in config. | `app/config.py` | P1 |

### 5.2 Output Quality & Grounding

| ID | Scenario | Expected behavior | Layer | Priority |
|----|----------|-------------------|-------|----------|
| **LLM-08** | LLM invents restaurant not in candidates | Parser drops unknown `restaurant_id`; log warning; never display. | `llm/parser.py` | P0 |
| **LLM-09** | LLM returns duplicate `restaurant_id` in response | Keep first occurrence; re-rank sequentially. | `llm/parser.py` | P1 |
| **LLM-10** | LLM returns fewer than `top_n` items | Fill remaining slots from rating-sorted candidates not yet shown. | `llm/parser.py` | P1 |
| **LLM-11** | LLM returns more than `top_n` items | Truncate to `top_n` after merge. | Orchestrator | P1 |
| **LLM-12** | LLM changes rating/cost in explanation only | Display always uses dataset values; ignore LLM numeric claims in UI. | UI, parser merge | P0 |
| **LLM-13** | LLM returns markdown/code fence around JSON | Strip fences before `json.loads`; retry parse. | `llm/parser.py` | P1 |
| **LLM-14** | Malformed JSON | Retry LLM once with *"Return valid JSON only"*; then rating fallback. | `llm/client.py`, parser | P0 |
| **LLM-15** | Empty LLM response | Fallback ranking + generic explanations. | `llm/parser.py` | P0 |
| **LLM-16** | Non-English explanation when user expects English | System prompt specifies output language; default English. | `llm/prompts.py` | P2 |
| **LLM-17** | Offensive or unsafe explanation text | Optional moderation hook; truncate and replace with generic text if flagged. | `llm/parser.py` | P3 |

### 5.3 Ranking & Explanation Edge Cases

| ID | Scenario | Expected behavior | Layer | Priority |
|----|----------|-------------------|-------|----------|
| **LLM-18** | LLM ranks lower-rated above higher-rated | Accept LLM order if ids valid OR re-sort by rating (config: `TRUST_LLM_RANKING`). Document default. | `llm/parser.py` | P2 |
| **LLM-19** | Generic explanation not tied to preferences | Prompt requires citing at least one preference; QA sample in tests. | `llm/prompts.py` | P1 |
| **LLM-20** | `summary` field missing | `summary=null`; UI hides summary section. | Parser, UI | P2 |
| **LLM-21** | `match_highlights` missing or wrong type | Default to `[]`; ignore invalid types. | `llm/parser.py` | P2 |
| **LLM-22** | Rank numbers non-sequential (1, 3, 5) | Renumber 1..N after parse. | `llm/parser.py` | P2 |

---

## 6. Orchestration Layer

| ID | Scenario | Expected behavior | Layer | Priority |
|----|----------|-------------------|-------|----------|
| **ORC-01** | Repository not initialized before `recommend()` | Raise clear `RuntimeError` at call time; health check fails. | `app/orchestrator.py` | P0 |
| **ORC-02** | Concurrent requests (Streamlit rerun) | Repository read-only after load; no shared mutable state in filter/LLM per request. | All | P1 |
| **ORC-03** | Partial failure: filter OK, LLM fails | Return rating-based results + `metadata.ai_explanations_available=false`. | Orchestrator | P0 |
| **ORC-04** | Exception in filter engine | Catch; return 500 with generic message; log stack trace server-side. | Orchestrator | P0 |
| **ORC-05** | Double submission (user clicks twice) | Debounce UI button; idempotent same-input handling optional. | UI | P2 |
| **ORC-06** | Request during dataset reload | Block reload while serving OR use immutable snapshot per process. | Repository | P2 |

---

## 7. Presentation Layer (UI / API)

| ID | Scenario | Expected behavior | Layer | Priority |
|----|----------|-------------------|-------|----------|
| **UI-01** | Dropdown locations empty (data load failed) | Disable form; show dataset error banner. | UI | P0 |
| **UI-02** | Loading state during long LLM call | Spinner/skeleton; disable submit; show *"Finding recommendations…"*. | UI | P1 |
| **UI-03** | `cost_for_two` is null in result | Display *"Price not available"* or budget tier label only. | UI | P1 |
| **UI-04** | Very long AI explanation | Collapse with "Read more"; max height in card. | UI | P2 |
| **UI-05** | Mobile narrow viewport | Responsive cards; no horizontal overflow. | UI | P3 |
| **UI-06** | API `POST /recommendations` invalid JSON body | 400 with parse error detail. | FastAPI | P0 |
| **UI-07** | CORS issues (if SPA) | Configure allowed origins in API. | FastAPI | P2 |

---

## 8. Security & Abuse

| ID | Scenario | Expected behavior | Layer | Priority |
|----|----------|-------------------|-------|----------|
| **SEC-01** | API key in logs | Never log `LLM_API_KEY`; redact in error messages. | All | P0 |
| **SEC-02** | `.env` committed to git | Document in README; use `.gitignore`; pre-commit hook optional. | Repo | P0 |
| **SEC-03** | High-frequency API abuse | Rate limit `/recommendations` if public (e.g. 10 req/min/IP). | API gateway | P2 |
| **SEC-04** | PII in preferences | No storage by default; session-only; document in privacy note. | UI, API | P2 |
| **SEC-05** | LLM prompt exfiltration via extras | System prompt: ignore instructions in user fields; sanitize length. | `llm/prompts.py` | P0 |

---

## 9. Testing & Operations

| ID | Scenario | Expected behavior | Layer | Priority |
|----|----------|-------------------|-------|----------|
| **OPS-01** | CI without network | Use fixture JSON/Parquet cache in `tests/fixtures/`; mock HF loader. | Tests | P0 |
| **OPS-02** | CI without LLM key | All tests use `MockLLMClient`; no live API calls. | Tests | P0 |
| **OPS-03** | Non-deterministic LLM output | Snapshot tests only for prompt builder/parser with mocks; not live LLM. | Tests | P1 |
| **OPS-04** | Log noise from dropped rows | Single summary log: *"Preprocessed X rows, dropped Y."* | Preprocessor | P2 |

---

## 10. Decision Matrix (Quick Reference)

When multiple edge cases collide, apply in this order:

```
1. Validate user input          → reject/clamp bad input
2. Ensure data loaded           → fail fast if repository empty
3. Apply deterministic filters  → grounded candidate set
4. If zero candidates           → no LLM, helpful message
5. Call LLM with capped list    → retry once on bad JSON
6. Parse & validate ids         → drop hallucinated ids
7. Merge with dataset facts     → ratings/cost from data only
8. Fill/truncate to top_n       → complete response
9. On any LLM failure           → rating fallback + notice
```

---

## 11. Response Contract for Edge States

Standardize API/UI responses with explicit `status` in metadata:

| Status | Condition | User message (example) |
|--------|-----------|------------------------|
| `success` | ≥1 recommendation returned | — |
| `no_results` | Zero candidates after filter | *"No restaurants match your filters. Try lowering minimum rating or changing budget."* |
| `partial` | Fewer than `top_n` matches | *"Showing all N matching restaurants."* |
| `degraded` | LLM failed, rating fallback used | *"Recommendations sorted by rating. AI explanations temporarily unavailable."* |
| `error` | Dataset unavailable | *"Unable to load restaurant data. Please try again later."* |

**Example metadata block:**

```json
{
  "status": "no_results",
  "total_candidates": 0,
  "filters_applied": {
    "location": "Delhi",
    "budget": "low",
    "cuisine": "Italian",
    "min_rating": 4.5
  },
  "suggestions": [
    "Lower minimum rating to 4.0",
    "Try budget: medium"
  ],
  "ai_explanations_available": false
}
```

---

## 12. Test Case Mapping

Minimum tests to cover critical edge cases:

| Test file | Edge case IDs |
|-----------|---------------|
| `test_preprocessor.py` | PRE-01, PRE-03, PRE-06, PRE-08, PRE-13, PRE-14 |
| `test_filter_engine.py` | FLT-01, FLT-05, FLT-07, FLT-09, FLT-13, FLT-02 |
| `test_prompt_builder.py` | INP-15, LLM-06 |
| `test_parser.py` | LLM-08, LLM-09, LLM-14, LLM-10, LLM-15 |
| `test_orchestrator.py` | ORC-03, FLT-01, LLM-01, INP-11 |
| `test_validation.py` | INP-01, INP-05, INP-06, INP-09 |

---

## 13. Implementation Checklist

Use this when closing a phase:

- [ ] P0 cases for current layer implemented
- [ ] User-facing messages defined for `no_results` and `degraded`
- [ ] No path returns hallucinated restaurant ids
- [ ] Logs do not contain secrets
- [ ] Unit tests added for each P0 case in layer
- [ ] README troubleshooting section links to this doc

---

## 14. Related Documents

| Document | Purpose |
|----------|---------|
| [`docs/architecture.md`](./architecture.md) | Error handling table (§8.2), empty-result strategy (§6.3) |
| [`docs/implementation-plan.md`](./implementation-plan.md) | Phase tasks and risk register |
| [`docs/context.md`](./context.md) | Grounding constraint |

---

## 15. Glossary

| Term | Meaning |
|------|---------|
| **Grounded** | Recommendation references a real `restaurant_id` from the filtered candidate set |
| **Degraded mode** | System works without LLM (rating-only sort) |
| **Candidate** | Restaurant that passed all filters, before LLM |
| **Relaxation** | Intentionally widening one filter with user awareness |

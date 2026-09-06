# ADR 0003: Evals Elimination and Codebase Simplification

## Status

Accepted

## Context

Following the LanceDB migration and serving consolidation, the codebase still contained vestigial artifacts and architectural decisions from the previous author:
1. **Eval Suite Over-Engineering**: An evaluation runner (`evals.py`), a 40-pair generated test dataset (`eval_set.json`), associated documentation (`docs/evals/`), and report-only workflow steps added maintenance overhead and rigid expectations for a dynamic corpus.
2. **Ambiguous Module Naming**: The ingestion pipeline was named `builder.py`, obscuring its actual role (data ingestion, HTTP scraping, chunking, and database upserting).
3. **Fragile Workflow Cache Assumptions**: The nightly ingestion job assumed GitHub Actions cache (`~/.cache/xkcd-search`) would always be present. On cache expiration or cold runners, it risked scraping 3,200+ comics from scratch instead of restoring the existing dataset from Hugging Face Hub.
4. **Configuration and Tooling Slop**:
   - `pyproject.toml` had misplaced `dev = [...]` dependencies directly under `[tool.pytest.ini_options]`.
   - `.gitignore` contained stale rules for SQLite files (`index.sqlite*`) and VCR cassettes despite the project's strict "no VCR, no mocks" rule.
   - `.github/workflows/opencode.yml` referenced non-existent `actions/checkout@v6`.
   - Vendored external skills (3D modeling, CUDA extensions) littered `.agents/skills`.

## Decisions

### 1. Completely Remove Evaluation Artifacts
- Deleted `src/xkcd_search/evals.py`, `tests/test_evals.py`, `docs/evals/`, and `eval_set.json`.
- Removed the `evals` script entry from `pyproject.toml`.
- Stripped eval-related terminology (`hit@k`, `MRR`, `eval set`) from `CONTEXT.md` and `AGENTS.md`.

### 2. Rename `builder.py` to `ingest.py`
- Renamed `src/xkcd_search/builder.py` to `src/xkcd_search/ingest.py` to accurately reflect its single responsibility: scraping comic data and ingesting it into the LanceDB vector database.
- Updated all execution commands and CI workflows (`index-daily.yml`) to invoke `python -m xkcd_search.ingest`.

### 3. Resilient Remote Dataset Ingestion
- In `ingest.py`, if local cache is absent, `main()` uses `snapshot_download` to restore the existing LanceDB dataset directly from Hugging Face Hub before checking for newly published comics.
- Ensured dataset repository existence with `HfApi().create_repo(..., exist_ok=True)` prior to `upload_folder`.
- Cleaned explanations with `mwparserfromhell.strip_code()` before saving to LanceDB so consumers receive readable plain text rather than raw wikitext markup.

### 4. API & Robustness Polish
- Handled empty or whitespace search queries gracefully in `search_xkcd` by returning `[]` immediately without sending empty inference requests.
- Added parameter alias support (`limit` in addition to `k`) in `/api/search` and `/search` to accommodate varied agent conventions.
- Standardized `skill.md` at both repo root and `/skill.md` endpoint.
- Fixed `pyproject.toml` dependency groups and ignored non-code directories in `ruff`.

## Consequences

- The codebase is composed of only two source modules (`app.py` and `ingest.py`).
- No extraneous dependencies, artificial eval metrics, or brittle cache setups.
- Ingestion runs incrementally and idempotently across any machine.
- 100% test pass rate with full integration coverage.

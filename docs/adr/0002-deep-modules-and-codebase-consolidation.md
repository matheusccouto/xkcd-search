# ADR 0002: Deep Modules and Codebase Consolidation

## Status

Accepted

## Context

Prior to this change, the `xkcd_search` package suffered from shallow module fragmentation:
1. `app.py` was a 20-line pass-through file that merely imported `build_app()` from `server.py`.
2. `search_app.py` was a thin adapter around Gradio that imported `search_xkcd` from `server.py`.
3. `server.py` imported `search_app.py` to build the Gradio interface and compose the ASGI application.
4. This circular import tangle obscured where the application was actually defined and forced developers and tests to navigate three shallow files for one cohesive service.

## Decisions

### 1. Consolidate Serving into a Single Deep Module: `app.py`
In accordance with deep module design principles:
- **Small Interface**: Callers and deployment environments interact with `app` (the ASGI application), `mcp` (the FastMCP instance), and `search_xkcd(query, k)` (the core search function).
- **Deep Implementation**: All complexity—LanceDB connection pooling, Hugging Face Serverless Inference vector computation, FastMCP protocol handling, REST API routing (`/api/search`), Agent Skill serving (`/skill.md`), and Gradio card rendering—is encapsulated inside `src/xkcd_search/app.py`.
- **Eliminate Pass-Throughs**: Deleted `src/xkcd_search/server.py` and `src/xkcd_search/search_app.py`.

### 2. Two Cohesive Domain Modules
The codebase is reduced to two focused modules, each with high depth and clear purpose:
1. `src/xkcd_search/app.py`: The live application module (Web UI, FastMCP, REST API, Agent Skill, and retrieval engine).
2. `src/xkcd_search/ingest.py`: The ingestion pipeline (fetches xkcd and explainxkcd, generates chunks, computes embeddings, and updates the LanceDB dataset on Hugging Face).

### 3. Consolidated Test Suite
Consolidated test files into two test modules directly mirroring functionality: `tests/test_app.py` (comprehensive app, MCP, REST, UI tests) and `tests/test_index_daily_workflow.py` (contract tests for the scheduled GitHub Action).

## Consequences

- **Pros**:
  - High locality: Any changes to endpoints, UI layout, or search logic happen in one place.
  - Zero circular dependencies.
  - Running `python -m xkcd_search.app` runs the application directly where it is defined.
  - Simpler, cleaner codebase that is significantly easier to understand and maintain.
- **Cons**:
  - `app.py` is slightly longer (~160 lines), but remains well within readable, cohesive bounds.

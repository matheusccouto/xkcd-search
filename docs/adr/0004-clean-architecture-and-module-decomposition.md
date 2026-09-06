# ADR 0004: Clean Architecture and Module Decomposition

## Status

Accepted

## Context

Consolidating everything into `app.py` created unnecessary coupling between distinct domain responsibilities:
1. Core retrieval (LanceDB queries and vector encoding).
2. Protocol serving (FastMCP tool registration and FastAPI REST endpoints).
3. Web user interface (Gradio Blocks and HTML rendering).

Additionally, tests were overly brittle and complex (inspecting private Gradio layout trees and JSON-RPC dictionaries), and `app.py` relied on global table variables.

## Decisions

### 1. Three Clear Application Modules
Decomposed `src/xkcd_search` into focused, junior-engineer-friendly modules:
- `src/xkcd_search/search.py`: Encapsulates `SearchEngine`, query vector encoding with Hugging Face Serverless Inference, and LanceDB similarity search. Eliminates global state in favor of an explicit, dependency-injectable `SearchEngine`.
- `src/xkcd_search/server.py`: Encapsulates FastMCP server (`search_xkcd` tool) and FastAPI REST endpoints (`/api/search`, `/search`, `/skill.md`).
- `src/xkcd_search/app.py`: Encapsulates Gradio web UI and mounts it to the ASGI root (`/`).
- `src/xkcd_search/ingest.py`: Encapsulates data scraping, chunking, and nightly dataset upload to Hugging Face Datasets.

### 2. Streamlined Workflows & Script CLI
- Added `[project.scripts] xkcd-ingest = "xkcd_search.ingest:main"` to `pyproject.toml`.
- Updated GitHub Actions to `actions/checkout@v6`.
- Simplified `.github/workflows/index-daily.yml` by removing redundant `uv sync` and cache restore/save steps, as LanceDB is directly restored from Hugging Face Hub via `snapshot_download`.
- Added clear explanatory comments for the HF Space restart step.

### 3. Test Simplification
- Replaced brittle Gradio internal AST inspection with direct component instantiation checks and functional endpoint tests.
- Uses `SearchEngine(table=...)` fixture directly, eliminating monkeypatching of global state.

### 4. Ruff "ALL" Compliance
- Activated `select = ["ALL"]` in `pyproject.toml`.
- Resolved all type annotations, docstring requirements, and error messages across the repository.
- Limited ignores strictly to formatter-incompatible rules (`COM812`, `ISC001`), mutually exclusive pydocstyle rules (`D203`, `D213`), copyright headers (`CPY001`), and `S101` in `tests/*`.

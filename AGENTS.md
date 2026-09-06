# xkcd-search-mcp

Semantic search over xkcd and explainxkcd, reachable four ways:
1. Gradio search web app at `/`
2. Remote FastMCP endpoint at `/mcp` (`search_xkcd`)
3. Unauthenticated REST API at `/api/search?q={query}&k={count}`
4. Agent Skill at `.agents/skills/xkcd-search/SKILL.md`

Corpus is indexed in LanceDB and hosted on Hugging Face Datasets (`couto/xkcd`).
Live endpoint: `https://couto-xkcd-search.hf.space`.

## Layout

- `src/xkcd_search/search.py`: Core retrieval engine (`SearchEngine`), embedding generation, and LanceDB queries.
- `src/xkcd_search/app.py`: FastMCP server (`search_xkcd`), REST endpoint (`/api/search`), Gradio web UI (`/`), and ASGI entry point.
- `src/xkcd_search/ingest.py`: Scraping xkcd + explainxkcd, computing embeddings, and publishing to Hugging Face.
- `.agents/skills/xkcd-search/SKILL.md`: Agent skill definition (installable via `npx skills add`).
- `tests/test_app.py`: Core integration tests covering search, UI, MCP, and REST API.
- `evals/`: Retrieval quality benchmark suite (`test_retrieval.py`, `sampler.py`, `dataset.json`).
- `.github/workflows/index-daily.yml`: Nightly build, upload to HF dataset, and Space redeploy.

## Commands

- `uv sync`: Install dependencies.
- `uv run pytest`: Run test suite.
- `uv run pytest evals/`: Run retrieval evaluation benchmark suite (local or remote with `XKCD_TEST_URL`).
- `uv run python -m evals.test_retrieval`: Print aggregated evaluation metrics report (`--url` for remote).
- `uv run python -m evals.sampler --count 3`: Sample random comics from LanceDB to template new entries.
- `uvx ruff check . && uvx ruff format --check . && uvx ty check`: Lint and typecheck.
- `uv run xkcd-ingest`: Rebuild or update LanceDB index.
- `uv run python -m xkcd_search.app`: Run local server on port 7860.

## Core Rules

- **Fail fast and loudly**: Do not swallow errors or boot empty fallback tables. If data is missing or connection fails, let it raise.
- **Attribution**: Every search result must include `number`, `title`, and `url` to comply with CC BY-SA 3.0.
- **Integration tests**: Tests hit real data and test fixtures. No mocks, no VCR cassettes.
- **Async tests**: Pytest runs with `asyncio_mode = "auto"`. Write `async def test_...`.

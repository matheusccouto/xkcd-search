# xkcd-search-mcp

## Commands

- `uv run pytest`: Run test suite.
- `uv run --env-file .env pytest evals/`: Run retrieval benchmark suite.
- `uvx ruff check .`: Lint code.
- `uvx ruff format --check .`: Check formatting.
- `uvx ty check`: Typecheck.
- `uv run xkcd-ingest`: Ingest missing comics into LanceDB.
- `uv run -m xkcd_search.app`: Run local server on port 7860.

## Standards

- Code is read far more often than written; optimize for readability and clear reading sequence.
- Prefer explicit and simple over clever or nested abstractions.
- Fail fast and loudly; never swallow errors or add silent fallbacks.
- Test with real data and fixtures only; no mocks.
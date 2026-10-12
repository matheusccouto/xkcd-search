---
title: xkcd-search
emoji: 🔎
sdk: docker
app_port: 7860
---

# xkcd-search

Semantic search over xkcd and explainxkcd.com via LanceDB and Hugging Face Serverless Inference.

Live endpoint: `https://couto-xkcd-search.hf.space`

## Interfaces

- **Web UI**: [`/`](https://couto-xkcd-search.hf.space)
- **MCP Server**: [`/mcp`](https://couto-xkcd-search.hf.space/mcp) (`search(query, k=5)`)
- **REST API**: `GET /api/search?q={query}&k={count}`
- **Agent Skill**: `npx skills add matheusccouto/xkcd-search-mcp`

## Development

```bash
uv sync                                                       # Install dependencies
uv run pytest                                                 # Run test suite
uv run --env-file .env pytest evals/                          # Run retrieval benchmark
uvx ruff check . && uvx ruff format --check . && uvx ty check  # Lint and typecheck
uv run xkcd-ingest                                            # Update index
uv run -m xkcd_search.app                                     # Start server on :7860
```

## Attribution

- **explainxkcd**: [CC BY-SA 3.0](https://creativecommons.org/licenses/by-sa/3.0/).
- **xkcd**: Randall Munroe, [CC BY-NC 2.5](https://xkcd.com/license.html).
- **Code**: [Apache 2.0](./LICENSE).

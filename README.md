---
title: xkcd-search
emoji: 🔎
colorFrom: blue
colorTo: indigo
sdk: docker
app_port: 7860
pinned: false
---

# xkcd-search

Semantic search for xkcd comics across the full 3,000+ comic archive plus explainxkcd.com.

Reachable four ways:
1. **Web UI**: [https://couto-xkcd-search.hf.space](https://couto-xkcd-search.hf.space) (browse comic cards)
2. **REST API**: `GET https://couto-xkcd-search.hf.space/api/search?q={query}&k={count}` (unauthenticated JSON API)
3. **Agent Skill**: `.agents/skills/xkcd-search/SKILL.md` (installable via `npx skills add matheusccouto/xkcd-search-mcp`)
4. **MCP Endpoint**: `https://couto-xkcd-search.hf.space/mcp` (for Claude Desktop, Cursor, and FastMCP clients)

## REST API

An unauthenticated endpoint for scripts, tools, and AI agents:

```bash
curl -s "https://couto-xkcd-search.hf.space/api/search?q=standards+universal&k=2"
```

Response JSON:

```json
[
  {
    "number": 927,
    "title": "Standards",
    "url": "https://xkcd.com/927/",
    "image_url": "https://imgs.xkcd.com/comics/standards.png",
    "alt_text": "Fortunately, the charging one has been solved now that we've all standardized on mini-USB. USB 3.0 mini-B, that is. No, wait, micro-B. Ok, listen:...",
    "transcript": "...",
    "explanation": "..."
  }
]
```

## MCP Tool

Connect any MCP client to `https://couto-xkcd-search.hf.space/mcp`:

```python
search_xkcd(query: str, k: int = 5) -> list[dict]
```

Semantic top-K lookup. Every result is a dict with `number`, `title`, `url`, `image_url`, `alt_text`, `transcript`, and `explanation`. Cite `url` when referencing a comic.

## How it works

1. A daily GitHub Actions job (`.github/workflows/index-daily.yml`) fetches new comics and explainxkcd wikitext.
2. Chunks are embedded with `BAAI/bge-small-en-v1.5` via Hugging Face Serverless Inference.
3. Records are stored in a **LanceDB** table and published directly to Hugging Face Datasets (`couto/xkcd`).
4. The workflow calls the Hugging Face Spaces restart API to redeploy.
5. The Space connects to the Lance dataset and serves the web UI at `/`, FastMCP at `/mcp`, and REST API at `/api/search`.

## Local development

```bash
uv sync
uv run pytest                                   # in-process integration tests
uv run xkcd-ingest                             # build/update local LanceDB table
uv run python -m xkcd_search.app                # run composed app (UI at /, MCP at /mcp, REST at /api/search)
uv run fastmcp dev src/xkcd_search/app.py:mcp # open the FastMCP inspector
```

## Testing

```bash
uv run pytest                                             # in-process integration
XKCD_TEST_URL=https://couto-xkcd-search.hf.space/mcp \
    uv run pytest tests/test_app.py                       # hit live Space
```

## Attribution and licensing

Search results are indexed from explainxkcd.com, licensed under [CC BY-SA 3.0](https://creativecommons.org/licenses/by-sa/3.0/). When citing a result, link back to the comic's `url` and credit the explainxkcd contributors.

Comic images remain the work of Randall Munroe, licensed under [CC BY-NC 2.5](https://xkcd.com/license.html).

The source code in this repository is licensed under [Apache 2.0](./LICENSE).

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

Semantic search for the complete xkcd archive (3,000+ comics) plus explainxkcd.com. Backed by LanceDB and Hugging Face Serverless Inference.

Reachable four ways:
- **Web UI**: [https://couto-xkcd-search.hf.space](https://couto-xkcd-search.hf.space)
- **REST API**: `GET /api/search?q={query}&k={count}`
- **MCP Server**: `https://couto-xkcd-search.hf.space/mcp`
- **Agent Skill**: `npx skills add matheusccouto/xkcd-search-mcp`

## Interfaces & Installation

### 1. REST API
Unauthenticated endpoint for scripts, tools, and agents:

```bash
curl -s "https://couto-xkcd-search.hf.space/api/search?q=standards+universal&k=1"
```

```json
[
  {
    "number": 927,
    "title": "Standards",
    "url": "https://xkcd.com/927/",
    "image_url": "https://imgs.xkcd.com/comics/standards.png",
    "alt_text": "Fortunately, the charging one has been solved...",
    "transcript": "...",
    "explanation": "..."
  }
]
```

### 2. Model Context Protocol (MCP)
Add the remote MCP server to your client.

**Claude Desktop** (`claude_desktop_config.json`):
```json
{
  "mcpServers": {
    "xkcd": {
      "url": "https://couto-xkcd-search.hf.space/mcp"
    }
  }
}
```

**Cursor** (`.cursor/mcp.json`):
```json
{
  "mcpServers": {
    "xkcd": {
      "url": "https://couto-xkcd-search.hf.space/mcp"
    }
  }
}
```

**FastMCP CLI**:
```bash
fastmcp run https://couto-xkcd-search.hf.space/mcp
```

Tool provided:
- `search_xkcd(query: str, k: int = 5) -> list[dict]`

### 3. Agent Skill
Install the skill into agentic workflows:

```bash
npx skills add matheusccouto/xkcd-search-mcp
```

### 4. Web UI
Visit [https://couto-xkcd-search.hf.space](https://couto-xkcd-search.hf.space) to search and view comics directly in your browser.

## How it works

1. **Scraping**: A nightly workflow checks for new comics on xkcd.com and explanations on explainxkcd.com.
2. **Embedding**: Text chunks are embedded with `BAAI/bge-small-en-v1.5` via Hugging Face Serverless Inference.
3. **Storage**: LanceDB dataset hosted on Hugging Face Datasets (`couto/xkcd`).
4. **Serving**: A Docker Space runs FastMCP, Gradio, and Starlette on port 7860.

## Local Development

```bash
# Setup
uv sync

# Run tests
uv run pytest

# Test against live Space
XKCD_TEST_URL=https://couto-xkcd-search.hf.space/mcp uv run pytest

# Lint and type check
uvx ruff check . && uvx ruff format --check . && uvx ty check

# Run local server
uv run python -m xkcd_search.app
```

## Evaluations

Run retrieval quality benchmarks over natural queries against the evaluation corpus:

```bash
# Run pytest evaluation suite
uv run pytest evals/

# Run benchmark report (Hit@1, Hit@3, Hit@5, MRR)
uv run python -m evals.test_retrieval

# Discover random explainxkcd pages to add new entries to dataset.json
uv run python -m evals.sampler --count 3
```

## Attribution and Licensing

- **explainxkcd**: Content is licensed under [CC BY-SA 3.0](https://creativecommons.org/licenses/by-sa/3.0/). When citing results, link back to the comic's `url`.
- **xkcd**: Comics are created by Randall Munroe and licensed under [CC BY-NC 2.5](https://xkcd.com/license.html).
- **Source code**: Licensed under [Apache 2.0](./LICENSE).

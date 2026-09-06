---
name: xkcd-search
description: Semantic search over the xkcd comic archive. Use when looking for relevant xkcd comics, numbers, explanations, alt text, or transcripts based on concepts, topics, or punchlines.
---

# xkcd Search Skill

Semantic search across the entire xkcd archive (3,000+ strips), including full transcripts and explainxkcd explanations.

## Usage

### 1. HTTP REST API (Unauthenticated)

Endpoint: `https://couto-xkcd-search.hf.space/api/search`

Query parameters:
- `q` (string, required): Natural language search query (e.g., `"universal standards"`, `"python flying"`, `"sql injection"`)
- `k` (integer, optional, default: `5`, max: `20`): Number of comics to return

#### Curl Example:
```bash
curl -s "https://couto-xkcd-search.hf.space/api/search?q=python+flying&k=3"
```

#### JSON Response Schema:
```json
[
  {
    "number": 353,
    "title": "Python",
    "url": "https://xkcd.com/353/",
    "image_url": "https://imgs.xkcd.com/comics/python.png",
    "alt_text": "I wrote 20 short programs in Python yesterday. It was wonderful. Perl, I'm leaving you.",
    "transcript": "...",
    "explanation": "..."
  }
]
```

### 2. MCP Endpoint

If connecting via Model Context Protocol:
- Endpoint: `https://couto-xkcd-search.hf.space/mcp`
- Tool: `search_xkcd(query: str, k: int = 5)`
- Returns list of matching comic objects.

### 3. Attribution
Always cite the comic's `url` in user responses to fulfill CC BY-SA 3.0 attribution.

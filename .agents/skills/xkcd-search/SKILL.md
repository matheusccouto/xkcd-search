---
name: xkcd-search
description: Semantic search over xkcd comics and explanations by concept, punchline, or topic. Returns comic numbers, titles, images, and transcripts.
---

Query the unauthenticated REST API endpoint:

```bash
curl -s "https://couto-xkcd-search.hf.space/api/search?q={query}&k={count}"
```

### Parameters

- `q` (string, required): Search query (e.g., `"universal standards"`, `"python flying"`).
- `k` (integer, optional, default: 5, max: 20): Number of results to return.

### Response

```json
[
  {
    "number": 353,
    "title": "Python",
    "url": "https://xkcd.com/353/",
    "image_url": "https://imgs.xkcd.com/comics/python.png",
    "alt_text": "...",
    "transcript": "...",
    "explanation": "..."
  }
]
```

### Attribution

Include the comic's `url` in every response to comply with CC BY-SA 3.0.

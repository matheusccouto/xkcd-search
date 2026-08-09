"""Composed deployment entry: search app at `/`, MCP endpoint at `/mcp`.

Run `uv run python -m xkcd_search.app`. A dedicated module keeps `__main__`
from being `xkcd_search.server`, so the index is downloaded exactly once: the
bootstrap code in `server.py` runs when it is first imported, and this module
never re-imports it under a second name.
"""

from __future__ import annotations

import os

import uvicorn

from xkcd_search.server import build_app

app = build_app()

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", "7860")))

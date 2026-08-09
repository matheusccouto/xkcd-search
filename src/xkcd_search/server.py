"""FastMCP server exposing `search_xkcd`.

On boot, downloads the latest `index.sqlite` GitHub Release asset and opens a
read-only SQLite connection. No polling: the nightly indexer publishes a new
Release and calls the HF Spaces restart API, which restarts this process and
re-downloads the fresh artifact.

`build_app()` composes this MCP endpoint at `/mcp` together with the search
app at `/` into one ASGI app; the deployed boot path runs that composed app.
"""

from __future__ import annotations

import os
import sqlite3
import sys
from typing import Any

from fastmcp import FastMCP
from starlette.types import ASGIApp

from xkcd_search.builder import INDEX_PATH, encode, new_client, open_connection, query_top_k

GITHUB_REPO = "matheusccouto/xkcd-search-mcp"
RELEASES_API = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"

mcp = FastMCP("xkcd-search")
_conn: sqlite3.Connection | None = None


def _download_index() -> None:
    """Fetch the latest `index.sqlite` Release asset into INDEX_PATH."""
    with new_client(timeout=60.0, follow_redirects=True) as client:
        resp = client.get(RELEASES_API)
        resp.raise_for_status()
        for asset in resp.json().get("assets", []):
            if asset.get("name") == "index.sqlite":
                INDEX_PATH.parent.mkdir(parents=True, exist_ok=True)
                tmp = INDEX_PATH.with_suffix(".tmp")
                with client.stream("GET", asset["browser_download_url"]) as r:
                    r.raise_for_status()
                    with tmp.open("wb") as f:
                        for chunk in r.iter_bytes(1 << 20):
                            f.write(chunk)
                tmp.rename(INDEX_PATH)
                return
        raise RuntimeError(f"no 'index.sqlite' asset in latest release of {GITHUB_REPO}")


@mcp.tool
def search_xkcd(query: str, k: int = 5) -> list[dict[str, Any]]:
    """Semantic search over xkcd comics, ranked by relevance to `query`.

    Returns up to `k` comics, each with `number`, `title`, `url`, `image_url`,
    `alt_text`, `transcript`, and `explanation`. Cite the `url` when referencing
    a comic; explanations come from explainxkcd.com (CC BY-SA 3.0).
    """
    assert _conn is not None, "index not loaded"
    k = max(1, min(int(k), 20))
    numbers = query_top_k(_conn, encode([query])[0], k)
    if not numbers:
        return []
    placeholders = ",".join("?" * len(numbers))
    sql = (
        "SELECT number, title, url, image_url, alt_text, transcript, explanation "
        f"FROM comics WHERE number IN ({placeholders})"
    )
    rows = _conn.execute(sql, numbers).fetchall()
    by_number = {r["number"]: r for r in rows}
    return [dict(by_number[n]) for n in numbers if n in by_number]


def build_app() -> ASGIApp:
    """Compose the search app at `/` and the MCP endpoint at `/mcp` into one ASGI app.

    Reuses the module-level `mcp` object and index connection. `gradio` is
    imported only here, so server boot and the MCP test suite never pay its
    import cost.
    """
    import gradio as gr
    from fastapi import FastAPI
    from starlette.routing import Route

    from xkcd_search.search_app import build_ui

    mcp_http_app = mcp.http_app(path="/mcp")
    ui = build_ui()
    app = FastAPI(
        lifespan=mcp_http_app.lifespan,
        docs_url=None,
        openapi_url=None,
        redoc_url=None,
    )
    # Register /mcp before mount_gradio_app mounts at "/": the "/" mount matches
    # every path, so only registration order gives /mcp precedence.
    app.router.routes.append(Route("/mcp", endpoint=mcp_http_app))
    return gr.mount_gradio_app(app, ui, path="/")


if "pytest" not in sys.modules and os.getenv("XKCD_SKIP_BOOTSTRAP") != "1":
    if not INDEX_PATH.exists():
        _download_index()
    _conn = open_connection(INDEX_PATH, read_only=True)

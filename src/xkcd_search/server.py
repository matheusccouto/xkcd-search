"""FastMCP server exposing xkcd semantic search as an MCP tool and REST endpoint."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from fastmcp import FastMCP
from starlette.concurrency import run_in_threadpool
from starlette.responses import JSONResponse

from xkcd_search.index import SearchIndex

if TYPE_CHECKING:
    from starlette.requests import Request

DEFAULT_K = 5

mcp = FastMCP("xkcd-search")
search_index = SearchIndex()


@mcp.tool(name="search")
def search_tool(query: str, k: int = DEFAULT_K) -> list[dict[str, Any]]:
    """Semantic search over xkcd comics, ranked by relevance."""
    comics = search_index.search(query, k=k)
    return [c.to_dict() for c in comics]


@mcp.custom_route("/api/search", methods=["GET"])
async def search_api(request: Request) -> JSONResponse:
    """Return ranked search results as JSON."""
    query = request.query_params.get("q", "")
    try:
        k = int(request.query_params.get("k", DEFAULT_K))
    except ValueError:
        k = DEFAULT_K
    comics = await run_in_threadpool(search_index.search, query, k=k)
    return JSONResponse([c.to_dict() for c in comics])

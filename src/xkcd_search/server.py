"""FastMCP and REST API server for xkcd search."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from fastmcp import FastMCP
from starlette.responses import JSONResponse

from xkcd_search.search import SearchEngine

if TYPE_CHECKING:
    from starlette.applications import Starlette
    from starlette.requests import Request


def create_server(engine: SearchEngine | None = None) -> tuple[FastMCP, Starlette]:
    """Create FastMCP server and HTTP application backed by SearchEngine."""
    search_engine = engine or SearchEngine()

    mcp = FastMCP("xkcd-search")

    @mcp.tool(name="search_xkcd")
    def search_tool(query: str, k: int = 5) -> list[dict[str, Any]]:
        """Semantic search over xkcd comics, ranked by relevance."""
        return search_engine.search(query, k=k)

    @mcp.custom_route("/api/search", methods=["GET"])
    @mcp.custom_route("/search", methods=["GET"])
    async def search_api(request: Request) -> JSONResponse:
        query = request.query_params.get("q", "")
        k_val = int(request.query_params.get("k", "5"))
        return JSONResponse(search_engine.search(query, k=k_val))

    return mcp, mcp.http_app(path="/mcp")

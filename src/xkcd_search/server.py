"""FastMCP server exposing xkcd semantic search as an MCP tool and REST endpoint."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from fastmcp import FastMCP
from starlette.responses import JSONResponse

from xkcd_search.retriever import XKCDRetriever

if TYPE_CHECKING:
    from starlette.requests import Request

DEFAULT_K = 5

mcp = FastMCP("xkcd-search")
retriever = XKCDRetriever()


@mcp.tool(name="search")
def search_tool(query: str, k: int = DEFAULT_K) -> list[dict[str, Any]]:
    """Semantic search over xkcd comics, ranked by relevance."""
    return [doc.metadata for doc in retriever.invoke(query, k=k)]


@mcp.custom_route("/api/search", methods=["GET"])
async def search_api(request: Request) -> JSONResponse:
    """Return ranked search results as JSON."""
    query = request.query_params.get("q", "")
    k = int(request.query_params.get("k", DEFAULT_K))
    return JSONResponse([doc.metadata for doc in retriever.invoke(query, k=k)])

"""Tests for xkcd search: retrieval, MCP, REST, and UI."""

from __future__ import annotations

import os
from http import HTTPStatus
from typing import TYPE_CHECKING

import httpx
import pytest
from fastmcp import Client

from xkcd_search.retriever import XKCDRetriever

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from fastmcp import FastMCP
    from starlette.applications import Starlette

OVERTON_COMIC_NUMBER = 3230


@pytest.fixture
async def mcp_client(mcp_server: FastMCP | str) -> AsyncIterator[Client]:
    """Async MCP client over the in-memory server or remote URL."""
    auth = (
        "oauth" if isinstance(mcp_server, str) and "fastmcp.app" in mcp_server else None
    )
    async with Client(mcp_server, auth=auth) as client:
        yield client


@pytest.fixture
async def http_client(
    composed_app: Starlette | None,
) -> AsyncIterator[httpx.AsyncClient]:
    """Async httpx client over composed app, or remote URL."""
    if composed_app is None:
        transport = None
        base_url = os.getenv("XKCD_TEST_URL", "").removesuffix("/mcp")
    else:
        transport = httpx.ASGITransport(app=composed_app)
        base_url = "http://test"
    async with httpx.AsyncClient(
        transport=transport, base_url=base_url, timeout=30.0
    ) as client:
        yield client


async def test_search_ranks_relevant_comic_first(retriever: XKCDRetriever) -> None:
    """Ensure search ranks the relevant comic first with attribution."""
    hit = retriever.invoke("overton window politics", k=3)[0].metadata
    assert hit["number"] == OVERTON_COMIC_NUMBER
    assert hit["title"] == "Overton"
    assert hit["url"] == f"https://xkcd.com/{OVERTON_COMIC_NUMBER}/"


async def test_search_respects_k(retriever: XKCDRetriever) -> None:
    """Ensure search respects the k parameter."""
    assert len(retriever.invoke("exploits of a mom sql", k=1)) == 1


async def test_empty_query_returns_empty_list(retriever: XKCDRetriever) -> None:
    """Ensure empty or whitespace queries return an empty list immediately."""
    assert retriever.invoke("") == []
    assert retriever.invoke("   ") == []


async def test_invalid_lance_uri_fails_loudly() -> None:
    """Ensure a bad LanceDB URI raises loudly."""
    r = XKCDRetriever(uri="/nonexistent/invalid/path/that/does/not/exist")
    with pytest.raises((ValueError, OSError)):
        _ = r.table


async def test_mcp_search_tool(mcp_client: Client) -> None:
    """Ensure MCP server advertises and executes the search tool."""
    tools = await mcp_client.list_tools()
    assert [tool.name for tool in tools] == ["search"]
    result = await mcp_client.call_tool(
        "search", {"query": "overton window politics", "k": 2}
    )
    assert result.data[0]["number"] == OVERTON_COMIC_NUMBER


async def test_rest_api_search_endpoint(http_client: httpx.AsyncClient) -> None:
    """Ensure REST API search endpoint returns JSON results."""
    resp = await http_client.get("/api/search?q=overton+window&k=2")
    assert resp.status_code == HTTPStatus.OK
    assert resp.json()[0]["number"] == OVERTON_COMIC_NUMBER


async def test_root_serves_gradio_ui(http_client: httpx.AsyncClient) -> None:
    """Ensure root path serves the Gradio interface."""
    resp = await http_client.get("/")
    assert resp.status_code == HTTPStatus.OK
    assert "xkcd search" in resp.text

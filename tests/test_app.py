"""Tests for xkcd search: search engine, web UI, MCP, and REST API."""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING

import httpx
import pytest

from xkcd_search.app import build_ui, render_cards
from xkcd_search.ingest import open_or_create_table
from xkcd_search.search import SearchEngine

if TYPE_CHECKING:
    from collections.abc import AsyncIterator
    from pathlib import Path

    from fastmcp import Client
    from starlette.applications import Starlette

OVERTON_COMIC_NUMBER = 3230
HTTP_OK = 200
REQUESTED_COUNT = 1
SEARCH_TOP_K = 3


@asynccontextmanager
async def _composed_client(app: Starlette | None) -> AsyncIterator[httpx.AsyncClient]:
    """Provide an httpx.AsyncClient over composed app with lifespan running."""
    if app is None:
        base_url = os.getenv("XKCD_TEST_URL", "").removesuffix("/mcp")
        async with httpx.AsyncClient(base_url=base_url, timeout=30.0) as client:
            yield client
    else:
        transport = httpx.ASGITransport(app=app)
        async with (
            app.router.lifespan_context(app),
            httpx.AsyncClient(transport=transport, base_url="http://test") as client,
        ):
            yield client


def test_search_ranks_relevant_comic_first(search_engine: SearchEngine) -> None:
    """Ensure search ranks relevant comic first."""
    results = search_engine.search("overton window politics", k=SEARCH_TOP_K)
    assert len(results) >= 1
    assert results[0]["number"] == OVERTON_COMIC_NUMBER
    assert results[0]["url"] == f"https://xkcd.com/{OVERTON_COMIC_NUMBER}/"
    assert results[0]["title"] == "Overton"
    assert results[0]["image_url"]
    assert results[0]["explanation"]


def test_search_returns_requested_count(search_engine: SearchEngine) -> None:
    """Ensure search respects k parameter."""
    results = search_engine.search("exploits of a mom sql", k=REQUESTED_COUNT)
    assert len(results) == REQUESTED_COUNT
    assert results[0]["url"].startswith("https://xkcd.com/")


def test_search_empty_query_returns_empty_list(search_engine: SearchEngine) -> None:
    """Ensure empty or whitespace queries return an empty list immediately."""
    assert search_engine.search("") == []
    assert search_engine.search("   ") == []


def test_search_empty_index_returns_no_matches(tmp_path: Path) -> None:
    """Ensure searching an empty table returns no matches without crashing."""
    empty_table = open_or_create_table(tmp_path / "empty_lance")
    engine = SearchEngine(table=empty_table)
    assert engine.search("definitely not a comic") == []


def test_invalid_lance_uri_fails_loudly() -> None:
    """Ensure non-existent local URI raises loudly."""
    engine = SearchEngine(uri="/nonexistent/invalid/path/that/does/not/exist")
    with pytest.raises((ValueError, OSError)):
        _ = engine.table


def test_render_cards_renders_clickable_image(search_engine: SearchEngine) -> None:
    """Ensure rendered cards include image and anchor link."""
    html_out = render_cards(
        "overton window politics", k=REQUESTED_COUNT, engine=search_engine
    )
    assert "<img" in html_out
    assert ">Overton</a>" not in html_out
    assert f"#{OVERTON_COMIC_NUMBER}" not in html_out


def test_render_cards_empty_query_is_noop(search_engine: SearchEngine) -> None:
    """Ensure empty query returns empty string."""
    assert render_cards("", engine=search_engine) == ""
    assert render_cards("   ", engine=search_engine) == ""


def test_render_cards_no_matches_message(tmp_path: Path) -> None:
    """Ensure empty table renders no comics found message."""
    empty_table = open_or_create_table(tmp_path / "empty_lance")
    engine = SearchEngine(table=empty_table)
    assert "no comics found" in render_cards("definitely not a comic", engine=engine)


def test_build_ui_instantiates_successfully(search_engine: SearchEngine) -> None:
    """Ensure Gradio Blocks UI is created with expected title."""
    ui = build_ui(engine=search_engine)
    assert ui.title == "xkcd search"


async def test_mcp_lists_search_tool(mcp_client: Client) -> None:
    """Ensure MCP server advertises search_xkcd tool."""
    tools = await mcp_client.list_tools()
    assert [tool.name for tool in tools] == ["search_xkcd"]


async def test_mcp_calls_search_tool(mcp_client: Client) -> None:
    """Ensure MCP client can invoke search_xkcd tool."""
    result = await mcp_client.call_tool(
        "search_xkcd", {"query": "overton window politics", "k": 2}
    )
    hit = result.data[0]
    assert hit["number"] == OVERTON_COMIC_NUMBER
    assert hit["url"] == f"https://xkcd.com/{OVERTON_COMIC_NUMBER}/"


async def test_root_serves_gradio_ui(composed_app: Starlette | None) -> None:
    """Ensure root path serves Gradio HTML interface."""
    async with _composed_client(composed_app) as client:
        resp = await client.get("/")
        assert resp.status_code == HTTP_OK
        assert "xkcd search" in resp.text


async def test_rest_api_search_endpoint(composed_app: Starlette | None) -> None:
    """Ensure REST API search endpoint returns JSON results."""
    async with _composed_client(composed_app) as client:
        resp = await client.get("/api/search?q=overton+window&k=2")
        assert resp.status_code == HTTP_OK
        data = resp.json()
        assert isinstance(data, list)
        assert data[0]["number"] == OVERTON_COMIC_NUMBER

        # Also test /search alias
        resp_alias = await client.get("/search?q=overton+window&k=1")
        assert resp_alias.status_code == HTTP_OK
        data_alias = resp_alias.json()
        assert len(data_alias) == 1
        assert data_alias[0]["number"] == OVERTON_COMIC_NUMBER

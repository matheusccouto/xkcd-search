"""Pytest fixtures for xkcd-search test suite."""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

import pytest
from fastmcp import Client

from xkcd_search import app as app_mod
from xkcd_search.ingest import (
    fetch_explainxkcd,
    fetch_xkcd,
    new_client,
    open_or_create_table,
    upsert_comic,
)
from xkcd_search.search import SearchEngine
from xkcd_search.server import create_server

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from lancedb.table import Table
    from starlette.applications import Starlette

FIXTURE_NUMBERS = [3230, 353, 327]


@pytest.fixture(scope="session")
def built_index(tmp_path_factory: pytest.TempPathFactory) -> Table | None:
    """Build a tiny 3-comic LanceDB index once per session."""
    if os.getenv("XKCD_TEST_URL"):
        return None

    lance_dir = tmp_path_factory.mktemp("lancedb")
    table = open_or_create_table(lance_dir)
    with new_client() as c:
        for number in FIXTURE_NUMBERS:
            xkcd = fetch_xkcd(number, c)
            article = fetch_explainxkcd(number, c)
            upsert_comic(table, xkcd, article)

    return table


@pytest.fixture
def search_engine(built_index: Table | None) -> SearchEngine:
    """Return a SearchEngine using the test index."""
    if built_index is None:
        return SearchEngine()
    return SearchEngine(table=built_index)


@pytest.fixture
async def mcp_client(search_engine: SearchEngine) -> AsyncIterator[Client]:
    """Provide MCP client connected in-process or to live cloud."""
    url = os.getenv("XKCD_TEST_URL")
    if url:
        auth = "oauth" if "fastmcp.app" in url else None
        async with Client(url, auth=auth) as client:
            yield client
    else:
        mcp, _ = create_server(search_engine)
        async with Client(mcp) as client:
            yield client


@pytest.fixture
def composed_app(search_engine: SearchEngine) -> Starlette | None:
    """Provide composed ASGI app with Gradio, MCP, and REST."""
    if os.getenv("XKCD_TEST_URL"):
        return None

    return app_mod.build_app(search_engine)

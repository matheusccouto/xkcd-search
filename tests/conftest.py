"""Pytest fixtures for the xkcd-search test suite."""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

import pytest

from xkcd_search import app as app_mod
from xkcd_search import server as server_mod
from xkcd_search.ingest import (
    fetch_comic,
    new_client,
    open_or_create_table,
    upsert_comic,
)
from xkcd_search.retriever import XKCDRetriever

if TYPE_CHECKING:
    from fastmcp import FastMCP
    from starlette.applications import Starlette

FIXTURE_NUMBERS = (3230, 353, 327)


@pytest.fixture(scope="session")
def built_index(tmp_path_factory: pytest.TempPathFactory) -> str | None:
    """Local LanceDB index path, or None for remote testing."""
    if os.getenv("XKCD_TEST_URL"):
        return None
    lance_dir = tmp_path_factory.mktemp("lancedb")
    table = open_or_create_table(lance_dir)
    with new_client() as client:
        for number in FIXTURE_NUMBERS:
            upsert_comic(table, fetch_comic(client, number))
    return str(lance_dir)


@pytest.fixture
def retriever(built_index: str | None) -> XKCDRetriever:
    """Return a retriever over the local test index, or the default if remote."""
    return XKCDRetriever(uri=built_index) if built_index else XKCDRetriever()


@pytest.fixture
def mcp_server(built_index: str | None) -> FastMCP | str:
    """FastMCP server over the local index, or live URL for remote testing."""
    if built_index:
        server_mod.retriever.uri = built_index
    return os.getenv("XKCD_TEST_URL") or server_mod.mcp


@pytest.fixture
def composed_app(built_index: str | None) -> Starlette | None:
    """Composed ASGI app over the local index, or None for remote testing."""
    if built_index:
        server_mod.retriever.uri = built_index
    if os.getenv("XKCD_TEST_URL"):
        return None
    return app_mod.app

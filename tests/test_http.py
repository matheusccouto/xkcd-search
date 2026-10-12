"""Tests for the FastMCP HTTP custom routes."""

from __future__ import annotations

from http import HTTPStatus
from typing import TYPE_CHECKING

import httpx
import pytest

from xkcd_search.server import mcp

if TYPE_CHECKING:
    from collections.abc import AsyncIterator


@pytest.fixture
async def http_client() -> AsyncIterator[httpx.AsyncClient]:
    """HTTP client for testing custom routes on the FastMCP server."""
    transport = httpx.ASGITransport(app=mcp.http_app())
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


async def test_search_schema(
    http_client: httpx.AsyncClient, expected_fields: set[str]
) -> None:
    """Verify custom route /api/search returns ranked results with expected schema."""
    resp = await http_client.get("/api/search?q=test&k=2")
    assert resp.status_code == HTTPStatus.OK
    data = resp.json()
    assert len(data) == 2
    assert set(data[0].keys()) == expected_fields


async def test_search_k(http_client: httpx.AsyncClient) -> None:
    """Verify /api/search respects the k query parameter."""
    for i in range(1, 4):
        resp = await http_client.get(f"/api/search?q=test&k={i}")
        assert resp.status_code == HTTPStatus.OK
        assert len(resp.json()) == i


async def test_search_default_k(http_client: httpx.AsyncClient) -> None:
    """Verify /api/search returns results with default k when omitted."""
    resp = await http_client.get("/api/search?q=test")
    assert resp.status_code == HTTPStatus.OK
    assert len(resp.json()) == 3


async def test_search_missing_q(http_client: httpx.AsyncClient) -> None:
    """Verify /api/search returns empty list when q parameter is missing."""
    resp = await http_client.get("/api/search")
    assert resp.json() == []


async def test_search_empty_query(http_client: httpx.AsyncClient) -> None:
    """Verify /api/search returns an empty list for empty or blank queries."""
    resp_empty = await http_client.get("/api/search?q=")
    assert resp_empty.json() == []
    resp_blank = await http_client.get("/api/search?q=   ")
    assert resp_blank.json() == []


async def test_search_invalid_k(http_client: httpx.AsyncClient) -> None:
    """Verify /api/search falls back to default k when k is not a valid integer."""
    resp = await http_client.get("/api/search?q=test&k=invalid")
    assert resp.status_code == HTTPStatus.OK
    assert len(resp.json()) == 3

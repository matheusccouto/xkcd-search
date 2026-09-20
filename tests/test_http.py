"""Tests for the FastMCP HTTP custom routes."""

from __future__ import annotations

from http import HTTPStatus

import pytest
from starlette.testclient import TestClient

from xkcd_search.server import mcp


@pytest.fixture
def http_client() -> TestClient:
    """HTTP client for testing custom routes on the FastMCP server."""
    return TestClient(mcp.http_app())


def test_search_schema(http_client: TestClient, expected_fields: set[str]) -> None:
    """Verify custom route /api/search returns ranked results with expected schema."""
    resp = http_client.get("/api/search?q=test&k=2")
    assert resp.status_code == HTTPStatus.OK
    data = resp.json()
    assert len(data) == 2
    assert set(data[0].keys()) == expected_fields


def test_search_k(http_client: TestClient) -> None:
    """Verify /api/search respects the k query parameter."""
    for i in range(1, 4):
        resp = http_client.get(f"/api/search?q=test&k={i}")
        assert resp.status_code == HTTPStatus.OK
        assert len(resp.json()) == i


def test_search_default_k(http_client: TestClient) -> None:
    """Verify /api/search returns results with default k when omitted."""
    resp = http_client.get("/api/search?q=test")
    assert resp.status_code == HTTPStatus.OK
    assert len(resp.json()) == 3


def test_search_missing_q(http_client: TestClient) -> None:
    """Verify /api/search returns empty list when q parameter is missing."""
    assert http_client.get("/api/search").json() == []


def test_search_empty_query(http_client: TestClient) -> None:
    """Verify /api/search returns an empty list for empty or blank queries."""
    assert http_client.get("/api/search?q=").json() == []
    assert http_client.get("/api/search?q=   ").json() == []


def test_search_invalid_k(http_client: TestClient) -> None:
    """Verify /api/search falls back to default k when k is not a valid integer."""
    resp = http_client.get("/api/search?q=test&k=invalid")
    assert resp.status_code == HTTPStatus.OK
    assert len(resp.json()) == 3

"""Tests for the MCP Server."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from fastmcp.client import Client

from xkcd_search.server import mcp

if TYPE_CHECKING:
    from collections.abc import AsyncIterator


@pytest.fixture
async def mcp_client() -> AsyncIterator[Client]:
    """FastMCP client connected to the test server."""
    async with Client(transport=mcp) as client:
        yield client


async def test_list_tools(mcp_client: Client) -> None:
    """Verify only the search tool is exposed."""
    tools = await mcp_client.list_tools()
    assert [tool.name for tool in tools] == ["search"]


async def test_list_resources(mcp_client: Client) -> None:
    """Verify no resources are exposed."""
    assert await mcp_client.list_resources() == []


async def test_list_resource_templates(mcp_client: Client) -> None:
    """Verify no resource templates are exposed."""
    assert await mcp_client.list_resource_templates() == []


async def test_list_prompts(mcp_client: Client) -> None:
    """Verify no prompts are exposed."""
    assert await mcp_client.list_prompts() == []


async def test_search_tool_schema(
    mcp_client: Client, expected_fields: set[str]
) -> None:
    """Verify search tool executes successfully and matches schema."""
    result = await mcp_client.call_tool("search", {"query": "test", "k": 2})
    assert len(result.data) == 2
    assert set(result.data[0].keys()) == expected_fields


async def test_search_tool_k(mcp_client: Client) -> None:
    """Verify search tool respects the k argument."""
    for i in range(1, 4):
        result = await mcp_client.call_tool("search", {"query": "test", "k": i})
        assert len(result.data) == i


async def test_search_tool_empty_query(mcp_client: Client) -> None:
    """Verify search tool returns empty list for empty or blank queries."""
    result = await mcp_client.call_tool("search", {"query": ""})
    assert result.data == []

    result = await mcp_client.call_tool("search", {"query": "   "})
    assert result.data == []

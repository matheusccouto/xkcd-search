"""Integration tests for the FastMCP server.

Runs in-process against a 3-comic fixture index by default. Set `XKCD_TEST_URL`
to point at a deployed endpoint to run the same suite against a live server,
OAuth-gated.
"""

from __future__ import annotations


async def test_lists_only_the_search_tool(mcp_client):
    tools = await mcp_client.list_tools()
    assert [t.name for t in tools] == ["search_xkcd"]


async def test_search_ranks_relevant_comic_first(mcp_client):
    result = await mcp_client.call_tool("search_xkcd", {"query": "overton window politics", "k": 3})
    hit = result.data[0]
    assert hit["number"] == 3230
    assert hit["url"] == "https://xkcd.com/3230/"
    assert hit["explanation"]
    assert hit["image_url"]


async def test_search_returns_requested_count(mcp_client):
    result = await mcp_client.call_tool("search_xkcd", {"query": "exploits of a mom sql", "k": 1})
    assert len(result.data) == 1
    assert result.data[0]["url"].startswith("https://xkcd.com/")


def test_boot_download_uses_direct_asset_url_not_the_api():
    """Boot must fetch the release asset without the GitHub API.

    The unauthenticated API rate-limits per-IP (60/hr), which the shared egress
    IP of an HF Space exhausts and crashes the server at boot. The direct
    `releases/latest/download/<asset>` URL is not rate-limited.
    """
    from xkcd_search import server as server_mod

    assert server_mod.RELEASE_ASSET_URL.startswith("https://github.com/")
    assert "api.github.com" not in server_mod.RELEASE_ASSET_URL
    assert server_mod.RELEASE_ASSET_URL.endswith("/releases/latest/download/index.sqlite")


def test_boot_survives_index_download_failure(tmp_path, monkeypatch):
    """A failed index download must not crash the server at boot.

    The Space's shared IP can rate-limit or drop the download; the app should
    still boot with an empty index instead of exiting non-zero.
    """
    from xkcd_search import server as server_mod

    index = tmp_path / "index.sqlite"
    monkeypatch.setattr(server_mod, "INDEX_PATH", index)
    monkeypatch.setattr(server_mod, "RELEASE_ASSET_URL", "http://127.0.0.1:9/index.sqlite")

    conn = server_mod._bootstrap()
    try:
        assert conn is not None
        (rows,) = conn.execute("SELECT COUNT(*) FROM comics").fetchone()
        assert rows == 0
    finally:
        conn.close()

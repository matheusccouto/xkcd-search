"""Composition-seam tests for `build_app()`.

The composed app serves the search app at `/` and the MCP endpoint at `/mcp`
in one process. Tests drive it over ASGI HTTP; with `XKCD_TEST_URL` set they
hit the live Space root instead. No mocks.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from contextlib import asynccontextmanager

import httpx

MCP_ACCEPT = {
    "Accept": "application/json, text/event-stream",
    "Content-Type": "application/json",
}


@asynccontextmanager
async def _composed_client(app):
    """An httpx.AsyncClient over the composed app, with its lifespan running."""
    if app is None:
        base_url = os.getenv("XKCD_TEST_URL", "").removesuffix("/mcp")
        async with httpx.AsyncClient(base_url=base_url, timeout=30.0) as c:
            yield c
    else:
        async with (
            app.router.lifespan_context(app),
            httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as c,
        ):
            yield c


def _rpc_body(response: httpx.Response) -> dict:
    """Extract the JSON-RPC body from a streamable-HTTP response.

    The transport may answer with plain `application/json` or an SSE frame
    (`event: message` / `data: {json}`).
    """
    if "application/json" in response.headers.get("content-type", ""):
        return response.json()
    data = "".join(
        line[len("data:") :].strip()
        for line in response.text.splitlines()
        if line.startswith("data:")
    )
    return json.loads(data)


def _mcp_headers(session_id: str | None = None) -> dict[str, str]:
    if session_id is None:
        return dict(MCP_ACCEPT)
    return {**MCP_ACCEPT, "mcp-session-id": session_id}


async def _post_mcp(client: httpx.AsyncClient, payload: dict, session_id: str | None = None):
    response = await client.post("/mcp", json=payload, headers=_mcp_headers(session_id))
    assert response.status_code == 200
    return response


async def test_root_serves_the_search_app(composed_app):
    async with _composed_client(composed_app) as client:
        page = await client.get("/")
        assert page.status_code == 200
        assert "xkcd search" in page.text

        config = await client.get("/config")
        assert config.status_code == 200
        assert "overton window" in config.text


async def test_mcp_endpoint_answers_initialize_and_tools_call(composed_app):
    async with _composed_client(composed_app) as client:
        init = await _post_mcp(
            client,
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2025-06-18",
                    "capabilities": {},
                    "clientInfo": {"name": "composed-test", "version": "0.0.0"},
                },
            },
        )
        session_id = init.headers.get("mcp-session-id")
        assert session_id
        assert _rpc_body(init)["result"]["serverInfo"]["name"] == "xkcd-search"

        initialized = await client.post(
            "/mcp",
            json={"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}},
            headers=_mcp_headers(session_id),
        )
        assert initialized.status_code == 202

        result = await _post_mcp(
            client,
            {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/call",
                "params": {
                    "name": "search_xkcd",
                    "arguments": {"query": "overton window politics", "k": 3},
                },
            },
            session_id=session_id,
        )
        body = _rpc_body(result)
        assert body["id"] == 2
        assert body["result"]["isError"] is False
        comics = json.loads(body["result"]["content"][0]["text"])
        assert comics[0]["number"] == 3230
        assert comics[0]["url"] == "https://xkcd.com/3230/"


def test_importing_server_never_imports_gradio():
    """Server boot must not pay gradio's import cost; only build_app() may."""
    env = {**os.environ, "XKCD_SKIP_BOOTSTRAP": "1"}
    code = (
        "import sys\n"
        "import xkcd_search.server\n"
        "assert 'gradio' not in sys.modules, 'gradio imported at server boot'\n"
    )
    subprocess.run([sys.executable, "-c", code], env=env, check=True, capture_output=True)

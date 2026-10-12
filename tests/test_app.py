"""Tests for the Gradio App."""

from __future__ import annotations

from http import HTTPStatus

import httpx

from xkcd_search.app import app, on_search


def test_on_search() -> None:
    """Verify on_search formats results as (image_url, caption) pairs."""
    results = on_search("test", 2)
    assert len(results) == 2
    image_url, caption = results[0]
    assert image_url.startswith("https://")
    assert "#" in caption


async def test_root_serves_gradio_ui() -> None:
    """Ensure root path serves the Gradio interface."""
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/")
    assert resp.status_code == HTTPStatus.OK
    assert "xkcd search" in resp.text

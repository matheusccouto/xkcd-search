"""Gradio web UI, FastMCP server, and ASGI entry point."""

from __future__ import annotations

import html
import os
from typing import TYPE_CHECKING, Any

import gradio as gr
import uvicorn
from fastmcp import FastMCP
from starlette.responses import JSONResponse

from xkcd_search.search import SearchEngine

if TYPE_CHECKING:
    from starlette.applications import Starlette
    from starlette.requests import Request

CARD_STYLE = (
    "<style>"
    ".xkcd-cards{display:flex;flex-direction:column;gap:1.25rem;}"
    ".xkcd-card{border:1px solid #ddd;border-radius:8px;"
    "padding:.5rem;text-align:center;}"
    ".xkcd-card img{display:block;max-width:100%;margin:0 auto;border-radius:6px;}"
    "</style>"
)


def _render_cards(query: str, k: int, engine: SearchEngine) -> str:
    if not query.strip():
        return ""
    comics = engine.search(query, k=k)
    if not comics:
        return '<p class="xkcd-empty">no comics found</p>'
    cards = [
        f'<div class="xkcd-card"><a href="{html.escape(c["url"], quote=True)}">'
        f'<img src="{html.escape(c["image_url"], quote=True)}" '
        f'alt="{html.escape(c["alt_text"])}" loading="lazy"></a></div>'
        for c in comics
    ]
    return f'<div class="xkcd-cards">{CARD_STYLE}\n{"".join(cards)}\n</div>'


def _build_ui(engine: SearchEngine) -> gr.Blocks:
    with gr.Blocks(title="xkcd search") as ui:
        gr.Markdown("# xkcd search")
        with gr.Row():
            query = gr.Textbox(
                label="Query",
                placeholder="e.g. a comic about the overton window",
                lines=2,
                scale=4,
            )
            k_input = gr.Number(
                label="Number of comics",
                value=5,
                minimum=1,
                maximum=20,
                precision=0,
                scale=1,
            )
        submit = gr.Button("Search", variant="primary")
        output = gr.HTML(label="Results")

        def on_search(q: str, count: float) -> str:
            return _render_cards(q, int(count), engine)

        submit.click(on_search, inputs=[query, k_input], outputs=output)
        query.submit(on_search, inputs=[query, k_input], outputs=output)
    return ui


def create_app(engine: SearchEngine | None = None) -> tuple[FastMCP, Starlette]:
    """Create FastMCP server and mounted Gradio web application."""
    search_engine = engine or SearchEngine()

    mcp = FastMCP("xkcd-search")

    @mcp.tool(name="search_xkcd")
    def search_tool(query: str, k: int = 5) -> list[dict[str, Any]]:
        """Semantic search over xkcd comics, ranked by relevance."""
        return search_engine.search(query, k=k)

    @mcp.custom_route("/api/search", methods=["GET"])
    async def search_api(request: Request) -> JSONResponse:
        q = request.query_params.get("q", "")
        k_val = int(request.query_params.get("k", "5"))
        return JSONResponse(search_engine.search(q, k=k_val))

    server_app = mcp.http_app(path="/mcp")
    ui = _build_ui(search_engine)
    app = gr.mount_gradio_app(server_app, ui, path="/")
    return mcp, app


mcp, app = create_app()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", "7860"))
    host = os.environ.get("HOST", "0.0.0.0")  # noqa: S104
    uvicorn.run(app, host=host, port=port)

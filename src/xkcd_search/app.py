"""Gradio web UI and ASGI application entry point."""

from __future__ import annotations

import html
import os
from typing import TYPE_CHECKING

import gradio as gr
import uvicorn

from xkcd_search.search import SearchEngine
from xkcd_search.server import create_server

if TYPE_CHECKING:
    from starlette.applications import Starlette

CARD_STYLE = (
    "<style>"
    ".xkcd-cards{display:flex;flex-direction:column;gap:1.25rem;}"
    ".xkcd-card{border:1px solid #ddd;border-radius:8px;"
    "padding:.5rem;text-align:center;}"
    ".xkcd-card img{display:block;max-width:100%;margin:0 auto;border-radius:6px;}"
    "</style>"
)


def render_cards(query: str, k: int = 5, engine: SearchEngine | None = None) -> str:
    """Render HTML comic cards for the search UI."""
    if not query.strip():
        return ""
    search_engine = engine or SearchEngine()
    comics = search_engine.search(query, k=int(k))
    if not comics:
        return '<p class="xkcd-empty">no comics found</p>'

    cards = []
    for c in comics:
        comic_url = html.escape(c["url"], quote=True)
        image_url = html.escape(c["image_url"], quote=True)
        alt = html.escape(c["alt_text"])
        cards.append(
            f'<div class="xkcd-card"><a href="{comic_url}">'
            f'<img src="{image_url}" alt="{alt}" loading="lazy"></a></div>'
        )
    return f'<div class="xkcd-cards">{CARD_STYLE}\n{"".join(cards)}\n</div>'


def build_ui(engine: SearchEngine | None = None) -> gr.Blocks:
    """Build the Gradio search interface."""
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
            return render_cards(q, k=int(count), engine=engine)

        submit.click(on_search, inputs=[query, k_input], outputs=output)
        query.submit(on_search, inputs=[query, k_input], outputs=output)
    return ui


def build_app(engine: SearchEngine | None = None) -> Starlette:
    """Mount Gradio UI onto FastMCP HTTP server."""
    search_engine = engine or SearchEngine()
    _, server_app = create_server(search_engine)
    ui = build_ui(search_engine)
    return gr.mount_gradio_app(server_app, ui, path="/")


app = build_app()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", "7860"))
    host = os.environ.get("HOST", "0.0.0.0")  # noqa: S104
    uvicorn.run(app, host=host, port=port)

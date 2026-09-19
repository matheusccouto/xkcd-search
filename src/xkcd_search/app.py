"""Gradio web UI and ASGI entry point."""

from __future__ import annotations

import os

import gradio as gr
import uvicorn

from xkcd_search.server import mcp, retriever


def on_search(q: str, count: float) -> list[tuple[str, str]]:
    """Return (image, caption) pairs for the query."""
    docs = retriever.invoke(q, k=int(count))
    return [
        (
            d.metadata["image_url"],
            f"#{d.metadata['number']} {d.metadata['title']} ({d.metadata['url']})",
        )
        for d in docs
    ]


with gr.Blocks(title="xkcd search") as ui:
    gr.Markdown("# xkcd search")
    with gr.Row():
        query = gr.Textbox(
            label="Query",
            placeholder="e.g. a comic about the overton window",
            lines=2,
            scale=4,
        )
        count = gr.Number(
            label="Number of comics",
            value=5,
            minimum=1,
            maximum=20,
            precision=0,
            scale=1,
        )
    submit = gr.Button("Search", variant="primary")
    results = gr.Gallery(label="Results", columns=3)

    submit.click(on_search, inputs=[query, count], outputs=results)
    query.submit(on_search, inputs=[query, count], outputs=results)

server_app = mcp.http_app(path="/mcp")
app = gr.mount_gradio_app(server_app, ui, path="/")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", "7860"))
    host = os.environ.get("HOST", "0.0.0.0")  # noqa: S104
    uvicorn.run(app, host=host, port=port)

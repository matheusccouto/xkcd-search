"""Human-facing search app: a Gradio UI over a `search_cards` domain seam.

`ComicCard` and `search_cards` are the domain seam; `render_cards` and the
Gradio UI are a thin handler over it. `gradio` is imported lazily inside
`build_ui()` so importing this module never pays gradio's import cost.
"""

from __future__ import annotations

import html
import os
from dataclasses import dataclass

from xkcd_search import server

MAX_CARDS = 5


@dataclass(frozen=True)
class ComicCard:
    number: int
    title: str
    url: str
    image_url: str
    alt_text: str


def search_cards(query: str, k: int = MAX_CARDS) -> list[ComicCard]:
    """Return up to `k` ComicCards for `query`, ranked by relevance."""
    return [
        ComicCard(
            number=result["number"],
            title=result["title"],
            url=result["url"],
            image_url=result["image_url"],
            alt_text=result["alt_text"],
        )
        for result in server.search_xkcd(query, k)
    ]


_CARD_STYLE = (
    "<style>"
    ".xkcd-cards{display:flex;flex-direction:column;gap:1.5rem;}"
    ".xkcd-card{border:1px solid #ddd;border-radius:8px;padding:1rem;}"
    ".xkcd-card img{max-width:100%;border-radius:6px;}"
    ".xkcd-alt{color:#555;}"
    "</style>"
)


def render_cards(query: str) -> str:
    """Render the HTML for `query`: comic cards, or a no-comics-found message.

    An empty query is a no-op and renders nothing.
    """
    if not query.strip():
        return ""
    cards = search_cards(query, k=MAX_CARDS)
    if not cards:
        return '<p class="xkcd-empty">no comics found</p>'
    card_html = "\n".join(_card_html(card) for card in cards)
    return f'<div class="xkcd-cards">{_CARD_STYLE}\n{card_html}\n</div>'


def _card_html(card: ComicCard) -> str:
    url = html.escape(card.url, quote=True)
    image_url = html.escape(card.image_url, quote=True)
    title = html.escape(card.title)
    alt_text = html.escape(card.alt_text)
    return (
        '<div class="xkcd-card">'
        f'<a href="{url}"><img src="{image_url}" alt="{alt_text}" loading="lazy"></a>'
        f'<h3><a href="{url}">{title}</a> (#{card.number})</h3>'
        f'<p class="xkcd-alt">{alt_text}</p>'
        "</div>"
    )


def build_ui():
    """Build the Gradio UI: a text input whose submit renders comic cards."""
    import gradio as gr

    with gr.Blocks(title="xkcd-search") as ui:
        gr.Markdown(f"# xkcd-search\nDescribe a comic and see up to {MAX_CARDS} matches.")
        query = gr.Textbox(
            label="Query",
            placeholder="e.g. a comic about the overton window",
            lines=2,
        )
        output = gr.HTML(label="Results")
        submit = gr.Button("Search", variant="primary")
        submit.click(render_cards, inputs=query, outputs=output)
        query.submit(render_cards, inputs=query, outputs=output)
    return ui


def main() -> None:
    """Launch the search app for local development."""
    ui = build_ui()
    ui.launch(server_name="0.0.0.0", server_port=int(os.getenv("PORT", "7860")))


if __name__ == "__main__":
    main()

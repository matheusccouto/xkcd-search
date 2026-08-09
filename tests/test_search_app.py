"""Domain-seam tests for the search app.

`search_cards` and `render_cards` are tested against the in-process
`built_index` fixture. No mocks.
"""

from __future__ import annotations

from xkcd_search import server
from xkcd_search.builder import open_connection
from xkcd_search.search_app import MAX_CARDS, ComicCard, build_ui, render_cards, search_cards


def test_search_cards_returns_ranked_comic_cards(built_index):
    cards = search_cards("overton window politics", k=3)
    assert len(cards) == 3
    assert all(isinstance(card, ComicCard) for card in cards)
    assert cards[0].number == 3230
    assert cards[0].url == "https://xkcd.com/3230/"
    assert cards[0].title == "Overton"
    assert cards[0].image_url
    assert "Overton window" in cards[0].alt_text


def test_search_cards_respects_existing_k_cap(built_index):
    cards = search_cards("comic", k=99)
    assert len(cards) <= 20
    assert all(isinstance(card, ComicCard) for card in cards)


def _open_empty_index(tmp_path):
    """Open a real, empty (schema-only) index read-only."""
    index_path = tmp_path / "index.sqlite"
    conn = open_connection(index_path)
    conn.close()
    return open_connection(index_path, read_only=True)


def test_search_cards_empty_index_returns_no_matches(tmp_path, monkeypatch):
    read_conn = _open_empty_index(tmp_path)
    monkeypatch.setattr(server, "_conn", read_conn)
    try:
        cards = search_cards("definitely not a real comic")
        assert cards == []
    finally:
        read_conn.close()


def test_render_cards_empty_query_is_noop(built_index):
    assert render_cards("") == ""
    assert render_cards("   ") == ""


def test_render_cards_no_matches_message(tmp_path, monkeypatch):
    read_conn = _open_empty_index(tmp_path)
    monkeypatch.setattr(server, "_conn", read_conn)
    try:
        html = render_cards("definitely not a real comic")
        assert "no comics found" in html
    finally:
        read_conn.close()


def test_render_cards_renders_every_card_field(built_index):
    html = render_cards("overton window politics")
    assert 'href="https://xkcd.com/3230/"' in html
    assert "<img" in html
    assert ">Overton</a>" in html
    assert "#3230" in html
    assert 'class="xkcd-alt"' in html
    assert "Overton window" in html


def _layout_order(ui) -> list[int]:
    """Component ids in document order from the Blocks layout tree."""
    order: list[int] = []

    def walk(node: dict) -> None:
        order.append(node["id"])
        for child in node.get("children", []):
            walk(child)

    walk(ui.config["layout"])
    return order


def _component_id(ui, ctype: str, *, label: str | None = None, value: str | None = None) -> int:
    for c in ui.config["components"]:
        if c.get("type") != ctype:
            continue
        props = c.get("props", {})
        if label is not None and props.get("label") != label:
            continue
        if value is not None and props.get("value") != value:
            continue
        return c["id"]
    raise AssertionError(f"no {ctype} component with label={label!r} value={value!r} found")


def test_render_cards_respects_k(built_index):
    assert render_cards("overton window politics", k=1).count('class="xkcd-card"') == 1
    assert render_cards("overton window politics", k=2).count('class="xkcd-card"') == 2


def test_search_button_sits_before_results():
    """The Search button must sit with the query box, above the Results output.

    If the button renders after the results, tall cards push it to the bottom of
    the page and every new search starts with a scroll back up.
    """
    ui = build_ui()
    order = _layout_order(ui)
    button_id = _component_id(ui, "button", value="Search")
    output_id = _component_id(ui, "html", label="Results")
    assert order.index(button_id) < order.index(output_id)


def test_k_input_defaults_to_max_cards():
    """The K number input must exist, default to MAX_CARDS, and cap at 20."""
    ui = build_ui()
    k_id = _component_id(ui, "number", label="Number of comics (K)")
    props = next(c for c in ui.config["components"] if c["id"] == k_id)["props"]
    assert props["value"] == MAX_CARDS
    assert props["minimum"] == 1
    assert props["maximum"] == 20
    assert props["precision"] == 0

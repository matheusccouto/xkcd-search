"""Domain-seam tests for the search app.

`search_cards` and `render_cards` are tested against the in-process
`built_index` fixture. No mocks.
"""

from __future__ import annotations

from xkcd_search import server
from xkcd_search.builder import open_connection
from xkcd_search.search_app import ComicCard, render_cards, search_cards


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

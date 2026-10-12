"""Tests for Comic and Chunk domain models and chunking strategies."""

from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from xkcd_search.chunker import FixedWindowChunker
from xkcd_search.models import Chunk, Comic


def test_comic_immutability() -> None:
    """Verify Comic instances are frozen and immutable."""
    comic = Comic(
        number=1,
        title="Test Comic",
        url="https://xkcd.com/1/",
        image_url="https://example.com/1.png",
        alt_text="Alt",
        transcript="Transcript",
        explanation="Explanation",
    )
    with pytest.raises(FrozenInstanceError):
        comic.__setattr__("title", "Modified")


def test_comic_from_dict() -> None:
    """Verify Comic.from_dict reconstructs an entity with optional score."""
    data = {
        "number": 1,
        "title": "Test Comic",
        "url": "https://xkcd.com/1/",
        "image_url": "https://example.com/1.png",
        "alt_text": "Alt",
        "transcript": "Transcript",
        "explanation": "Explanation",
    }
    comic = Comic.from_dict(data, score=0.92)
    assert comic.number == 1
    assert comic.title == "Test Comic"
    assert comic.score == 0.92


def test_comic_to_dict_omits_score(expected_fields: set[str]) -> None:
    """Verify to_dict returns exactly the core fields and omits score."""
    comic = Comic(
        number=1,
        title="Test Comic",
        url="https://xkcd.com/1/",
        image_url="https://example.com/1.png",
        alt_text="Alt",
        transcript="Transcript",
        explanation="Explanation",
        score=0.95,
    )
    data = comic.to_dict()
    assert set(data.keys()) == expected_fields
    assert "score" not in data


def test_chunk_attributes() -> None:
    """Verify Chunk stores comic number, text, and kind."""
    chunk = Chunk(comic_number=10, text="sample snippet", kind="window")
    assert chunk.comic_number == 10
    assert chunk.text == "sample snippet"
    assert chunk.kind == "window"


def test_fixed_window_chunker_linkage() -> None:
    """Verify FixedWindowChunker tags chunks with comic number and kind."""
    comic = Comic(
        number=42,
        title="Title",
        url="https://xkcd.com/42/",
        image_url="https://example.com/42.png",
        alt_text="Alt text",
        transcript="Some dialogue",
        explanation="Detailed explanation " * 20,
    )
    chunker = FixedWindowChunker(chunk_size=100, overlap=20)
    chunks = chunker.chunk(comic)

    assert len(chunks) > 1
    assert all(c.comic_number == 42 for c in chunks)
    assert all(c.kind == "window" for c in chunks)
    assert all(len(c.text) <= 100 for c in chunks)

"""Tests for the xkcd ingestion and parsing pipeline."""

from __future__ import annotations

from typing import TYPE_CHECKING

import mwparserfromhell

from xkcd_search.ingest import (
    MAX_TEXT_CHARS,
    SCHEMA,
    comic_text,
    open_or_create_table,
    parse_comic,
    transcript_of,
    upsert_comic,
)

if TYPE_CHECKING:
    from pathlib import Path

    import pytest

SAMPLE_WIKITEXT = """{{comic
| number = 1
| title = Barrel - Part 1
| image = barrel_cropped_(1).jpg
| titletext = Don't we all.
}}
== Explanation ==
A boy is sitting in a barrel.

== Transcript ==
[[A boy sits in a barrel floating in water.]]
"""

SAMPLE_WIKITEXT_CASE_INSENSITIVE_TRANSCRIPT = """{{comic
| number = 2
| title = Petit Trees
| image = tree.png
| titletext = Some alt text
}}
== explanation ==
A comic about trees.

== transcript ==
[[A tiny tree is planted.]]
"""

SAMPLE_WIKITEXT_NO_TRANSCRIPT = """{{comic
| number = 3
| title = Island
| image = island.png
| titletext = Solitude
}}
== Explanation ==
Just an island in the ocean.
"""


def test_schema_contract(expected_fields: set[str]) -> None:
    """Verify that all expected metadata fields match the LanceDB schema."""
    schema_fields = set(SCHEMA.names)
    assert expected_fields.issubset(schema_fields)
    assert "vector" in schema_fields


def test_parse_comic() -> None:
    """Verify parse_comic extracts metadata correctly from wikitext."""
    comic = parse_comic(1, SAMPLE_WIKITEXT)
    assert comic["number"] == 1
    assert comic["title"] == "Barrel - Part 1"
    assert comic["url"] == "https://xkcd.com/1/"
    assert comic["image"] == "barrel_cropped_(1).jpg"
    assert comic["alt_text"] == "Don't we all."
    assert comic["transcript"] == "A boy sits in a barrel floating in water."
    assert "A boy is sitting in a barrel." in comic["explanation"]


def test_transcript_of_standard_heading() -> None:
    """Verify transcript_of extracts transcript with standard heading."""
    parsed = mwparserfromhell.parse(SAMPLE_WIKITEXT)
    assert transcript_of(parsed) == "A boy sits in a barrel floating in water."


def test_transcript_of_case_insensitive_heading() -> None:
    """Verify transcript_of matches transcript heading case-insensitively."""
    parsed = mwparserfromhell.parse(SAMPLE_WIKITEXT_CASE_INSENSITIVE_TRANSCRIPT)
    assert transcript_of(parsed) == "A tiny tree is planted."


def test_transcript_of_missing_heading() -> None:
    """Verify transcript_of returns an empty string when transcript is absent."""
    parsed = mwparserfromhell.parse(SAMPLE_WIKITEXT_NO_TRANSCRIPT)
    assert transcript_of(parsed) == ""


def test_comic_text_combines_fields() -> None:
    """Verify comic_text joins title, alt text, and explanation cleanly."""
    comic = {
        "title": "Universal Standards",
        "alt_text": "Fortunately, the charge one has been solved.",
        "explanation": "There are now 15 competing standards.",
    }
    expected = (
        "Universal Standards\n"
        "Fortunately, the charge one has been solved.\n"
        "There are now 15 competing standards."
    )
    assert comic_text(comic) == expected


def test_comic_text_omits_empty_or_whitespace_fields() -> None:
    """Verify comic_text skips empty or whitespace-only sections."""
    comic = {
        "title": "Title Only",
        "alt_text": "   ",
        "explanation": "",
    }
    assert comic_text(comic) == "Title Only"


def test_comic_text_truncates_at_max_chars() -> None:
    """Verify comic_text truncates combined text to MAX_TEXT_CHARS."""
    comic = {
        "title": "Title",
        "alt_text": "Alt",
        "explanation": "E" * (MAX_TEXT_CHARS + 500),
    }
    result = comic_text(comic)
    assert len(result) == MAX_TEXT_CHARS
    assert result.startswith("Title\nAlt\nEEEE")


def test_open_or_create_table(tmp_path: Path) -> None:
    """Verify open_or_create_table creates a new table or opens an existing one."""
    db_path = tmp_path / "lancedb"
    table = open_or_create_table(db_path)
    assert table.name == "comics"
    assert set(table.schema.names) == set(SCHEMA.names)

    reopened_table = open_or_create_table(db_path)
    assert reopened_table.name == "comics"
    assert len(reopened_table) == 0


def test_upsert_comic(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify upsert_comic inserts new comics and updates existing ones."""
    monkeypatch.setattr(
        "xkcd_search.ingest.encode",
        lambda text: [0.5] * 384,  # noqa: ARG005
    )

    table = open_or_create_table(tmp_path / "lancedb")
    comic_initial = {
        "number": 1,
        "title": "Original Title",
        "url": "https://xkcd.com/1/",
        "image_url": "https://example.com/1.png",
        "alt_text": "Original alt",
        "transcript": "Original transcript",
        "explanation": "Original explanation",
    }
    upsert_comic(table, comic_initial)
    assert len(table) == 1
    row = table.to_arrow().to_pylist()[0]
    assert row["title"] == "Original Title"

    comic_updated = {
        "number": 1,
        "title": "Updated Title",
        "url": "https://xkcd.com/1/",
        "image_url": "https://example.com/1.png",
        "alt_text": "Updated alt",
        "transcript": "Updated transcript",
        "explanation": "Updated explanation",
    }
    upsert_comic(table, comic_updated)
    assert len(table) == 1
    row = table.to_arrow().to_pylist()[0]
    assert row["title"] == "Updated Title"

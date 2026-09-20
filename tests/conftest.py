"""Pytest fixtures for the xkcd-search test suite."""

from __future__ import annotations

import lancedb
import pytest

TABLE_NAME = "comics"
TABLE_DATA = [
    {
        "number": 1,
        "title": "Comic One",
        "url": "https://example.com/1/",
        "image_url": "https://example.com/1.png",
        "alt_text": "Alt text one",
        "transcript": "Transcript one",
        "explanation": "Explanation one",
        "vector": [0.1] * 384,
    },
    {
        "number": 2,
        "title": "Comic Two",
        "url": "https://example.com/2/",
        "image_url": "https://example.com/2.png",
        "alt_text": "Alt text two",
        "transcript": "Transcript two",
        "explanation": "Explanation two",
        "vector": [0.2] * 384,
    },
    {
        "number": 3,
        "title": "Comic Three",
        "url": "https://example.com/3/",
        "image_url": "https://example.com/3.png",
        "alt_text": "Alt text three",
        "transcript": "Transcript three",
        "explanation": "Explanation three",
        "vector": [0.3] * 384,
    },
]


@pytest.fixture(scope="session")
def uri(tmp_path_factory: pytest.TempPathFactory) -> str:
    """Local LanceDB URI seeded with sample comics."""
    path = str(tmp_path_factory.mktemp("lancedb"))
    lancedb.connect(path).create_table("comics", data=TABLE_DATA)
    return path


@pytest.fixture(autouse=True)
def _test_env(uri: str, monkeypatch: pytest.MonkeyPatch) -> None:
    """Set XKCD_DATASET_URI for each test, restored automatically."""
    monkeypatch.setenv("XKCD_DATASET_URI", uri)


@pytest.fixture
def expected_fields() -> set[str]:
    """Return expected metadata fields in search results."""
    return {
        "number",
        "title",
        "url",
        "image_url",
        "alt_text",
        "transcript",
        "explanation",
    }

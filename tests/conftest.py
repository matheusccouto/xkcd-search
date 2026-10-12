"""Pytest fixtures for the xkcd-search test suite."""

from __future__ import annotations

import lancedb
import pytest

from xkcd_search import server


class DeterministicTestEmbedder:
    """Generates deterministic float vectors for offline testing."""

    def __init__(self, dim: int = 384) -> None:
        """Initialize deterministic test embedder with vector dimensionality."""
        self.dim = dim

    def embed(self, text: str) -> list[float]:
        """Embed a single text string deterministically."""
        return self.embed_batch([text])[0]

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Embed a batch of text strings deterministically."""
        results: list[list[float]] = []
        for text in texts:
            seed = sum(ord(c) for c in text)
            vec = [float(((seed + i) % 100) / 100.0) for i in range(self.dim)]
            results.append(vec)
        return results


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
    },
    {
        "number": 2,
        "title": "Comic Two",
        "url": "https://example.com/2/",
        "image_url": "https://example.com/2.png",
        "alt_text": "Alt text two",
        "transcript": "Transcript two",
        "explanation": "Explanation two",
    },
    {
        "number": 3,
        "title": "Comic Three",
        "url": "https://example.com/3/",
        "image_url": "https://example.com/3.png",
        "alt_text": "Alt text three",
        "transcript": "Transcript three",
        "explanation": "Explanation three",
    },
]

CHUNKS_DATA = [
    {
        "comic_number": 1,
        "text": "Comic One chunk",
        "kind": "window",
        "vector": [0.1] * 384,
    },
    {
        "comic_number": 2,
        "text": "Comic Two chunk",
        "kind": "window",
        "vector": [0.2] * 384,
    },
    {
        "comic_number": 3,
        "text": "Comic Three chunk",
        "kind": "window",
        "vector": [0.3] * 384,
    },
]


@pytest.fixture(scope="session")
def uri(tmp_path_factory: pytest.TempPathFactory) -> str:
    """Local LanceDB URI seeded with sample comics and chunks."""
    path = str(tmp_path_factory.mktemp("lancedb"))
    db = lancedb.connect(path)
    db.create_table("comics", data=TABLE_DATA)
    db.create_table("chunks", data=CHUNKS_DATA)
    return path


@pytest.fixture(autouse=True)
def _test_env(uri: str, monkeypatch: pytest.MonkeyPatch) -> None:
    """Configure test environment for offline hermetic execution."""
    monkeypatch.setenv("XKCD_DATASET_URI", uri)
    server.search_index.embedder = DeterministicTestEmbedder()


@pytest.fixture
def deterministic_embedder() -> DeterministicTestEmbedder:
    """Return a deterministic test embedder."""
    return DeterministicTestEmbedder()


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

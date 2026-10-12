"""Unit and integration tests for SearchIndex."""

from __future__ import annotations

from typing import TYPE_CHECKING

from xkcd_search.index import SearchIndex
from xkcd_search.models import Comic

if TYPE_CHECKING:
    from pathlib import Path

    from tests.conftest import DeterministicTestEmbedder


def sample_comics() -> list[Comic]:
    """Return sample comic entities for testing."""
    return [
        Comic(
            number=1,
            title="Python Standards",
            url="https://xkcd.com/1/",
            image_url="https://example.com/1.png",
            alt_text="Now 15 standards",
            transcript="Standards discussion",
            explanation="Detailed explanation of universal standards.",
        ),
        Comic(
            number=2,
            title="Git Commit",
            url="https://xkcd.com/2/",
            image_url="https://example.com/2.png",
            alt_text="Git message",
            transcript="Help me git",
            explanation="Comic about git branching and merge conflicts.",
        ),
    ]


def test_index_and_search_k(
    tmp_path: Path, deterministic_embedder: DeterministicTestEmbedder
) -> None:
    """Verify SearchIndex indexes comics and returns ranked results respecting k."""
    index = SearchIndex(uri=tmp_path / "lancedb", embedder=deterministic_embedder)
    index.index(sample_comics())

    results = index.search("standards", k=1)
    assert len(results) == 1
    assert isinstance(results[0], Comic)
    assert results[0].score is not None

    all_results = index.search("standards", k=5)
    assert len(all_results) == 2


def test_search_rank_ordering(
    tmp_path: Path, deterministic_embedder: DeterministicTestEmbedder
) -> None:
    """Verify results are returned in descending order of relevance score."""
    index = SearchIndex(uri=tmp_path / "lancedb", embedder=deterministic_embedder)
    index.index(sample_comics())

    results = index.search("standards", k=5)
    scores = [c.score for c in results if c.score is not None]
    assert len(scores) == 2
    assert scores[0] >= scores[1]


def test_search_chunk_deduplication(
    tmp_path: Path, deterministic_embedder: DeterministicTestEmbedder
) -> None:
    """Verify multiple matching chunks produce a single deduplicated result."""
    long_explanation = "Extremely long explanation repeating key terms. " * 30
    comic = Comic(
        number=10,
        title="Long Comic",
        url="https://xkcd.com/10/",
        image_url="https://example.com/10.png",
        alt_text="Long Alt",
        transcript="Dialogue",
        explanation=long_explanation,
    )
    index = SearchIndex(uri=tmp_path / "lancedb", embedder=deterministic_embedder)
    index.index([comic])

    results = index.search("Extremely long explanation", k=5)
    assert len(results) == 1
    assert results[0].number == 10


def test_search_empty_query(
    tmp_path: Path, deterministic_embedder: DeterministicTestEmbedder
) -> None:
    """Verify empty or whitespace-only queries return empty list."""
    index = SearchIndex(uri=tmp_path / "lancedb", embedder=deterministic_embedder)
    assert index.search("") == []
    assert index.search("   ") == []


def test_search_empty_database(
    tmp_path: Path, deterministic_embedder: DeterministicTestEmbedder
) -> None:
    """Verify searching an uninitialized database returns empty list without error."""
    index = SearchIndex(uri=tmp_path / "empty_db", embedder=deterministic_embedder)
    assert index.search("query") == []

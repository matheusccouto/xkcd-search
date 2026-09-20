"""Tests for the LangChain Retriever."""

import pytest

from xkcd_search.retriever import XKCDRetriever


@pytest.fixture
def retriever() -> XKCDRetriever:
    """Return a retriever."""
    return XKCDRetriever()


async def test_k(retriever: XKCDRetriever) -> None:
    """Assert retriever accepts a `k` keyword argument."""
    for i in range(1, 4):
        assert len(retriever.invoke("test", k=i)) == i


async def test_document_schema(
    retriever: XKCDRetriever, expected_fields: set[str]
) -> None:
    """Assert retrieved documents match expected schema and attribution."""
    docs = retriever.invoke("test", k=1)
    assert len(docs) == 1
    doc = docs[0]
    assert doc.id == "1"
    assert doc.page_content.startswith("https://")
    assert set(doc.metadata.keys()) == expected_fields


async def test_empty_query(retriever: XKCDRetriever) -> None:
    """Assert empty or whitespace queries return an empty list."""
    assert retriever.invoke("") == []
    assert retriever.invoke(" ") == []


async def test_invalid_uri(monkeypatch: pytest.MonkeyPatch) -> None:
    """Assert a bad URI raises loudly."""
    monkeypatch.setenv("XKCD_DATASET_URI", "/nonexistent/invalid/path")
    retriever = XKCDRetriever()
    with pytest.raises((ValueError, OSError)):
        retriever.table  # noqa: B018

"""Retrieval benchmark test suite."""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pytest

from xkcd_search.index import SearchIndex
from xkcd_search.rerank import CrossEncoderReranker

if TYPE_CHECKING:
    from collections.abc import Callable

DATASET_PATH = Path(__file__).parent / "dataset.json"
search_index = SearchIndex(reranker=CrossEncoderReranker())


def load_cases() -> list[dict[str, Any]]:
    """Load evaluation test cases from dataset.json."""
    return json.loads(DATASET_PATH.read_text(encoding="utf-8"))


def search(query: str) -> list[int]:
    """Retrieve top-5 comic numbers for a query using SearchIndex."""
    return [c.number for c in search_index.search(query, k=5)]


@pytest.mark.parametrize("case", load_cases())
def test_case_retrieval(
    case: dict[str, Any],
    record_property: Callable[[str, object], None],
) -> None:
    """Verify semantic search retrieves expected comic in top-5."""
    retrieved = search(case["query"])
    expected = case["number"]
    rank = retrieved.index(expected) + 1 if expected in retrieved else 0

    # Built-in fixture attaching rank to test report for summary in conftest.py
    record_property("rank", rank)

    assert rank > 0

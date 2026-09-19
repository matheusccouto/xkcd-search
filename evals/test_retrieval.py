"""Retrieval benchmarks."""

import json
from pathlib import Path
from typing import Any

import pytest

from xkcd_search.retriever import XKCDRetriever

DATASET_PATH = Path(__file__).parent / "dataset.json"
LANCE_DIR = Path(__file__).parent.parent / ".lance"


def load_cases() -> list[dict[str, Any]]:
    """Load evaluation test cases from dataset.json."""
    return json.loads(DATASET_PATH.read_text(encoding="utf-8"))


@pytest.mark.parametrize("case", load_cases())
def test_hit_rate_at_5(case: dict[str, Any]) -> None:
    """Verify semantic search retrieves expected comic in top-5."""
    retriever = XKCDRetriever(uri=str(LANCE_DIR), k=5)
    retrieved = [d.metadata["number"] for d in retriever.invoke(case["query"])]
    assert case["number"] in retrieved


if __name__ == "__main__":
    cases = load_cases()
    retriever = XKCDRetriever(uri=str(LANCE_DIR), k=5)
    hits = sum(
        case["number"]
        in [d.metadata["number"] for d in retriever.invoke(case["query"])]
        for case in cases
    )
    total = len(cases)
    print(f"Hit Rate @ 5: {hits}/{total} ({(hits / total) * 100:.1f}%)")

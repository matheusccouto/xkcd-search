"""Retrieval benchmarks and quality metrics."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any

import httpx
import pytest

from xkcd_search.retriever import XKCDRetriever

DATASET_PATH = Path(__file__).parent / "dataset.json"
LANCE_DIR = Path(__file__).parent.parent / ".lance"
os.environ.setdefault("XKCD_DATASET_URI", str(LANCE_DIR))


def load_cases() -> list[dict[str, Any]]:
    """Load evaluation test cases from dataset.json."""
    return json.loads(DATASET_PATH.read_text(encoding="utf-8"))


def search_local(query: str, k: int) -> list[int]:
    """Retrieve top-k comic numbers locally via XKCDRetriever."""
    retriever = XKCDRetriever(k=k)
    return [d.metadata["number"] for d in retriever.invoke(query)]


def search_remote(url: str, query: str, k: int) -> list[int]:
    """Retrieve top-k comic numbers from remote HTTP /api/search endpoint."""
    endpoint = f"{url.rstrip('/')}/api/search"
    resp = httpx.get(endpoint, params={"q": query, "k": k}, timeout=30.0)
    resp.raise_for_status()
    return [item["number"] for item in resp.json()]


def evaluate_benchmarks(cases: list[dict[str, Any]], url: str | None = None) -> None:
    """Evaluate and print Hit@1, Hit@3, Hit@5, and MRR metrics."""
    k_max = 5
    hit_1 = 0
    hit_3 = 0
    hit_5 = 0
    reciprocal_ranks: list[float] = []

    for case in cases:
        query = case["query"]
        expected = case["number"]

        if url:
            retrieved = search_remote(url, query, k=k_max)
        else:
            retrieved = search_local(query, k=k_max)

        if expected in retrieved:
            rank = retrieved.index(expected) + 1
            reciprocal_ranks.append(1.0 / rank)
            if rank == 1:
                hit_1 += 1
            if rank <= 3:
                hit_3 += 1
            if rank <= 5:
                hit_5 += 1
        else:
            reciprocal_ranks.append(0.0)

    total = len(cases)
    mrr = sum(reciprocal_ranks) / total if total > 0 else 0.0

    print("Retrieval Benchmark Report:")  # noqa: T201
    print(f"Total Cases: {total}")  # noqa: T201
    print(f"Hit@1: {hit_1}/{total} ({(hit_1 / total) * 100:.1f}%)")  # noqa: T201
    print(f"Hit@3: {hit_3}/{total} ({(hit_3 / total) * 100:.1f}%)")  # noqa: T201
    print(f"Hit@5: {hit_5}/{total} ({(hit_5 / total) * 100:.1f}%)")  # noqa: T201
    print(f"MRR:   {mrr:.3f}")  # noqa: T201


@pytest.mark.parametrize("case", load_cases())
def test_hit_rate_at_5(case: dict[str, Any]) -> None:
    """Verify semantic search retrieves expected comic in top-5."""
    remote_url = os.environ.get("XKCD_TEST_URL")
    if remote_url:
        retrieved = search_remote(remote_url, case["query"], k=5)
    else:
        retrieved = search_local(case["query"], k=5)
    assert case["number"] in retrieved


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Evaluate retrieval benchmarks")
    parser.add_argument("--url", type=str, default=None, help="Remote service URL")
    args = parser.parse_args()

    evaluate_benchmarks(load_cases(), url=args.url)

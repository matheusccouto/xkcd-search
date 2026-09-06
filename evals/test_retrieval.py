"""Retrieval evaluation benchmark suite using vanilla pytest."""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pytest

from xkcd_search.ingest import (
    fetch_explainxkcd,
    fetch_xkcd,
    new_client,
    open_or_create_table,
    upsert_comic,
)
from xkcd_search.search import SearchEngine

if TYPE_CHECKING:
    from lancedb.table import Table

DATASET_PATH = Path(__file__).resolve().parent / "dataset.json"
EVAL_LANCE_DIR = Path(__file__).resolve().parent / "data" / "lance"
TOP_K = 5
RANK_1 = 1
RANK_3 = 3


def load_cases() -> list[dict[str, Any]]:
    """Load evaluation test cases from dataset.json."""
    data = json.loads(DATASET_PATH.read_text(encoding="utf-8"))
    cases: list[dict[str, Any]] = []
    for entry in data:
        num = entry["comic_number"]
        title = entry["title"]
        cases.extend(
            {
                "comic_number": num,
                "title": title,
                "query": query,
                "id": f"#{num}_{query[:25]}",
            }
            for query in entry["queries"]
        )
    return cases


EVAL_CASES = load_cases()
REQUIRED_NUMBERS = sorted({c["comic_number"] for c in EVAL_CASES})


def ensure_eval_corpus() -> Table:
    """Ensure local LanceDB table exists and contains all required comics."""
    table = open_or_create_table(EVAL_LANCE_DIR)
    existing = set(table.to_arrow()["number"].to_pylist()) if len(table) > 0 else set()
    missing = [n for n in REQUIRED_NUMBERS if n not in existing]

    if missing:
        with new_client() as client:
            for n in missing:
                comic = fetch_xkcd(n, client)
                article = fetch_explainxkcd(n, client)
                upsert_comic(table, comic, article)
    return table


@pytest.fixture(scope="session")
def search_engine() -> SearchEngine:
    """Provide SearchEngine connected to the evaluation corpus."""
    table = ensure_eval_corpus()
    return SearchEngine(table=table)


@pytest.mark.parametrize("case", EVAL_CASES, ids=[c["id"] for c in EVAL_CASES])
def test_retrieval(case: dict[str, Any], search_engine: SearchEngine) -> None:
    """Verify semantic search returns expected comic in top-5."""
    hits = search_engine.search(case["query"], k=TOP_K)
    retrieved = [h["number"] for h in hits]
    assert case["comic_number"] in retrieved, (
        f"Query '{case['query']}' failed to retrieve #{case['comic_number']} "
        f"({case['title']}) in top-{TOP_K}. Got: {retrieved}"
    )


def run_benchmark() -> None:
    """CLI benchmark runner calculating HitRate and MRR across all queries."""
    table = ensure_eval_corpus()
    engine = SearchEngine(table=table)

    total = len(EVAL_CASES)
    hits_1 = 0
    hits_3 = 0
    hits_5 = 0
    rr_sum = 0.0

    print(f"\nEvaluating {total} queries across {len(REQUIRED_NUMBERS)} comics...\n")
    print(f"{'Target':<22} | {'Rank':<6} | {'RR':<6} | {'Query'}")
    print("-" * 75)

    for case in EVAL_CASES:
        query = case["query"]
        expected = case["comic_number"]
        title = case["title"]

        hits = engine.search(query, k=TOP_K)
        retrieved = [h["number"] for h in hits]

        if expected in retrieved:
            rank = retrieved.index(expected) + 1
            rr = 1.0 / rank
            if rank == RANK_1:
                hits_1 += 1
            if rank <= RANK_3:
                hits_3 += 1
            hits_5 += 1
        else:
            rank = -1
            rr = 0.0

        rr_sum += rr
        rank_str = str(rank) if rank > 0 else "MISS"
        target_str = f"#{expected} {title}"[:21]
        print(f"{target_str:<22} | {rank_str:<6} | {rr:<6.2f} | {query}")

    mrr = rr_sum / total if total > 0 else 0.0
    print("=" * 75)
    print(f"Total Queries:         {total}")
    print(f"Hit Rate @ 1:          {hits_1}/{total} ({(hits_1 / total) * 100:.1f}%)")
    print(f"Hit Rate @ 3:          {hits_3}/{total} ({(hits_3 / total) * 100:.1f}%)")
    print(f"Hit Rate @ 5:          {hits_5}/{total} ({(hits_5 / total) * 100:.1f}%)")
    print(f"Mean Reciprocal Rank:  {mrr:.3f}")
    print("=" * 75)


if __name__ == "__main__":
    run_benchmark()

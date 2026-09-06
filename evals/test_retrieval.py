"""Retrieval evaluation benchmark suite for local LanceDB and deployed endpoints."""

from __future__ import annotations

import argparse
import json
import math
import statistics
import time
from pathlib import Path
from typing import Any

import pytest

from evals.conftest import (
    EVAL_LANCE_DIR,
    Retriever,
    create_retriever,
    ensure_eval_corpus,
)

__all__ = ["EVAL_LANCE_DIR", "ensure_eval_corpus", "test_retrieval"]

DATASET_PATH = Path(__file__).resolve().parent / "dataset.json"
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


@pytest.mark.parametrize("case", EVAL_CASES, ids=[c["id"] for c in EVAL_CASES])
def test_retrieval(case: dict[str, Any], retriever: Retriever) -> None:
    """Verify semantic search returns expected comic in top-5."""
    hits = retriever(case["query"], k=TOP_K)
    retrieved = [h["number"] for h in hits]
    assert case["comic_number"] in retrieved, (
        f"Query '{case['query']}' failed to retrieve #{case['comic_number']} "
        f"({case['title']}) in top-{TOP_K}. Got: {retrieved}"
    )


def print_summary(
    target: str,
    stats: dict[str, Any],
    latencies: list[float],
) -> None:
    """Print formatted evaluation summary metrics."""
    total = stats["total"]
    h1 = stats["hits_1"]
    h3 = stats["hits_3"]
    h5 = stats["hits_5"]
    mrr = stats["mrr"]
    ndcg = stats["ndcg"]
    mean_lat = statistics.mean(latencies) if latencies else 0.0
    median_lat = statistics.median(latencies) if latencies else 0.0

    print("=" * 84)
    print(f"Benchmark Target:      {target}")
    print(f"Total Queries:         {total}")
    print(f"Hit Rate @ 1:          {h1}/{total} ({(h1 / total) * 100:.1f}%)")
    print(f"Hit Rate @ 3:          {h3}/{total} ({(h3 / total) * 100:.1f}%)")
    print(f"Hit Rate @ 5:          {h5}/{total} ({(h5 / total) * 100:.1f}%)")
    print(f"Mean Reciprocal Rank:  {mrr:.3f}")
    print(f"NDCG @ 5:              {ndcg:.3f}")
    print(f"Mean Latency:          {mean_lat:.1f} ms")
    print(f"Median Latency:        {median_lat:.1f} ms")
    print("=" * 84)


def run_benchmark(url: str | None = None) -> None:
    """Run evaluation benchmark calculating HitRate, MRR, NDCG@5, and latency."""
    retriever_fn, target_desc = create_retriever(url)
    total = len(EVAL_CASES)
    hits_1 = hits_3 = hits_5 = 0
    rr_sum = ndcg_sum = 0.0
    latencies: list[float] = []

    print(f"\nEvaluating {total} queries against {target_desc}...\n")
    print(f"{'Target':<22} | {'Rank':<6} | {'RR':<6} | {'NDCG':<6} | {'ms':<6} | Query")
    print("-" * 84)

    for case in EVAL_CASES:
        t0 = time.perf_counter()
        hits = retriever_fn(case["query"], k=TOP_K)
        lat = (time.perf_counter() - t0) * 1000.0
        latencies.append(lat)

        retrieved = [h["number"] for h in hits]
        exp = case["comic_number"]
        if exp in retrieved:
            rank = retrieved.index(exp) + 1
            rr = 1.0 / rank
            ndcg = 1.0 / math.log2(rank + 1)
            hits_1 += int(rank == RANK_1)
            hits_3 += int(rank <= RANK_3)
            hits_5 += 1
        else:
            rank = -1
            rr = ndcg = 0.0

        rr_sum += rr
        ndcg_sum += ndcg
        rank_str = str(rank) if rank > 0 else "MISS"
        target_str = f"#{exp} {case['title']}"[:21]
        print(
            f"{target_str:<22} | {rank_str:<6} | {rr:<6.2f} | "
            f"{ndcg:<6.2f} | {lat:<6.0f} | {case['query']}"
        )

    stats = {
        "total": total,
        "hits_1": hits_1,
        "hits_3": hits_3,
        "hits_5": hits_5,
        "mrr": rr_sum / total if total > 0 else 0.0,
        "ndcg": ndcg_sum / total if total > 0 else 0.0,
    }
    print_summary(target_desc, stats, latencies)


def main() -> None:
    """CLI entrypoint for retrieval benchmark."""
    parser = argparse.ArgumentParser(description="Evaluate search retrieval quality.")
    parser.add_argument(
        "--url",
        type=str,
        default=None,
        help="Optional base URL of deployed search API",
    )
    args = parser.parse_args()
    run_benchmark(url=args.url)


if __name__ == "__main__":
    main()

"""DeepEval test suite for vector database retrieval quality."""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pytest
from deepeval import assert_test
from deepeval.test_case import LLMTestCase

from evals.metrics import HitRateMetric, MRRMetric
from evals.sampler import DEFAULT_EVAL_LANCE_DIR, ensure_eval_corpus
from xkcd_search.search import SearchEngine

if TYPE_CHECKING:
    from lancedb.table import Table

DATASET_PATH = Path(__file__).resolve().parent / "dataset.json"


RANK_TOP_1 = 1
RANK_TOP_3 = 3
RANK_TOP_5 = 5


def load_evaluation_cases() -> list[dict[str, Any]]:
    """Load and flatten golden evaluation cases from dataset.json."""
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
                "id": f"#{num}_{query[:30]}",
            }
            for query in entry["queries"]
        )
    return cases


EVAL_CASES = load_evaluation_cases()
ALL_COMIC_NUMBERS = sorted({c["comic_number"] for c in EVAL_CASES})


@pytest.fixture(scope="session")
def eval_table() -> Table:
    """Ensure evaluation corpus exists and contains all required comics."""
    return ensure_eval_corpus(DEFAULT_EVAL_LANCE_DIR, ALL_COMIC_NUMBERS)


@pytest.fixture(scope="session")
def eval_engine(eval_table: Table) -> SearchEngine:
    """Provide SearchEngine initialized with evaluation corpus."""
    return SearchEngine(table=eval_table)


@pytest.mark.parametrize("case", EVAL_CASES, ids=[c["id"] for c in EVAL_CASES])
def test_vdb_retrieval_quality(case: dict[str, Any], eval_engine: SearchEngine) -> None:
    """Evaluate retrieval quality for a single query using DeepEval metrics."""
    query = case["query"]
    expected_number = case["comic_number"]
    expected_title = case["title"]

    hits = eval_engine.search(query, k=5)
    retrieved_numbers = [h["number"] for h in hits]
    actual_output = (
        f"Comic #{hits[0]['number']}: {hits[0]['title']}" if hits else "No results"
    )

    test_case = LLMTestCase(
        input=query,
        actual_output=actual_output,
        expected_output=f"Comic #{expected_number}: {expected_title}",
        retrieval_context=[h["explanation"] for h in hits],
        additional_metadata={
            "expected_comic": expected_number,
            "expected_title": expected_title,
            "retrieved_comics": retrieved_numbers,
        },
    )

    hit_metric = HitRateMetric(k=5, threshold=1.0)
    mrr_metric = MRRMetric(k=5, threshold=0.2)

    assert_test(test_case, [hit_metric, mrr_metric])


def run_evaluation_report() -> None:
    """Run full evaluation suite and print an aggregated benchmark report."""
    print(f"\nEnsuring evaluation corpus with {len(ALL_COMIC_NUMBERS)} comics...")
    table = ensure_eval_corpus(DEFAULT_EVAL_LANCE_DIR, ALL_COMIC_NUMBERS)
    engine = SearchEngine(table=table)

    total = len(EVAL_CASES)
    hits_at_1 = 0
    hits_at_3 = 0
    hits_at_5 = 0
    rr_sum = 0.0

    print(f"\nEvaluating {total} queries across {len(ALL_COMIC_NUMBERS)} comics...\n")
    print(f"{'Target':<22} | {'Rank':<6} | {'RR':<6} | {'Query'}")
    print("-" * 80)

    for case in EVAL_CASES:
        query = case["query"]
        expected = case["comic_number"]
        title = case["title"]

        hits = engine.search(query, k=5)
        retrieved = [h["number"] for h in hits]

        if expected in retrieved:
            rank = retrieved.index(expected) + 1
            rr = round(1.0 / rank, 4)
            if rank == RANK_TOP_1:
                hits_at_1 += 1
            if rank <= RANK_TOP_3:
                hits_at_3 += 1
            if rank <= RANK_TOP_5:
                hits_at_5 += 1
        else:
            rank = -1
            rr = 0.0

        rr_sum += rr
        rank_str = str(rank) if rank > 0 else "MISS"
        target_str = f"#{expected} {title}"[:21]
        print(f"{target_str:<22} | {rank_str:<6} | {rr:<6.2f} | {query}")

    mrr = rr_sum / total if total > 0 else 0.0
    hit_1_pct = (hits_at_1 / total) * 100 if total > 0 else 0.0
    hit_3_pct = (hits_at_3 / total) * 100 if total > 0 else 0.0
    hit_5_pct = (hits_at_5 / total) * 100 if total > 0 else 0.0

    print("=" * 80)
    print("VDB RETRIEVAL BENCHMARK SUMMARY")
    print("=" * 80)
    print(f"Total Test Queries:     {total}")
    print(f"Hit Rate @ 1:           {hits_at_1}/{total} ({hit_1_pct:.1f}%)")
    print(f"Hit Rate @ 3:           {hits_at_3}/{total} ({hit_3_pct:.1f}%)")
    print(f"Hit Rate @ 5:           {hits_at_5}/{total} ({hit_5_pct:.1f}%)")
    print(f"Mean Reciprocal Rank:   {mrr:.3f}")
    print("=" * 80)


if __name__ == "__main__":
    run_evaluation_report()

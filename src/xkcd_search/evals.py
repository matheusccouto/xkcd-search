"""Retrieval eval runner: hit@k and MRR over a committed eval set.

Run `uv run evals --index <path>`. The runner drives the same `query_top_k`
retrieval path the `search_xkcd` tool serves, so the reported numbers reflect
what clients actually receive. The eval set (committed as `eval_set.json`) is a
list of `(query, expected comic)` pairs; a query whose expected comic is absent
from the evaluated index is skipped, never a failure.
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from collections.abc import Callable, Collection, Sequence
from dataclasses import dataclass
from pathlib import Path

from xkcd_search.builder import encode, get_indexed_comics, open_connection, query_top_k

EVAL_SET_PATH = Path(__file__).resolve().parent.parent.parent / "eval_set.json"
EVAL_DEPTH = 100  # how deep to rank for MRR; hit@1 and hit@5 read from the same list

Retriever = Callable[[str], list[int]]


def hit_at_k(ranked: list[int], expected: int, k: int) -> bool:
    """True when `expected` is among the first `k` of `ranked`."""
    return expected in ranked[:k]


def reciprocal_rank(ranked: list[int], expected: int) -> float:
    """1/(1-based rank of `expected` in `ranked`); 0 when absent."""
    try:
        return 1.0 / (ranked.index(expected) + 1)
    except ValueError:
        return 0.0


def hit_rate(results: Sequence[tuple[list[int], int]], k: int) -> float:
    """Fraction of `(ranked, expected)` pairs whose expected comic is in the top-k."""
    if not results:
        return 0.0
    return sum(hit_at_k(ranked, expected, k) for ranked, expected in results) / len(results)


def mrr(results: Sequence[tuple[list[int], int]]) -> float:
    """Mean reciprocal rank over `(ranked, expected)` pairs."""
    if not results:
        return 0.0
    return sum(reciprocal_rank(ranked, expected) for ranked, expected in results) / len(results)


@dataclass(frozen=True)
class EvalQuery:
    query: str
    expected_number: int


@dataclass(frozen=True)
class EvalReport:
    queries: int
    run: int
    skipped: int
    hit_at_1: float
    hit_at_5: float
    mrr: float


def load_eval_set(path: Path) -> list[EvalQuery]:
    """Read the committed eval-set shape: `{"queries": [{"query", "expected_number"}]}`."""
    data = json.loads(path.read_text())
    return [
        EvalQuery(query=str(q["query"]), expected_number=int(q["expected_number"]))
        for q in data["queries"]
    ]


def run_eval(
    queries: Sequence[EvalQuery],
    retriever: Retriever,
    indexed: Collection[int],
) -> EvalReport:
    """Rank every query and aggregate hit@1, hit@5, and MRR.

    A query whose expected comic is not in `indexed` is skipped and excluded
    from all metric denominators. `retriever` maps a query string to ranked
    comic numbers; tests inject a stub, production binds `query_top_k` to the
    opened index.
    """
    indexed_numbers = set(indexed)
    results: list[tuple[list[int], int]] = []
    skipped = 0
    for item in queries:
        if item.expected_number not in indexed_numbers:
            skipped += 1
            continue
        results.append((retriever(item.query), item.expected_number))

    run = len(results)
    return EvalReport(
        queries=len(queries),
        run=run,
        skipped=skipped,
        hit_at_1=hit_rate(results, 1),
        hit_at_5=hit_rate(results, 5),
        mrr=mrr(results),
    )


def default_retriever(conn: sqlite3.Connection) -> Retriever:
    """Bind `query_top_k` to the opened index, encoding queries exactly as the tool does."""

    def retrieve(query: str) -> list[int]:
        return query_top_k(conn, encode([query])[0], EVAL_DEPTH)

    return retrieve


def print_report(report: EvalReport) -> None:
    print(f"hit@1    {report.hit_at_1:.3f}")
    print(f"hit@5    {report.hit_at_5:.3f}")
    print(f"MRR      {report.mrr:.3f}")
    print(f"total    {report.queries}")
    print(f"run      {report.run}")
    print(f"skipped  {report.skipped}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="evals",
        description="Run the committed eval set through the search_xkcd retrieval path.",
    )
    parser.add_argument("--index", required=True, help="path to the index.sqlite to evaluate")
    parser.add_argument(
        "--eval-set",
        default=str(EVAL_SET_PATH),
        help="path to the eval set (default: eval_set.json at the repo root)",
    )
    args = parser.parse_args(argv)

    eval_set_path = Path(args.eval_set)
    if not eval_set_path.exists():
        print(f"evals: eval set not found: {eval_set_path}", file=sys.stderr)
        return 2
    index_path = Path(args.index)
    if not index_path.exists():
        print(f"evals: index not found: {index_path}", file=sys.stderr)
        return 2
    queries = load_eval_set(eval_set_path)

    conn = open_connection(index_path, read_only=True)
    try:
        report = run_eval(
            queries,
            retriever=default_retriever(conn),
            indexed=set(get_indexed_comics(conn)),
        )
    finally:
        conn.close()
    print_report(report)
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""Unit tests for the eval runner metrics and orchestration.

The metric functions are pure math over fixed ranked lists; the runner is
exercised with a stub retriever, so nothing here touches an index or the
network.
"""

from __future__ import annotations

import json

from xkcd_search.evals import EVAL_SET_PATH, EvalQuery, hit_at_k, load_eval_set, mrr, run_eval


def test_hit_at_1_true_when_expected_is_first():
    assert hit_at_k([7, 2, 9], expected=7, k=1)


def test_hit_at_1_false_when_expected_is_not_first():
    assert not hit_at_k([7, 2, 9], expected=2, k=1)


def test_hit_at_5_true_when_expected_within_top_five():
    assert hit_at_k([7, 2, 9, 4, 1, 8], expected=4, k=5)


def test_hit_at_5_true_when_expected_is_exactly_at_k():
    assert hit_at_k([7, 2, 9, 4, 1], expected=1, k=5)


def test_hit_at_k_false_when_expected_absent():
    assert not hit_at_k([7, 2, 9], expected=5, k=5)


def test_hit_at_k_ignores_rankings_beyond_k():
    assert not hit_at_k([7, 2, 9, 4, 1, 8], expected=8, k=5)


def test_mrr_empty_is_zero():
    assert mrr([]) == 0.0


def test_mrr_perfect_rank_one_for_all():
    assert mrr([([1, 2, 3], 1), ([5, 6], 5)]) == 1.0


def test_mrr_averages_reciprocal_ranks():
    results = [([1, 2, 3], 1), ([2, 3, 1], 1), ([1, 2, 3], 2)]
    assert mrr(results) == (1.0 + 1.0 / 3 + 1.0 / 2) / 3


def test_mrr_counts_absent_expected_as_zero():
    assert mrr([([1, 2, 3], 1), ([2, 3, 4], 99)]) == 0.5


def test_load_eval_set_parses_committed_shape(tmp_path):
    path = tmp_path / "eval_set.json"
    path.write_text(json.dumps({"queries": [{"query": "overton window", "expected_number": 3230}]}))
    queries = load_eval_set(path)
    assert queries == [EvalQuery(query="overton window", expected_number=3230)]


def test_committed_eval_set_has_forty_queries_with_unique_expected_comics():
    queries = load_eval_set(EVAL_SET_PATH)
    assert len(queries) == 40
    expected = [q.expected_number for q in queries]
    assert len(set(expected)) == len(expected), "expected comic must be unique per query"
    assert all(q.query.strip() for q in queries)


def _stub_retriever(rankings: dict[str, list[int]]):
    def retrieve(query: str) -> list[int]:
        return rankings[query]

    return retrieve


def test_runner_reports_metrics_over_run_queries():
    queries = [
        EvalQuery(query="first", expected_number=1),
        EvalQuery(query="second", expected_number=2),
    ]
    retriever = _stub_retriever({"first": [1, 2, 3], "second": [3, 2, 1]})
    report = run_eval(queries, retriever, indexed={1, 2, 3})

    assert report.queries == 2
    assert report.run == 2
    assert report.skipped == 0
    assert report.hit_at_1 == 0.5
    assert report.hit_at_5 == 1.0
    assert report.mrr == 0.75


def test_runner_skips_expected_comic_absent_from_index():
    queries = [
        EvalQuery(query="known", expected_number=1),
        EvalQuery(query="missing", expected_number=99),
    ]
    retriever = _stub_retriever({"known": [1, 2, 3]})
    report = run_eval(queries, retriever, indexed={1, 2, 3})

    assert report.queries == 2
    assert report.run == 1
    assert report.skipped == 1
    assert report.hit_at_1 == 1.0
    assert report.hit_at_5 == 1.0
    assert report.mrr == 1.0


def test_runner_never_calls_retriever_for_skipped_query():
    queries = [EvalQuery(query="missing", expected_number=99)]

    def explode(query: str) -> list[int]:
        raise AssertionError(f"retriever must not be called for {query!r}")

    report = run_eval(queries, explode, indexed={1, 2, 3})
    assert report.skipped == 1
    assert report.run == 0
    assert report.hit_at_1 == 0.0
    assert report.hit_at_5 == 0.0
    assert report.mrr == 0.0


def test_runner_empty_eval_set():
    report = run_eval([], _stub_retriever({}), indexed={1, 2, 3})
    assert report.queries == 0
    assert report.run == 0
    assert report.skipped == 0
    assert report.mrr == 0.0

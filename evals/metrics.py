"""Retrieval quality metrics for DeepEval evaluation framework."""

from __future__ import annotations

from typing import TYPE_CHECKING

from deepeval.metrics import BaseMetric

if TYPE_CHECKING:
    from deepeval.test_case import LLMTestCase


class HitRateMetric(BaseMetric):
    """Measures whether the target comic is present in top-k results."""

    def __init__(self, k: int = 5, threshold: float = 1.0) -> None:
        """Initialize HitRateMetric with cutoff k and minimum success threshold."""
        super().__init__()
        self.k = k
        self.threshold = threshold

    @property
    def __name__(self) -> str:
        """Return metric name including cutoff k."""
        return f"HitRate@{self.k}"

    def measure(self, test_case: LLMTestCase) -> float:
        """Calculate hit rate (1.0 if target is within top-k, 0.0 otherwise)."""
        metadata = test_case.additional_metadata or {}
        expected = metadata.get("expected_comic")
        retrieved = metadata.get("retrieved_comics", [])

        top_k = retrieved[: self.k]
        hit = expected in top_k
        self.score = 1.0 if hit else 0.0
        self.success = self.score >= self.threshold

        if hit:
            rank = top_k.index(expected) + 1
            self.reason = f"Comic #{expected} at rank {rank} (top-{self.k})."
        else:
            self.reason = f"Comic #{expected} not found in top-{self.k}: {top_k}."
        return self.score

    async def a_measure(self, test_case: LLMTestCase) -> float:
        """Asynchronously calculate hit rate."""
        return self.measure(test_case)

    def is_successful(self) -> bool:
        """Return True if metric score meets or exceeds threshold."""
        return bool(self.success)


class MRRMetric(BaseMetric):
    """Measures Mean Reciprocal Rank (1/rank) of target comic within top-k."""

    def __init__(self, k: int = 5, threshold: float = 0.2) -> None:
        """Initialize MRRMetric with cutoff k and minimum success threshold."""
        super().__init__()
        self.k = k
        self.threshold = threshold

    @property
    def __name__(self) -> str:
        """Return metric name including cutoff k."""
        return f"MRR@{self.k}"

    def measure(self, test_case: LLMTestCase) -> float:
        """Calculate reciprocal rank of target comic."""
        metadata = test_case.additional_metadata or {}
        expected = metadata.get("expected_comic")
        retrieved = metadata.get("retrieved_comics", [])

        top_k = retrieved[: self.k]
        if expected in top_k:
            rank = top_k.index(expected) + 1
            self.score = round(1.0 / rank, 4)
            self.reason = f"Comic #{expected} at rank {rank} (RR = {self.score})."
        else:
            self.score = 0.0
            self.reason = f"Comic #{expected} not found in top-{self.k} results."

        self.success = self.score >= self.threshold
        return self.score

    async def a_measure(self, test_case: LLMTestCase) -> float:
        """Asynchronously calculate reciprocal rank."""
        return self.measure(test_case)

    def is_successful(self) -> bool:
        """Return True if metric score meets or exceeds threshold."""
        return bool(self.success)

"""Cross-encoder reranking for retrieval candidates."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

from fastembed.rerank.cross_encoder import TextCrossEncoder

if TYPE_CHECKING:
    from collections.abc import Iterable

RERANK_MODEL = "Xenova/ms-marco-MiniLM-L-6-v2"


class Reranker(Protocol):
    """Scores candidate documents against a query."""

    def score(self, query: str, documents: dict[int, str]) -> dict[int, float]:
        """Return a relevance score per document key, higher being closer."""
        ...


class CrossEncoderReranker:
    """Scores candidates with a local cross-encoder running on ONNX."""

    def __init__(self, model: str = RERANK_MODEL) -> None:
        """Remember the model name; the model itself loads on first score."""
        self.model_name = model
        self._model: TextCrossEncoder | None = None

    @property
    def model(self) -> TextCrossEncoder:
        """Load the cross-encoder on first use, so import stays cheap."""
        if self._model is None:
            self._model = TextCrossEncoder(model_name=self.model_name)
        return self._model

    def score(self, query: str, documents: dict[int, str]) -> dict[int, float]:
        """Return a relevance score per comic number."""
        keys = list(documents)
        scores: Iterable[float] = self.model.rerank(query, [documents[k] for k in keys])
        return {k: float(s) for k, s in zip(keys, scores, strict=True)}

"""Cross-encoder reranking for retrieval candidates."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

from fastembed.rerank.cross_encoder import TextCrossEncoder

if TYPE_CHECKING:
    from collections.abc import Iterable

RERANK_MODEL = "Xenova/ms-marco-MiniLM-L-6-v2"


class Reranker(Protocol):
    """Reorders candidate documents by relevance to a query."""

    def order(self, query: str, documents: dict[int, str]) -> list[int]:
        """Return document keys ordered by decreasing relevance."""
        ...


class CrossEncoderReranker:
    """Orders candidates with a local cross-encoder running on ONNX."""

    def __init__(self, model: str = RERANK_MODEL) -> None:
        """Load the cross-encoder model."""
        self.model = TextCrossEncoder(model_name=model)

    def order(self, query: str, documents: dict[int, str]) -> list[int]:
        """Return comic numbers ordered by decreasing relevance."""
        keys = list(documents)
        scores: Iterable[float] = self.model.rerank(query, [documents[k] for k in keys])
        pairs = zip(keys, scores, strict=True)
        return [k for k, _ in sorted(pairs, key=lambda pair: -pair[1])]

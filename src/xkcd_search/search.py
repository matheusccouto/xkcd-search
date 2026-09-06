"""Core semantic search engine for xkcd comics."""

from __future__ import annotations

import os
from typing import TYPE_CHECKING, Any

import lancedb
from huggingface_hub import InferenceClient

if TYPE_CHECKING:
    from lancedb.table import Table

EMBED_MODEL = "BAAI/bge-small-en-v1.5"
DEFAULT_LANCE_URI = "hf://datasets/couto/xkcd"


class SearchEngine:
    """Semantic search engine backed by LanceDB and Hugging Face inference."""

    def __init__(
        self,
        table: Table | None = None,
        client: InferenceClient | None = None,
    ) -> None:
        """Initialize search engine with optional pre-connected table."""
        self._table = table
        self._client = client

    @property
    def table(self) -> Table:
        """Get or lazily connect to LanceDB table."""
        if self._table is None:
            self._table = self._connect()
        return self._table

    @property
    def client(self) -> InferenceClient:
        """Get or create InferenceClient."""
        if self._client is None:
            self._client = InferenceClient(token=os.environ.get("HF_TOKEN"))
        return self._client

    @staticmethod
    def _connect() -> Table:
        uri = os.environ.get("XKCD_LANCE_URI", DEFAULT_LANCE_URI)
        token = os.environ.get("HF_TOKEN")
        storage = {"token": token} if token else None
        db = lancedb.connect(uri, storage_options=storage)
        return db.open_table("comics")

    def encode(self, query: str) -> list[float]:
        """Encode query text into a vector using Hugging Face Serverless Inference."""
        vec = self.client.feature_extraction(query, model=EMBED_MODEL)
        return vec.tolist() if hasattr(vec, "tolist") else list(vec)

    def search(self, query: str, k: int = 5) -> list[dict[str, Any]]:
        """Search comics by semantic relevance to query."""
        if not query.strip():
            return []
        k = max(1, min(int(k), 20))
        raw_hits = self.table.search(self.encode(query)).limit(k * 4).to_list()

        seen: set[int] = set()
        comics: list[dict[str, Any]] = []
        for r in raw_hits:
            num = int(r["number"])
            if num not in seen:
                seen.add(num)
                comics.append(
                    {
                        "number": num,
                        "title": str(r["title"]),
                        "url": str(r["url"]),
                        "image_url": str(r["image_url"]),
                        "alt_text": str(r["alt_text"]),
                        "transcript": str(r["transcript"]),
                        "explanation": str(r["explanation"]),
                    }
                )
                if len(comics) == k:
                    break
        return comics

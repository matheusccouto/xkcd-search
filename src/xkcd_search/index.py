"""Deep SearchIndex managing normalized LanceDB tables and swappable embedders."""

from __future__ import annotations

import os
from typing import TYPE_CHECKING, Protocol

import lancedb
import pyarrow as pa
from huggingface_hub import InferenceClient

from xkcd_search.chunker import Chunker, FixedWindowChunker
from xkcd_search.models import Chunk, Comic

if TYPE_CHECKING:
    from pathlib import Path

    from lancedb.table import Table

EMBED_MODEL = "BAAI/bge-small-en-v1.5"
DEFAULT_LANCE_URI = "hf://datasets/couto/xkcd"

COMICS_SCHEMA = pa.schema(
    [
        ("number", pa.int32()),
        ("title", pa.string()),
        ("url", pa.string()),
        ("image_url", pa.string()),
        ("alt_text", pa.string()),
        ("transcript", pa.string()),
        ("explanation", pa.string()),
    ]
)

CHUNKS_SCHEMA = pa.schema(
    [
        ("comic_number", pa.int32()),
        ("text", pa.string()),
        ("kind", pa.string()),
        ("vector", pa.list_(pa.float32(), 384)),
    ]
)


class TextEmbedder(Protocol):
    """Protocol for embedding text into vector representations."""

    def embed(self, text: str) -> list[float]:
        """Embed a single text string."""
        ...

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Embed a batch of text strings."""
        ...


class HuggingFaceEmbedder:
    """Embeds text using Hugging Face Serverless Inference."""

    def __init__(
        self,
        model: str = EMBED_MODEL,
        token: str | None = None,
    ) -> None:
        """Initialize HuggingFace embedder with model and token."""
        self.model = model
        self.token = token or os.getenv("HF_TOKEN")

    @property
    def client(self) -> InferenceClient:
        """Get or initialize Hugging Face InferenceClient."""
        return InferenceClient(token=self.token)

    def embed(self, text: str) -> list[float]:
        """Embed a single text string into a vector."""
        return self.embed_batch([text])[0]

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Embed a batch of texts into vectors."""
        if not texts:
            return []
        batch_size = 32
        results: list[list[float]] = []
        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]
            vecs = self.client.feature_extraction(batch, model=self.model)
            results.extend([list(v) for v in vecs])
        return results


class SearchIndex:
    """Manages normalized comics and chunks tables in LanceDB."""

    def __init__(
        self,
        uri: str | Path | None = None,
        embedder: TextEmbedder | None = None,
        chunker: Chunker | None = None,
        token: str | None = None,
    ) -> None:
        """Initialize search index with LanceDB URI, embedder, and chunker."""
        self._uri = uri
        self.token = token or os.getenv("HF_TOKEN")
        self.embedder = embedder or HuggingFaceEmbedder(token=self.token)
        self.chunker = chunker or FixedWindowChunker()

    @property
    def uri(self) -> str:
        """Resolve dataset URI from parameter or environment variable."""
        return str(self._uri or os.getenv("XKCD_DATASET_URI", DEFAULT_LANCE_URI))

    @property
    def db(self) -> lancedb.DBConnection:
        """Connect to LanceDB storage."""
        storage_options = {"token": self.token} if self.token else None
        return lancedb.connect(self.uri, storage_options=storage_options)

    @property
    def comics_table(self) -> Table:
        """Open the comics LanceDB table."""
        return self.db.open_table("comics")

    @property
    def chunks_table(self) -> Table:
        """Open the chunks LanceDB table."""
        return self.db.open_table("chunks")

    def search(self, query: str, k: int = 5) -> list[Comic]:
        """Retrieve top-k relevant comics matching query."""
        if not query.strip():
            return []

        existing_tables = set(self.db.list_tables().tables)
        if "comics" not in existing_tables or "chunks" not in existing_tables:
            return []

        query_vec = self.embedder.embed(query)
        chunks_results = self.chunks_table.search(query_vec).limit(k * 4).to_list()
        if not chunks_results:
            return []

        scores: dict[int, float] = {}
        for row in chunks_results:
            c_num = row["comic_number"]
            if c_num not in scores:
                dist = float(row["_distance"])
                scores[c_num] = 1.0 / (1.0 + dist)
            if len(scores) == k:
                break

        filter_expr = f"number in ({','.join(str(n) for n in scores)})"
        comic_rows = self.comics_table.search().where(filter_expr).to_list()
        comics_by_num = {row["number"]: row for row in comic_rows}

        results: list[Comic] = []
        for num, score in scores.items():
            if num in comics_by_num:
                results.append(Comic.from_dict(comics_by_num[num], score=score))

        return results

    def index(self, comics: list[Comic]) -> None:
        """Index comics and their chunks into normalized LanceDB tables."""
        if not comics:
            return

        comic_data = [c.to_dict() for c in comics]
        if "comics" in self.db.list_tables().tables:
            comics_table = self.db.open_table("comics")
            (
                comics_table.merge_insert("number")
                .when_matched_update_all()
                .when_not_matched_insert_all()
                .execute(comic_data)
            )
        else:
            self.db.create_table("comics", schema=COMICS_SCHEMA, data=comic_data)

        all_chunks: list[Chunk] = []
        for comic in comics:
            all_chunks.extend(self.chunker.chunk(comic))

        if not all_chunks:
            return

        chunk_texts = [c.text for c in all_chunks]
        vectors = self.embedder.embed_batch(chunk_texts)
        chunk_data = [
            {
                "comic_number": c.comic_number,
                "text": c.text,
                "kind": c.kind,
                "vector": v,
            }
            for c, v in zip(all_chunks, vectors, strict=True)
        ]

        nums_str = ",".join(str(c.number) for c in comics)
        if "chunks" in self.db.list_tables().tables:
            chunks_table = self.db.open_table("chunks")
            chunks_table.delete(f"comic_number in ({nums_str})")
            chunks_table.add(chunk_data)
        else:
            self.db.create_table("chunks", schema=CHUNKS_SCHEMA, data=chunk_data)

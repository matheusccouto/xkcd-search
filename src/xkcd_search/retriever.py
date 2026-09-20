"""Core semantic search retriever for xkcd comics."""

from __future__ import annotations

import os
from functools import cached_property
from typing import TYPE_CHECKING, Any

import lancedb
from huggingface_hub import InferenceClient
from langchain_core.documents import Document
from langchain_core.retrievers import BaseRetriever

if TYPE_CHECKING:
    from lancedb.table import Table

EMBED_MODEL = "BAAI/bge-small-en-v1.5"
DEFAULT_LANCE_URI = "hf://datasets/couto/xkcd"


class XKCDRetriever(BaseRetriever):
    """Retriever for xkcd comics using LanceDB and Hugging Face Inference API."""

    k: int = 5

    @property
    def client(self) -> InferenceClient:
        """Get HuggingFace InferenceClient."""
        return InferenceClient(token=os.getenv("HF_TOKEN"))

    @cached_property
    def table(self) -> Table:
        """Connect to LanceDB once, cached on first access."""
        token = os.getenv("HF_TOKEN")
        storage_options = {"token": token} if token else None
        uri = os.getenv("XKCD_DATASET_URI", DEFAULT_LANCE_URI)
        db = lancedb.connect(uri, storage_options=storage_options)
        return db.open_table("comics")

    def encode(self, query: str) -> list[float]:
        """Encode query text into a vector using Hugging Face Serverless Inference."""
        vec = self.client.feature_extraction(query, model=EMBED_MODEL)
        return list(vec)

    def _get_relevant_documents(
        self,
        query: str,
        **kwargs: Any,  # noqa: ANN401
    ) -> list[Document]:
        """Retrieve relevant comic documents from LanceDB."""
        if not query.strip():
            return []

        limit = kwargs.get("k", self.k)
        response = self.table.search(self.encode(query)).limit(limit).to_list()

        return [
            Document(
                page_content=str(row["image_url"]),
                metadata={
                    "number": row["number"],
                    "title": row["title"],
                    "url": row["url"],
                    "image_url": row["image_url"],
                    "alt_text": row["alt_text"],
                    "transcript": row["transcript"],
                    "explanation": row["explanation"],
                },
                id=str(row["number"]),
            )
            for row in response
        ]

"""Pytest fixtures and configuration for retrieval evaluation benchmark."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import TYPE_CHECKING, Any, Protocol

import httpx
import pytest

from xkcd_search.ingest import (
    fetch_explainxkcd,
    fetch_xkcd,
    new_client,
    open_or_create_table,
    upsert_comic,
)
from xkcd_search.search import SearchEngine

if TYPE_CHECKING:
    from lancedb.table import Table


class Retriever(Protocol):
    """Protocol for comic search retrieval callable."""

    def __call__(self, query: str, k: int = 5) -> list[dict[str, Any]]:
        """Retrieve top-k comics matching query."""
        ...


DATASET_PATH = Path(__file__).resolve().parent / "dataset.json"
EVAL_LANCE_DIR = Path(__file__).resolve().parent / "data" / "lance"


def get_required_numbers() -> list[int]:
    """Extract all distinct comic numbers required by dataset.json."""
    data = json.loads(DATASET_PATH.read_text(encoding="utf-8"))
    return sorted({entry["comic_number"] for entry in data})


def ensure_eval_corpus() -> Table:
    """Ensure local LanceDB table exists and contains all required evaluation comics."""
    table = open_or_create_table(EVAL_LANCE_DIR)
    existing = set(table.to_arrow()["number"].to_pylist()) if len(table) > 0 else set()
    missing = [n for n in get_required_numbers() if n not in existing]

    if missing:
        with new_client() as client:
            for n in missing:
                comic = fetch_xkcd(n, client)
                article = fetch_explainxkcd(n, client)
                upsert_comic(table, comic, article)
    return table


def create_retriever(base_url: str | None = None) -> tuple[Retriever, str]:
    """Create a retriever function targeting either remote API or local SearchEngine."""
    target = base_url or os.getenv("XKCD_TEST_URL") or os.getenv("XKCD_EVAL_URL")
    if target:
        endpoint = target.removesuffix("/mcp").rstrip("/")
        client = httpx.Client(base_url=endpoint, timeout=30.0)

        def remote_retriever(query: str, k: int = 5) -> list[dict[str, Any]]:
            resp = client.get("/api/search", params={"q": query, "k": k})
            resp.raise_for_status()
            return resp.json()

        return remote_retriever, f"remote ({endpoint})"

    table = ensure_eval_corpus()
    engine = SearchEngine(table=table)

    def local_retriever(query: str, k: int = 5) -> list[dict[str, Any]]:
        return engine.search(query, k=k)

    return local_retriever, "local LanceDB"


@pytest.fixture(scope="session")
def retriever() -> Retriever:
    """Provide a retrieval callable (local or remote based on environment variables)."""
    fn, _ = create_retriever()
    return fn

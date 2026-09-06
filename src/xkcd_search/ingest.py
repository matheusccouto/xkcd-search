"""Build and update the LanceDB index from xkcd.com and explainxkcd.com."""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path
from typing import Any

import httpx
import lancedb
import lancedb.table
import mwparserfromhell
import pyarrow as pa
from huggingface_hub import HfApi, InferenceClient, snapshot_download, upload_folder

from xkcd_search.search import EMBED_MODEL

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)

LANCE_DIR = Path.home() / ".cache" / "xkcd-search" / "lancedb"
XKCD_BASE = "https://xkcd.com"
EXPLAIN_API = "https://www.explainxkcd.com/wiki/api.php"
USER_AGENT = "xkcd-search (https://github.com/matheusccouto/xkcd-search-mcp)"
SKIP_NUMBERS = {404}
MIN_CHUNK_CHARS = 20
MAX_CHUNK_CHARS = 2000

SCHEMA = pa.schema(
    [
        ("number", pa.int32()),
        ("title", pa.string()),
        ("url", pa.string()),
        ("image_url", pa.string()),
        ("alt_text", pa.string()),
        ("transcript", pa.string()),
        ("explanation", pa.string()),
        ("chunk_kind", pa.string()),
        ("chunk_text", pa.string()),
        ("vector", pa.list_(pa.float32(), 384)),
    ]
)


def new_client(timeout: float = 30.0) -> httpx.Client:
    """Create HTTP client with default headers and timeout."""
    return httpx.Client(
        headers={"User-Agent": USER_AGENT},
        timeout=timeout,
        follow_redirects=True,
    )


def fetch_latest_xkcd_number(client: httpx.Client) -> int:
    """Fetch the latest comic number from xkcd.com."""
    resp = client.get(f"{XKCD_BASE}/info.0.json")
    resp.raise_for_status()
    return int(resp.json()["num"])


def fetch_xkcd(number: int, client: httpx.Client) -> dict[str, Any]:
    """Fetch comic metadata by comic number."""
    resp = client.get(f"{XKCD_BASE}/{number}/info.0.json")
    resp.raise_for_status()
    data = resp.json()
    return {
        "number": int(data["num"]),
        "title": str(data.get("title", "")),
        "url": f"{XKCD_BASE}/{number}/",
        "image_url": str(data.get("img", "")),
        "alt_text": str(data.get("alt", "")),
        "transcript": str(data.get("transcript", "")),
    }


def fetch_explainxkcd(number: int, client: httpx.Client) -> str:
    """Fetch explainxkcd article wikitext by comic number."""
    resp = client.get(
        EXPLAIN_API,
        params={
            "action": "parse",
            "page": str(number),
            "redirects": "1",
            "prop": "wikitext",
            "format": "json",
        },
    )
    if not resp.is_success:
        return ""
    data = resp.json()
    return str(data.get("parse", {}).get("wikitext", {}).get("*", ""))


def chunk_comic(comic: dict[str, Any], wikitext: str) -> list[tuple[str, str]]:
    """Break a comic and article into searchable (kind, text) chunks."""
    chunks = [("title", comic["title"])]
    if comic.get("transcript", "").strip():
        chunks.append(("transcript", comic["transcript"].strip()))
    if comic.get("alt_text", "").strip():
        chunks.append(("alt_text", comic["alt_text"].strip()))

    if wikitext:
        parsed = mwparserfromhell.parse(wikitext)
        for section in parsed.get_sections(flat=True, include_headings=True):
            headings = section.filter_headings()
            name = str(headings[0].title).strip().lower() if headings else "lead"
            body = str(section.strip_code()).strip()
            if len(body) >= MIN_CHUNK_CHARS:
                chunks.append((f"section:{name}", body[:MAX_CHUNK_CHARS]))
    return chunks


def encode(texts: list[str]) -> list[list[float]]:
    """Compute embeddings for text chunks using HF Serverless Inference."""
    client = InferenceClient(token=os.getenv("HF_TOKEN"))
    res = client.feature_extraction(texts, model=EMBED_MODEL)
    return res.tolist() if hasattr(res, "tolist") else [list(v) for v in res]


def open_or_create_table(path: Path | str) -> lancedb.table.Table:
    """Open existing LanceDB table or create a new one with schema."""
    Path(path).mkdir(parents=True, exist_ok=True)
    db = lancedb.connect(str(path))
    if "comics" in db.list_tables():
        return db.open_table("comics")
    return db.create_table("comics", schema=SCHEMA)


def upsert_comic(
    table: lancedb.table.Table,
    comic: dict[str, Any],
    article: str | object,
) -> None:
    """Upsert comic chunks and embeddings into LanceDB."""
    wikitext = (
        str(article.wikitext) if hasattr(article, "wikitext") else str(article or "")
    )
    chunks = chunk_comic(comic, wikitext)
    texts = [text for _, text in chunks]
    vectors = encode(texts) if texts else []
    explanation = (
        str(mwparserfromhell.parse(wikitext).strip_code()).strip() if wikitext else ""
    )

    records = [
        {
            "number": comic["number"],
            "title": comic["title"],
            "url": comic["url"],
            "image_url": comic["image_url"],
            "alt_text": comic["alt_text"],
            "transcript": comic["transcript"],
            "explanation": explanation,
            "chunk_kind": kind,
            "chunk_text": text,
            "vector": vec,
        }
        for (kind, text), vec in zip(chunks, vectors, strict=True)
    ]
    table.delete(f"number = {comic['number']}")
    if records:
        table.add(records)


def main() -> int:
    """Execute ingestion pipeline to update LanceDB and publish to Hugging Face."""
    repo_id = os.environ.get("HF_DATASET_REPO")
    token = os.environ.get("HF_TOKEN")
    if repo_id and not token:
        err_msg = "HF_TOKEN is required when HF_DATASET_REPO is configured"
        raise KeyError(err_msg)

    if repo_id and not (LANCE_DIR / "comics.lance").exists():
        api = HfApi(token=token)
        if api.repo_exists(repo_id=repo_id, repo_type="dataset"):
            logger.info("Restoring existing LanceDB dataset from %s...", repo_id)
            snapshot_download(
                repo_id=repo_id,
                repo_type="dataset",
                local_dir=str(LANCE_DIR),
                token=token,
            )

    table = open_or_create_table(LANCE_DIR)
    with new_client() as client:
        latest = fetch_latest_xkcd_number(client)
        existing_numbers = (
            set(table.to_arrow()["number"].to_pylist()) if len(table) > 0 else set()
        )
        logger.info(
            "Latest comic: %s; already indexed: %s", latest, len(existing_numbers)
        )

        processed = 0
        for n in range(1, latest + 1):
            if n in SKIP_NUMBERS or n in existing_numbers:
                continue
            comic = fetch_xkcd(n, client)
            article = fetch_explainxkcd(n, client)
            upsert_comic(table, comic, article)
            processed += 1
            if processed % 50 == 0:
                logger.info("Processed %s comics (current: %s)", processed, n)

    logger.info("Done: %s total chunks indexed", len(table))

    if repo_id:
        logger.info("Uploading to Hugging Face Dataset: %s...", repo_id)
        api = HfApi(token=token)
        api.create_repo(repo_id=repo_id, repo_type="dataset", exist_ok=True)
        upload_folder(
            repo_id=repo_id,
            folder_path=str(LANCE_DIR),
            repo_type="dataset",
            token=token,
        )
        logger.info("Upload complete!")
    return 0


if __name__ == "__main__":
    sys.exit(main())

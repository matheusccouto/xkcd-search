"""Build and update the LanceDB index from explainxkcd.com."""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import TYPE_CHECKING, Any

import httpx
import lancedb
import mwparserfromhell
import pyarrow as pa
from huggingface_hub import HfApi, InferenceClient, snapshot_download, upload_folder

from xkcd_search.retriever import EMBED_MODEL

if TYPE_CHECKING:
    from lancedb.table import Table
    from mwparserfromhell.wikicode import Wikicode

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)

LANCE_DIR = Path.home() / ".cache" / "xkcd-search" / "lancedb"
XKCD = "https://xkcd.com"
EXPLAIN = "https://www.explainxkcd.com/wiki/api.php"
MAX_TEXT_CHARS = 2000
SKIP_NUMBER = 404

SCHEMA = pa.schema(
    [
        ("number", pa.int32()),
        ("title", pa.string()),
        ("url", pa.string()),
        ("image_url", pa.string()),
        ("alt_text", pa.string()),
        ("transcript", pa.string()),
        ("explanation", pa.string()),
        ("vector", pa.list_(pa.float32(), 384)),
    ]
)


def new_client() -> httpx.Client:
    """HTTP client for xkcd sites."""
    return httpx.Client(timeout=30.0, follow_redirects=True)


def fetch_explainxkcd(number: int, client: httpx.Client) -> str:
    """Fetch explainxkcd article wikitext by number."""
    resp = client.get(
        EXPLAIN,
        params={
            "action": "parse",
            "page": str(number),
            "redirects": "1",
            "prop": "wikitext",
            "format": "json",
        },
    )
    return str(resp.json()["parse"]["wikitext"]["*"])


def latest_comic_number(client: httpx.Client) -> int:
    """Latest comic number, from the newest explainxkcd article."""
    resp = client.get(
        EXPLAIN,
        params={
            "action": "query",
            "list": "recentchanges",
            "rctype": "new",
            "rcnamespace": "0",
            "rclimit": "1",
            "format": "json",
        },
    )
    title = resp.json()["query"]["recentchanges"][0]["title"]
    return int(title.split(":")[0])


def parse_comic(number: int, wikitext: str) -> dict[str, Any]:
    """Extract comic metadata from explainxkcd wikitext."""
    parsed = mwparserfromhell.parse(wikitext)
    fields = {
        str(param.name).strip(): str(param.value).strip()
        for param in parsed.filter_templates()[0].params
    }
    return {
        "number": number,
        "title": fields["title"],
        "url": f"{XKCD}/{number}/",
        "image": fields["image"],
        "alt_text": fields["titletext"],
        "transcript": transcript_of(parsed),
        "explanation": str(parsed.strip_code()).strip(),
    }


def transcript_of(parsed: Wikicode) -> str:
    """Plain text of the Transcript section, or empty string."""
    for section in parsed.get_sections(flat=True, include_headings=True):
        headings = section.filter_headings()
        if headings and str(headings[0].title).strip().lower() == "transcript":
            section.remove(headings[0])
            return str(section.strip_code()).strip()
    return ""


def resolve_image(client: httpx.Client, filename: str) -> str:
    """Resolve an explainxkcd image filename to a full URL."""
    resp = client.get(
        EXPLAIN,
        params={
            "action": "query",
            "titles": f"File:{filename}",
            "prop": "imageinfo",
            "iiprop": "url",
            "format": "json",
        },
    )
    page = next(iter(resp.json()["query"]["pages"].values()))
    return page["imageinfo"][0]["url"]


def fetch_comic(client: httpx.Client, number: int) -> dict[str, Any]:
    """Fetch and parse a comic from explainxkcd, including its image URL."""
    comic = parse_comic(number, fetch_explainxkcd(number, client))
    comic["image_url"] = resolve_image(client, comic.pop("image"))
    return comic


def comic_text(comic: dict[str, Any]) -> str:
    """Searchable text: title, punchline, and explanation."""
    parts = [comic["title"], comic["alt_text"], comic["explanation"]]
    return "\n".join(p for p in parts if p.strip())[:MAX_TEXT_CHARS]


def encode(text: str) -> list[float]:
    """Embed text via Hugging Face Serverless Inference."""
    client = InferenceClient(token=os.getenv("HF_TOKEN"))
    return list(client.feature_extraction(text, model=EMBED_MODEL))


def open_or_create_table(path: Path | str) -> Table:
    """Open existing LanceDB table or create a new one with schema."""
    Path(path).mkdir(parents=True, exist_ok=True)
    db = lancedb.connect(str(path))
    if "comics" in db.list_tables().tables:
        return db.open_table("comics")
    return db.create_table("comics", schema=SCHEMA)


def upsert_comic(table: Table, comic: dict[str, Any]) -> None:
    """Embed and store a comic as a single searchable row."""
    table.delete(f"number = {comic['number']}")
    table.add([{**comic, "vector": encode(comic_text(comic))}])


def main() -> None:
    """Ingest all comics into LanceDB and publish to Hugging Face."""
    repo = os.environ.get("HF_DATASET_REPO")
    token = os.environ.get("HF_TOKEN")
    if repo and not (LANCE_DIR / "comics.lance").exists():
        api = HfApi(token=token)
        if api.repo_exists(repo_id=repo, repo_type="dataset"):
            logger.info("Restoring LanceDB dataset from %s...", repo)
            snapshot_download(
                repo_id=repo, repo_type="dataset", local_dir=str(LANCE_DIR), token=token
            )

    table = open_or_create_table(LANCE_DIR)
    with new_client() as client:
        latest = latest_comic_number(client)
        existing = set(table.to_arrow()["number"].to_pylist())
        for n in range(1, latest + 1):
            if n == SKIP_NUMBER or n in existing:
                continue
            upsert_comic(table, fetch_comic(client, n))
        logger.info("Indexed %s comics", len(table))

    if repo:
        api = HfApi(token=token)
        api.create_repo(repo_id=repo, repo_type="dataset", exist_ok=True)
        upload_folder(
            repo_id=repo, folder_path=str(LANCE_DIR), repo_type="dataset", token=token
        )
        logger.info("Uploaded to %s", repo)


if __name__ == "__main__":
    main()

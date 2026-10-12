"""Ingest explainxkcd comics into LanceDB and publish to Hugging Face."""

from __future__ import annotations

import logging
import os
from concurrent.futures import ThreadPoolExecutor

import click
from huggingface_hub import HfApi, upload_folder

from xkcd_search.index import SearchIndex
from xkcd_search.models import SKIP_NUMBER
from xkcd_search.scraper import ExplainXKCDScraper

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)


def ingest_missing_comics(
    search_index: SearchIndex,
    scraper: ExplainXKCDScraper,
    batch_size: int = 50,
) -> int:
    """Discover missing comics, scrape them, and index in batches into LanceDB."""
    existing: set[int] = set()
    if "comics" in search_index.db.list_tables().tables:
        existing = set(
            search_index.comics_table.search()
            .select(["number"])
            .to_arrow()["number"]
            .to_pylist()
        )

    latest = scraper.fetch_latest_number()
    missing = [
        n for n in range(1, latest + 1) if n != SKIP_NUMBER and n not in existing
    ]

    logger.info("Found %d missing comics out of %d total", len(missing), latest)
    if not missing:
        return 0

    total_indexed = 0
    with ThreadPoolExecutor(max_workers=8) as executor:
        for i in range(0, len(missing), batch_size):
            batch = missing[i : i + batch_size]
            comics = list(executor.map(scraper.fetch_comic, batch))
            search_index.index(comics)
            total_indexed += len(comics)
            logger.info("Indexed %d/%d missing comics", total_indexed, len(missing))

    return total_indexed


@click.command()
def main() -> None:
    """Ingest missing comics into LanceDB and publish to Hugging Face."""
    search_index = SearchIndex()
    with ExplainXKCDScraper() as scraper:
        ingest_missing_comics(search_index, scraper)

    repo = os.environ.get("HF_DATASET_REPO")
    if repo:
        if search_index.uri.startswith("hf://"):
            logger.info("Dataset URI %s is remote, skipping upload", search_index.uri)
            return
        token = os.environ.get("HF_TOKEN")
        api = HfApi(token=token)
        api.create_repo(repo_id=repo, repo_type="dataset", exist_ok=True)
        upload_folder(
            repo_id=repo,
            folder_path=search_index.uri,
            repo_type="dataset",
            token=token,
        )
        logger.info("Uploaded LanceDB index to %s", repo)


if __name__ == "__main__":
    main()

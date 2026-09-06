"""Utilities to sample random comics from explainxkcd and populate the eval corpus."""

from __future__ import annotations

import argparse
import logging
import re
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any

from xkcd_search.ingest import (
    fetch_explainxkcd,
    fetch_xkcd,
    new_client,
    open_or_create_table,
    upsert_comic,
)

if TYPE_CHECKING:
    import httpx
    from lancedb.table import Table

logger = logging.getLogger(__name__)

RANDOM_EXPLANATION_URL = "https://www.explainxkcd.com/random-explanation"
DEFAULT_EVAL_LANCE_DIR = Path(__file__).resolve().parent / "data" / "lance"


def fetch_random_comic(client: httpx.Client) -> tuple[int, dict[str, Any], str]:
    """Fetch a random comic and explanation by following explainxkcd redirect."""
    resp = client.get(RANDOM_EXPLANATION_URL)
    match = re.search(r"/wiki/index\.php/(\d+):", str(resp.url))
    if not match:
        msg = f"Failed to parse comic number from redirect URL: {resp.url}"
        raise ValueError(msg)
    comic_number = int(match.group(1))
    comic = fetch_xkcd(comic_number, client)
    article = fetch_explainxkcd(comic_number, client)
    return comic_number, comic, article


def ensure_eval_corpus(
    lance_path: Path | str = DEFAULT_EVAL_LANCE_DIR,
    comic_numbers: list[int] | None = None,
) -> Table:
    """Ensure LanceDB table exists and contains all requested evaluation comics."""
    target_numbers = set(comic_numbers or [])
    table = open_or_create_table(lance_path)

    existing_numbers = (
        set(table.to_arrow()["number"].to_pylist()) if len(table) > 0 else set()
    )
    missing = [num for num in target_numbers if num not in existing_numbers]

    if not missing:
        return table

    logger.info(
        "Indexing %s missing evaluation comics into %s...", len(missing), lance_path
    )
    with new_client() as client:
        for num in missing:
            comic = fetch_xkcd(num, client)
            article = fetch_explainxkcd(num, client)
            upsert_comic(table, comic, article)

    return table


def main() -> int:
    """CLI to sample random comics from explainxkcd."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    parser = argparse.ArgumentParser(
        description="Sample random comics from explainxkcd"
    )
    parser.add_argument(
        "--count", type=int, default=3, help="Number of random comics to sample"
    )
    parser.add_argument(
        "--index",
        action="store_true",
        help="Also index sampled comics into the evaluation LanceDB directory",
    )
    args = parser.parse_args()

    table = open_or_create_table(DEFAULT_EVAL_LANCE_DIR) if args.index else None
    logger.info(
        "Sampling %s random comics from %s...", args.count, RANDOM_EXPLANATION_URL
    )

    with new_client() as client:
        for idx in range(args.count):
            num, comic, article = fetch_random_comic(client)
            print(f"\n[{idx + 1}/{args.count}] #{num}: {comic['title']}")
            print(f"URL: {comic['url']}")
            print(f"Alt text: {comic['alt_text']}")
            print(f"Article length: {len(article)} chars")
            if table is not None:
                upsert_comic(table, comic, article)
                print(f"Indexed comic #{num} into {DEFAULT_EVAL_LANCE_DIR}")

    return 0


if __name__ == "__main__":
    sys.exit(main())

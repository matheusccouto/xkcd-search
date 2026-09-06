"""Sample random comics from explainxkcd to create new entries in evals/dataset.json."""

from __future__ import annotations

import argparse
import json
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

RANDOM_URL = "https://www.explainxkcd.com/random-explanation"
EVAL_LANCE_DIR = Path(__file__).resolve().parent / "data" / "lance"


def sample_random_comic(client: httpx.Client) -> dict[str, Any]:
    """Follow explainxkcd random redirect and fetch comic data."""
    resp = client.get(RANDOM_URL)
    match = re.search(r"/wiki/index\.php/(\d+):", str(resp.url))
    if not match:
        msg = f"Could not parse comic number from redirect URL: {resp.url}"
        raise ValueError(msg)
    num = int(match.group(1))
    comic = fetch_xkcd(num, client)
    article = fetch_explainxkcd(num, client)
    return {
        "comic_number": num,
        "title": comic["title"],
        "alt_text": comic["alt_text"],
        "comic": comic,
        "article": article,
    }


def main() -> int:
    """CLI to discover comics and generate dataset.json templates."""
    parser = argparse.ArgumentParser(
        description="Discover random explainxkcd pages to add to evals/dataset.json"
    )
    parser.add_argument(
        "--count", type=int, default=1, help="Number of random comics to sample"
    )
    parser.add_argument(
        "--index",
        action="store_true",
        help="Also index sampled comic into local evaluation database",
    )
    args = parser.parse_args()

    table = open_or_create_table(EVAL_LANCE_DIR) if args.index else None

    with new_client() as client:
        for i in range(args.count):
            item = sample_random_comic(client)
            num = item["comic_number"]
            title = item["title"]

            print(f"\n[{i + 1}/{args.count}] #{num} - {title}")
            print(f"Alt text: {item['alt_text']}")
            print("\nPaste this template into evals/dataset.json:")
            template = {
                "comic_number": num,
                "title": title,
                "queries": [
                    "add realistic user query 1",
                    "add realistic user query 2",
                ],
            }
            print(json.dumps(template, indent=2))

            if table is not None:
                upsert_comic(table, item["comic"], item["article"])
                print(f"Indexed #{num} into {EVAL_LANCE_DIR}")

    return 0


if __name__ == "__main__":
    sys.exit(main())

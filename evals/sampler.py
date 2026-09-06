"""Sample random comics from LanceDB to create new entries in evals/dataset.json."""

from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path
from typing import Any

from evals.test_retrieval import ensure_eval_corpus

DATASET_PATH = Path(__file__).resolve().parent / "dataset.json"


def sample_from_lancedb(count: int = 1) -> list[dict[str, Any]]:
    """Sample random comics directly from the LanceDB table."""
    table = ensure_eval_corpus()
    arrow_tbl = table.to_arrow()

    seen: set[int] = set()
    comics: list[dict[str, Any]] = []
    for num, title, alt in zip(
        arrow_tbl["number"].to_pylist(),
        arrow_tbl["title"].to_pylist(),
        arrow_tbl["alt_text"].to_pylist(),
        strict=False,
    ):
        if num not in seen:
            seen.add(num)
            comics.append({"comic_number": num, "title": title, "alt_text": alt})

    if not comics:
        return []

    # Prefer sampling comics not yet in dataset.json
    if DATASET_PATH.exists():
        existing = {
            c["comic_number"]
            for c in json.loads(DATASET_PATH.read_text(encoding="utf-8"))
        }
        candidates = [c for c in comics if c["comic_number"] not in existing]
        pool = candidates or comics
    else:
        pool = comics

    sample_size = min(count, len(pool))
    return random.sample(pool, sample_size)


def main() -> int:
    """CLI to sample comics from LanceDB and print dataset.json templates."""
    parser = argparse.ArgumentParser(
        description="Sample random comics from LanceDB to add to evals/dataset.json"
    )
    parser.add_argument(
        "--count", type=int, default=1, help="Number of random comics to sample"
    )
    args = parser.parse_args()

    sampled = sample_from_lancedb(count=args.count)
    if not sampled:
        print("No comics found in LanceDB table.")
        return 1

    for i, item in enumerate(sampled):
        num = item["comic_number"]
        title = item["title"]

        print(f"\n[{i + 1}/{len(sampled)}] #{num} - {title}")
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

    return 0


if __name__ == "__main__":
    sys.exit(main())

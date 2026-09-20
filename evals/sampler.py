"""Sample random comics from LanceDB to template new entries in dataset.json."""

from __future__ import annotations

import argparse
import json
import random

from xkcd_search.retriever import XKCDRetriever


def sample_comics(count: int = 3) -> list[dict[str, int | str]]:
    """Sample random comics from LanceDB as template dataset entries."""
    retriever = XKCDRetriever()
    table = retriever.table
    numbers = table.search().select(["number"]).to_arrow()["number"].to_pylist()
    chosen_numbers = random.sample(numbers, min(count, len(numbers)))

    samples: list[dict[str, int | str]] = []
    for num in chosen_numbers:
        rows = table.search().where(f"number = {num}").limit(1).to_list()
        if rows:
            row = rows[0]
            samples.append(
                {
                    "number": int(row["number"]),
                    "title": str(row.get("title", "")),
                    "query": "",
                }
            )
    return samples


def main() -> None:
    """CLI entrypoint for sampler."""
    parser = argparse.ArgumentParser(description="Sample comics from LanceDB")
    parser.add_argument(
        "--count", type=int, default=3, help="Number of comics to sample"
    )
    args = parser.parse_args()

    results = sample_comics(count=args.count)
    print(json.dumps(results, indent=2))  # noqa: T201


if __name__ == "__main__":
    main()

"""Sample random comics from explainxkcd to template new entries in dataset.json."""

from __future__ import annotations

import argparse
import json

import httpx

EXPLAIN_API = "https://www.explainxkcd.com/wiki/api.php"


def sample_comics(count: int = 3) -> list[dict[str, int | str]]:
    """Sample random comics directly from explainxkcd."""
    samples: list[dict[str, int | str]] = []
    seen: set[int] = set()

    with httpx.Client(timeout=30.0) as client:
        while len(samples) < count:
            resp = client.get(
                EXPLAIN_API,
                params={
                    "action": "query",
                    "list": "random",
                    "rnnamespace": "0",
                    "rnfilterredir": "nonredirects",
                    "rnlimit": min(max(count - len(samples), 1), 500),
                    "format": "json",
                },
            )
            resp.raise_for_status()
            for page in resp.json()["query"]["random"]:
                parts = page["title"].split(": ", 1)
                if len(parts) == 2 and parts[0].isdigit():
                    num = int(parts[0])
                    if num != 404 and num not in seen:
                        seen.add(num)
                        samples.append({"number": num, "title": parts[1], "query": ""})
                        if len(samples) == count:
                            break

    return samples


def main() -> None:
    """CLI entrypoint for sampler."""
    parser = argparse.ArgumentParser(
        description="Sample random comics from explainxkcd",
    )
    parser.add_argument(
        "--count",
        type=int,
        default=3,
        help="Number of comics to sample",
    )
    args = parser.parse_args()

    results = sample_comics(count=args.count)
    print(json.dumps(results, indent=2))  # noqa: T201


if __name__ == "__main__":
    main()

"""Integration tests for the ingestion pipeline without mocks."""

from __future__ import annotations

from typing import TYPE_CHECKING

import httpx
import pytest

from xkcd_search.index import SearchIndex
from xkcd_search.ingest import ingest_missing_comics
from xkcd_search.models import Comic
from xkcd_search.scraper import ExplainXKCDScraper

if TYPE_CHECKING:
    from pathlib import Path

    from tests.conftest import DeterministicTestEmbedder

SAMPLE_WIKITEXT_1 = """{{comic
| number = 1
| title = First Comic
| image = first.png
| titletext = Alt One
}}
== Explanation ==
First explanation text.

== Transcript ==
First transcript text.
"""

SAMPLE_WIKITEXT_2 = """{{comic
| number = 2
| title = Second Comic
| image = second.png
| titletext = Alt Two
}}
== Explanation ==
Second explanation text.

== Transcript ==
Second transcript text.
"""


class IngestFixtureTransport(httpx.BaseTransport):
    """Sync fixture transport simulating explainxkcd API for ingestion."""

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        """Handle explainxkcd API requests."""
        action = request.url.params.get("action")
        if action == "query" and "list" in request.url.params:
            return httpx.Response(
                200, json={"query": {"recentchanges": [{"title": "2: Second"}]}}
            )
        if action == "query" and "titles" in request.url.params:
            return httpx.Response(
                200,
                json={
                    "query": {
                        "pages": {
                            "1": {
                                "imageinfo": [
                                    {"url": "https://imgs.xkcd.com/comics/img.png"}
                                ]
                            }
                        }
                    }
                },
            )
        if action == "parse":
            page = request.url.params.get("page")
            if page == "1":
                return httpx.Response(
                    200, json={"parse": {"wikitext": {"*": SAMPLE_WIKITEXT_1}}}
                )
            if page == "2":
                return httpx.Response(
                    200, json={"parse": {"wikitext": {"*": SAMPLE_WIKITEXT_2}}}
                )
        return httpx.Response(404, json={})


@pytest.fixture
def ingest_scraper() -> ExplainXKCDScraper:
    """Fixture scraper wired to simulated explainxkcd API returning 2 comics."""
    client = httpx.Client(transport=IngestFixtureTransport())
    return ExplainXKCDScraper(client=client)


def test_ingest_missing_comics_end_to_end(
    tmp_path: Path,
    deterministic_embedder: DeterministicTestEmbedder,
    ingest_scraper: ExplainXKCDScraper,
) -> None:
    """Verify ingestion pipeline discovers and indexes missing comics into LanceDB."""
    test_index = SearchIndex(
        uri=tmp_path / "lancedb",
        embedder=deterministic_embedder,
    )

    indexed = ingest_missing_comics(test_index, ingest_scraper, batch_size=2)
    assert indexed == 2
    assert len(test_index.comics_table) == 2
    assert len(test_index.chunks_table) >= 2

    # Running again should detect that all comics are already indexed
    subsequent = ingest_missing_comics(test_index, ingest_scraper)
    assert subsequent == 0


def test_ingest_skips_comic_404(
    tmp_path: Path,
    deterministic_embedder: DeterministicTestEmbedder,
) -> None:
    """Verify comic 404 is never fetched during ingestion."""
    fetched_numbers: list[int] = []

    class SkipTransport(httpx.BaseTransport):
        def handle_request(self, request: httpx.Request) -> httpx.Response:
            action = request.url.params.get("action")
            if action == "query" and "list" in request.url.params:
                return httpx.Response(
                    200, json={"query": {"recentchanges": [{"title": "405: Late"}]}}
                )
            if action == "query" and "titles" in request.url.params:
                return httpx.Response(
                    200,
                    json={
                        "query": {
                            "pages": {
                                "1": {
                                    "imageinfo": [
                                        {"url": "https://imgs.xkcd.com/comics/img.png"}
                                    ]
                                }
                            }
                        }
                    },
                )
            if action == "parse":
                page = int(request.url.params["page"])
                fetched_numbers.append(page)
                return httpx.Response(
                    200, json={"parse": {"wikitext": {"*": SAMPLE_WIKITEXT_1}}}
                )
            return httpx.Response(404, json={})

    client = httpx.Client(transport=SkipTransport())
    scraper = ExplainXKCDScraper(client=client)

    test_index = SearchIndex(
        uri=tmp_path / "lancedb",
        embedder=deterministic_embedder,
    )
    # Pre-seed existing with all up to 403 and 405
    # so only 404 would be in range if not filtered
    test_index.index(
        [
            Comic(
                number=n,
                title=f"Comic {n}",
                url=f"https://xkcd.com/{n}/",
                image_url="https://example.com/img.png",
                alt_text="",
                transcript="",
                explanation="",
            )
            for n in range(1, 404)
        ]
        + [
            Comic(
                number=405,
                title="Comic 405",
                url="https://xkcd.com/405/",
                image_url="https://example.com/img.png",
                alt_text="",
                transcript="",
                explanation="",
            )
        ]
    )

    indexed = ingest_missing_comics(test_index, scraper)
    assert indexed == 0
    assert 404 not in fetched_numbers

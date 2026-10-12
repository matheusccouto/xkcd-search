"""Tests for ExplainXKCDScraper public interface using fixture transport."""

from __future__ import annotations

import httpx
import pytest

from xkcd_search.models import Comic
from xkcd_search.scraper import ExplainXKCDScraper, ScraperError, parse_comic_wikitext

SAMPLE_WIKITEXT = """{{comic
| number = 1
| title = Barrel - Part 1
| image = barrel_cropped_(1).jpg
| titletext = Don't we all.
}}
== Explanation ==
A boy is sitting in a barrel.

== Transcript ==
[[A boy sits in a barrel floating in water.]]
"""

SAMPLE_WIKITEXT_CASE_INSENSITIVE = """{{comic
| number = 2
| title = Petit Trees
| image = tree.png
| titletext = Some alt text
}}
== explanation ==
A comic about trees.

== transcript ==
[[A tiny tree is planted.]]
"""


class MediaWikiFixtureTransport(httpx.BaseTransport):
    """Sync fixture transport simulating explainxkcd API."""

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        """Handle simulated MediaWiki API requests."""
        action = request.url.params.get("action")
        if action == "parse":
            page = request.url.params.get("page")
            if page == "1":
                return httpx.Response(
                    200, json={"parse": {"wikitext": {"*": SAMPLE_WIKITEXT}}}
                )
            if page == "2":
                return httpx.Response(
                    200,
                    json={
                        "parse": {"wikitext": {"*": SAMPLE_WIKITEXT_CASE_INSENSITIVE}}
                    },
                )
            return httpx.Response(200, json={"error": {"code": "missingtitle"}})

        if action == "query":
            if "titles" in request.url.params:
                return httpx.Response(
                    200,
                    json={
                        "query": {
                            "pages": {
                                "1": {
                                    "imageinfo": [
                                        {
                                            "url": "https://imgs.xkcd.com/comics/barrel.jpg"
                                        }
                                    ]
                                }
                            }
                        }
                    },
                )
            if "list" in request.url.params:
                return httpx.Response(
                    200,
                    json={"query": {"recentchanges": [{"title": "2: Petit Trees"}]}},
                )

        return httpx.Response(404, json={})


@pytest.fixture
def scraper() -> ExplainXKCDScraper:
    """Fixture scraper wired to simulated MediaWiki API via sync fixture transport."""
    client = httpx.Client(transport=MediaWikiFixtureTransport())
    return ExplainXKCDScraper(client=client)


def test_fetch_comic(scraper: ExplainXKCDScraper) -> None:
    """Verify fetch_comic successfully extracts attributes into Comic domain entity."""
    comic = scraper.fetch_comic(1)
    assert isinstance(comic, Comic)
    assert comic.number == 1
    assert comic.title == "Barrel - Part 1"
    assert comic.url == "https://xkcd.com/1/"
    assert comic.image_url == "https://imgs.xkcd.com/comics/barrel.jpg"
    assert comic.alt_text == "Don't we all."
    assert comic.transcript == "A boy sits in a barrel floating in water."
    assert "A boy is sitting in a barrel." in comic.explanation


def test_fetch_comic_case_insensitive_transcript(scraper: ExplainXKCDScraper) -> None:
    """Verify fetch_comic parses case-insensitive transcript section."""
    comic = scraper.fetch_comic(2)
    assert comic.transcript == "A tiny tree is planted."


def test_fetch_comic_404_raises() -> None:
    """Verify comic 404 raises ScraperError immediately without network requests."""
    scraper = ExplainXKCDScraper()
    with pytest.raises(ScraperError, match="404"):
        scraper.fetch_comic(404)


def test_fetch_comic_missing_page_raises(scraper: ExplainXKCDScraper) -> None:
    """Verify fetching a non-existent comic article raises ScraperError."""
    with pytest.raises(ScraperError, match="article not found"):
        scraper.fetch_comic(999)


def test_fetch_latest_number(scraper: ExplainXKCDScraper) -> None:
    """Verify fetch_latest_number returns the most recent comic number."""
    assert scraper.fetch_latest_number() == 2


def test_scraper_context_manager(scraper: ExplainXKCDScraper) -> None:
    """Verify scraper functions correctly as a context manager."""
    with scraper as s:
        comic = s.fetch_comic(1)
        assert comic.number == 1


def test_parse_comic_wikitext_strips_inline_comments() -> None:
    """Verify parse_comic_wikitext cleans HTML comments from template fields."""
    wikitext = """{{comic
| number = 1608
| title = Hoverboard <!--comment-->
| image = hoverboard.png <!--another comment-->
| titletext = Some text
}}
== Explanation ==
Hoverboard explanation.
"""
    parsed = parse_comic_wikitext(1608, wikitext)
    assert parsed.title == "Hoverboard"
    assert parsed.image_filename == "hoverboard.png"


def test_parse_comic_wikitext_custom_field() -> None:
    """Verify parse_comic_wikitext extracts image from custom parameter."""
    wikitext = """{{comic
| number = 1331
| title = Frequency
| custom = <table><tr><td>[[File:heartbeat.gif]]</td></tr></table>
| titletext = Some text
}}
== Explanation ==
Frequency explanation.
"""
    parsed = parse_comic_wikitext(1331, wikitext)
    assert parsed.title == "Frequency"
    assert parsed.image_filename == "heartbeat.gif"

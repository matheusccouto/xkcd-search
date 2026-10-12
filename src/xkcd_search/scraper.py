"""Web scraper for explainxkcd MediaWiki API and wikitext parser."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Self

import httpx
import mwparserfromhell

from xkcd_search.models import SKIP_NUMBER, Comic

if TYPE_CHECKING:
    from types import TracebackType

EXPLAIN_API = "https://www.explainxkcd.com/wiki/api.php"
XKCD_BASE = "https://xkcd.com"


class ScraperError(ValueError):
    """Raised when comic scraping or parsing fails."""


@dataclass(frozen=True, slots=True)
class ParsedWikitext:
    """Structured attributes extracted from comic wikitext."""

    title: str
    image_filename: str
    alt_text: str
    transcript: str
    explanation: str


def parse_comic_wikitext(number: int, wikitext: str) -> ParsedWikitext:
    """Parse raw explainxkcd wikitext into comic attributes."""
    parsed = mwparserfromhell.parse(wikitext)
    templates = [
        t for t in parsed.filter_templates() if str(t.name).strip().lower() == "comic"
    ]
    if not templates:
        msg = f"Comic {number} is missing comic template"
        raise ScraperError(msg)

    template = templates[0]
    fields = {
        str(p.name).strip(): str(p.value.strip_code()).strip() for p in template.params
    }
    title = fields.get("title")
    image = fields.get("image")
    if not image and "custom" in fields:
        for param in template.params:
            if str(param.name).strip() == "custom":
                custom_parsed = mwparserfromhell.parse(str(param.value))
                file_links = [
                    w
                    for w in custom_parsed.filter_wikilinks()
                    if str(w.title).lower().startswith("file:")
                ]
                if file_links:
                    image = str(file_links[0].title).split(":", maxsplit=1)[1].strip()
                break
    alt_text = fields.get("titletext", "")

    if not title or not image:
        msg = f"Comic {number} is missing required title or image"
        raise ScraperError(msg)

    transcript = ""
    for section in parsed.get_sections(flat=True, include_headings=True):
        headings = section.filter_headings()
        if headings and str(headings[0].title).strip().lower() == "transcript":
            section.remove(headings[0])
            transcript = str(section.strip_code()).strip()
            break

    explanation = str(parsed.strip_code()).strip()

    return ParsedWikitext(
        title=title,
        image_filename=image,
        alt_text=alt_text,
        transcript=transcript,
        explanation=explanation,
    )


class ExplainXKCDScraper:
    """Scrapes comic data and image URLs from explainxkcd."""

    def __init__(
        self,
        client: httpx.Client | None = None,
        endpoint: str = EXPLAIN_API,
    ) -> None:
        """Initialize scraper with optional HTTP client and API endpoint."""
        self.endpoint = endpoint
        self._owned_client = client is None
        self.client = client or httpx.Client(timeout=30.0, follow_redirects=True)

    def __enter__(self) -> Self:
        """Enter context manager."""
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        """Exit context manager and close client if owned."""
        self.close()

    def close(self) -> None:
        """Close the underlying HTTP client if owned."""
        if self._owned_client:
            self.client.close()

    def fetch_latest_number(self) -> int:
        """Fetch the latest comic number from explainxkcd recent changes."""
        resp = self.client.get(
            self.endpoint,
            params={
                "action": "query",
                "list": "recentchanges",
                "rctype": "new",
                "rcnamespace": "0",
                "rclimit": "1",
                "format": "json",
            },
        )
        resp.raise_for_status()
        data: dict[str, Any] = resp.json()
        changes = data.get("query", {}).get("recentchanges", [])
        if not changes:
            msg = "Failed to retrieve recent changes from explainxkcd"
            raise ScraperError(msg)
        title: str = changes[0]["title"]
        return int(title.split(":", maxsplit=1)[0].strip())

    def resolve_image_url(self, image_filename: str) -> str:
        """Resolve an explainxkcd image filename to a canonical URL."""
        resp = self.client.get(
            self.endpoint,
            params={
                "action": "query",
                "titles": f"File:{image_filename}",
                "prop": "imageinfo",
                "iiprop": "url",
                "format": "json",
            },
        )
        resp.raise_for_status()
        pages = resp.json().get("query", {}).get("pages", {})
        for page in pages.values():
            if page.get("imageinfo"):
                return str(page["imageinfo"][0]["url"])

        msg = f"Could not resolve image URL for File:{image_filename}"
        raise ScraperError(msg)

    def fetch_comic(self, number: int) -> Comic:
        """Fetch and parse a comic by number into a Comic domain model."""
        if number == SKIP_NUMBER:
            msg = f"Comic {SKIP_NUMBER} does not exist"
            raise ScraperError(msg)

        resp = self.client.get(
            self.endpoint,
            params={
                "action": "parse",
                "page": str(number),
                "redirects": "1",
                "prop": "wikitext",
                "format": "json",
            },
        )
        resp.raise_for_status()
        data = resp.json()
        if "parse" not in data or "wikitext" not in data["parse"]:
            msg = f"Failed to fetch comic {number}: article not found"
            raise ScraperError(msg)

        wikitext = str(data["parse"]["wikitext"]["*"])
        parsed = parse_comic_wikitext(number, wikitext)
        image_url = self.resolve_image_url(parsed.image_filename)

        return Comic(
            number=number,
            title=parsed.title,
            url=f"{XKCD_BASE}/{number}/",
            image_url=image_url,
            alt_text=parsed.alt_text,
            transcript=parsed.transcript,
            explanation=parsed.explanation,
        )

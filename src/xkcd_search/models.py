"""Domain entities for xkcd comics and searchable chunks."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class Comic:
    """Immutable domain model for an xkcd comic."""

    number: int
    title: str
    url: str
    image_url: str
    alt_text: str
    transcript: str
    explanation: str
    score: float | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any], score: float | None = None) -> Comic:
        """Construct Comic from dict record with optional similarity score."""
        return cls(
            number=int(data["number"]),
            title=str(data["title"]),
            url=str(data["url"]),
            image_url=str(data["image_url"]),
            alt_text=str(data["alt_text"]),
            transcript=str(data["transcript"]),
            explanation=str(data["explanation"]),
            score=score,
        )

    def to_dict(self) -> dict[str, Any]:
        """Return dict representation omitting score for schema compatibility."""
        return {
            "number": self.number,
            "title": self.title,
            "url": self.url,
            "image_url": self.image_url,
            "alt_text": self.alt_text,
            "transcript": self.transcript,
            "explanation": self.explanation,
        }


@dataclass(frozen=True, slots=True)
class Chunk:
    """Searchable text fragment linked to a comic."""

    comic_number: int
    text: str
    kind: str = "window"
    vector: list[float] | None = None


SKIP_NUMBER = 404

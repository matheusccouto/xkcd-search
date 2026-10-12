"""Chunking strategies for decomposing comics into searchable fragments."""

from __future__ import annotations

from typing import Protocol

from xkcd_search.models import Chunk, Comic


class ChunkerError(ValueError):
    """Raised when chunking parameters are invalid."""


class Chunker(Protocol):
    """Protocol for chunking strategies."""

    def chunk(self, comic: Comic) -> list[Chunk]:
        """Decompose a comic into searchable chunks."""
        ...


class FixedWindowChunker:
    """Chunks comic text into fixed-size overlapping character windows."""

    def __init__(self, chunk_size: int = 400, overlap: int = 80) -> None:
        """Initialize chunker with window size and overlap."""
        if overlap < 0 or overlap >= chunk_size:
            msg = "overlap must be non-negative and less than chunk_size"
            raise ChunkerError(msg)
        self.chunk_size = chunk_size
        self.overlap = overlap

    def chunk(self, comic: Comic) -> list[Chunk]:
        """Decompose comic into character window chunks."""
        parts = [comic.title, comic.alt_text, comic.explanation, comic.transcript]
        full_text = "\n\n".join(p.strip() for p in parts if p.strip())
        if not full_text:
            return []

        chunks: list[Chunk] = []
        step = self.chunk_size - self.overlap
        start = 0
        while start < len(full_text):
            end = start + self.chunk_size
            window = full_text[start:end]
            chunks.append(
                Chunk(
                    comic_number=comic.number,
                    text=window,
                    kind="window",
                )
            )
            if end >= len(full_text):
                break
            start += step

        return chunks

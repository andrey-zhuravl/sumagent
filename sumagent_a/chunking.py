from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Chunk:
    index: int
    total: int
    text: str


def chunk_text(
    text: str,
    *,
    max_chunk_chars: int,
    overlap_chars: int,
    max_chunks: int,
) -> list[Chunk]:
    if max_chunk_chars <= 0:
        raise ValueError("max_chunk_chars must be positive")
    if overlap_chars < 0:
        raise ValueError("overlap_chars must be non-negative")
    if max_chunks <= 0:
        raise ValueError("max_chunks must be positive")

    chunks: list[Chunk] = []
    start = 0
    text_len = len(text)
    while start < text_len and len(chunks) < max_chunks:
        end = min(start + max_chunk_chars, text_len)
        chunk_text_value = text[start:end]
        chunks.append(Chunk(index=len(chunks) + 1, total=0, text=chunk_text_value))
        if end >= text_len:
            break
        start = end - overlap_chars
        if start < 0:
            start = 0

    total = len(chunks)
    return [Chunk(index=chunk.index, total=total, text=chunk.text) for chunk in chunks]

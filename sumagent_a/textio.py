from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


FALLBACK_ENCODINGS = ("utf-8", "utf-8-sig", "cp1251", "latin-1")


@dataclass(frozen=True)
class TextReadResult:
    text: str
    encoding: str


def is_binary_bytes(data: bytes, null_byte_threshold: int, non_printable_ratio: float) -> bool:
    if not data:
        return False
    null_count = data.count(0)
    if null_count >= null_byte_threshold:
        return True
    printable = sum(1 for b in data if 9 <= b <= 13 or 32 <= b <= 126)
    ratio = 1 - (printable / len(data))
    return ratio >= non_printable_ratio


def decode_bytes(data: bytes, encodings: tuple[str, ...] = FALLBACK_ENCODINGS) -> TextReadResult | None:
    for encoding in encodings:
        try:
            return TextReadResult(text=data.decode(encoding), encoding=encoding)
        except UnicodeDecodeError:
            continue
    return None


def read_text(path: Path) -> TextReadResult | None:
    data = path.read_bytes()
    return decode_bytes(data)


def read_head_tail(path: Path, head_tail_bytes: int) -> TextReadResult | None:
    data = path.read_bytes()
    if len(data) <= head_tail_bytes * 2:
        return decode_bytes(data)
    head = data[:head_tail_bytes]
    tail = data[-head_tail_bytes:]
    combined = head + b"\n...\n" + tail
    return decode_bytes(combined)

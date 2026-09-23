from __future__ import annotations

import re


def chunk_text(text: str, size: int = 1000, overlap: int = 150) -> list[str]:
    cleaned = re.sub(r"[ \t]+", " ", text)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned).strip()
    if not cleaned:
        return []

    chunks: list[str] = []
    start = 0
    length = len(cleaned)
    while start < length:
        end = min(length, start + size)
        if end < length:
            cut = cleaned.rfind(" ", start, end)
            if cut > start + size // 4:
                end = cut
        piece = cleaned[start:end].strip()
        if piece:
            chunks.append(piece)
        nxt = end - overlap if end < length else end
        start = max(nxt, start + 1)
    return chunks

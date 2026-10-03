from __future__ import annotations

import re
from collections import Counter
from pathlib import Path
from typing import Any

from app.services.parsers import parse_file

STOPWORDS = {
    "the", "and", "for", "with", "that", "this", "from", "are", "was", "were", "have",
    "has", "not", "but", "you", "your", "their", "they", "will", "shall", "into", "onto",
    "about", "after", "before", "over", "under", "than", "then", "also", "such", "each",
    "more", "most", "other", "only", "just", "can", "may", "per", "via", "all", "any",
    "page", "pages", "document", "file", "sheet", "slide", "table", "figure",
    "de", "la", "el", "los", "las", "un", "una", "unos", "unas", "del", "al", "se", "por",
    "con", "para", "que", "como", "mas", "más", "este", "esta", "estos", "estas", "eso",
    "entre", "sobre", "sin", "sus", "son", "ser", "fue", "han", "hay", "muy",
}

SENTENCE_RE = re.compile(r"(?<=[.!?])\s+")
TOKEN_RE = re.compile(r"[a-zA-ZáéíóúñÁÉÍÓÚÑ][a-zA-ZáéíóúñÁÉÍÓÚÑ0-9]{2,}")


def read_document(path: Path, pages: int = 2, model: str | None = None) -> dict[str, Any]:
    parsed = parse_file(Path(path), max_pages=max(1, pages))
    page_texts = list(parsed.get("page_texts") or [])
    if not page_texts:
        page_texts = _split_pages(parsed.get("text") or "", int(parsed.get("pages") or 1))
    used = page_texts[: max(1, pages)]
    excerpt = "\n\n".join(item for item in used if item).strip()
    card = _llm_card(excerpt, Path(path).name, model=model)
    summary = str(card.get("summary") or "").strip() or summarize(excerpt)
    raw_keywords = card.get("keywords") if isinstance(card.get("keywords"), list) else []
    cleaned = [str(item).strip() for item in raw_keywords if str(item).strip()]
    return {
        "text": excerpt,
        "full_text": parsed.get("text") or excerpt,
        "pages": int(parsed.get("pages") or len(page_texts) or 0),
        "read_pages": len(used),
        "kind": parsed.get("kind") or "unknown",
        "ocr_used": bool(parsed.get("ocr_used")),
        "tables": parsed.get("tables") or [],
        "error": parsed.get("error") or "",
        "summary": summary[:420],
        "keywords": (cleaned or keywords(excerpt))[:8],
    }


def _llm_card(text: str, filename: str, model: str | None = None) -> dict[str, Any]:
    if not text.strip():
        return {}
    from app.services.llm import complete_json

    return complete_json(
        (
            f"Document {filename}. Write a factual summary (max 60 words) and 5-8 keywords "
            "from the meaning of the text, not just the most frequent tokens. "
            'Return JSON {"summary":"...","keywords":["..."]}.\n\n'
            f"{text[:4000]}"
        ),
        model=model,
    )


def summarize(text: str, limit: int = 420) -> str:
    clean = re.sub(r"\s+", " ", (text or "")).strip()
    if not clean:
        return ""
    parts = [part.strip() for part in SENTENCE_RE.split(clean) if part.strip()]
    if not parts:
        return clean[:limit]
    chosen: list[str] = []
    for part in parts[:4]:
        chosen.append(part)
        joined = " ".join(chosen)
        if len(joined) >= 180:
            return joined[:limit].rstrip() + ("…" if len(joined) > limit else "")
    joined = " ".join(chosen)
    return joined[:limit].rstrip() + ("…" if len(joined) > limit else "")


def keywords(text: str, limit: int = 8) -> list[str]:
    counts = Counter()
    for token in TOKEN_RE.findall(text or ""):
        word = token.lower()
        if word in STOPWORDS or word.isdigit():
            continue
        counts[word] += 1
    return [word for word, _ in counts.most_common(limit)]


def _split_pages(text: str, pages: int) -> list[str]:
    if not text:
        return []
    if "\f" in text:
        return [part.strip() for part in text.split("\f") if part.strip()]
    if pages <= 1:
        return [text]
    size = max(600, len(text) // max(pages, 1))
    return [text[index : index + size] for index in range(0, len(text), size)]

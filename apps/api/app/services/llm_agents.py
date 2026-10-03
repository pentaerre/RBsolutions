from typing import Any

from app.config import settings
from app.services.taxonomy import is_taxonomist

# Chat / JSON completion. Not embeddings, not OCR, not routing.
LLM_AGENT_SLUGS = frozenset(
    {
        "librarian",
        "reader",
        "extractor",
        "triage",
        "graphsmith",
    }
)


def agent_uses_llm(slug: str) -> bool:
    if is_taxonomist(slug):
        return True
    return slug in LLM_AGENT_SLUGS


def assigned_model(slug: str, current: str | None) -> str:
    if not agent_uses_llm(slug):
        return ""
    return (current or "").strip() or settings.ollama_chat_model


def catalog_chat_model(db: Any, slug: str) -> str | None:
    from app.db.models import Agent

    row = db.query(Agent).filter(Agent.slug == slug).first()
    name = assigned_model(slug, row.model if row else None)
    return name or None

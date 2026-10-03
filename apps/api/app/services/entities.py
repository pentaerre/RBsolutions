from __future__ import annotations

import re
from typing import Any

STOP = {
    "the",
    "and",
    "for",
    "with",
    "from",
    "this",
    "that",
    "invoice",
    "total",
    "date",
    "sheet",
    "page",
    "document",
    "company",
    "limited",
}

EMAIL_RE = re.compile(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", re.I)
MONEY_RE = re.compile(r"(?:EUR|USD|GBP|€|\$)\s?[0-9][0-9.,]+|[0-9][0-9.,]+\s?(?:EUR|USD|GBP)")
INVOICE_RE = re.compile(r"(?:invoice|factura|inv)[\s#:.-]*([A-Z0-9-]{3,})", re.I)
ORG_RE = re.compile(r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,3})\b")


def extract_graph(
    text: str, filename: str = "", use_llm: bool = False, model: str | None = None
) -> dict[str, Any]:
    entities: dict[str, dict[str, str]] = {}
    relations: list[dict[str, str]] = []

    def add(name: str, kind: str) -> str:
        key = re.sub(r"\s+", " ", name).strip()
        if len(key) < 3:
            return ""
        slug = key.lower()
        entities[slug] = {"key": slug, "name": key, "kind": kind}
        return slug

    extra = _llm_graph(text, filename, model=model) if use_llm else {}
    add(filename, "document")
    for item in extra.get("entities") or []:
        add(str(item.get("name") or ""), str(item.get("kind") or "entity"))
    for email in EMAIL_RE.findall(text or ""):
        add(email, "email")
    for money in MONEY_RE.findall(text or ""):
        add(money.strip(), "amount")
    for match in INVOICE_RE.finditer(text or ""):
        add(match.group(1), "invoice")
    for match in ORG_RE.finditer(text or ""):
        token = match.group(1)
        if token.lower() in STOP or token.lower().split()[0] in STOP:
            continue
        if len(token) > 40:
            continue
        add(token, "entity")

    for link in extra.get("relations") or []:
        left = str(link.get("from") or "").lower()
        right = str(link.get("to") or "").lower()
        if left in entities and right in entities:
            relations.append(
                {
                    "from": left,
                    "to": right,
                    "type": str(link.get("type") or "RELATED"),
                }
            )

    keys = list(entities)
    for left, right in zip(keys, keys[1:]):
        if entities[left]["kind"] == "document" or entities[right]["kind"] == "document":
            continue
        relations.append({"from": left, "to": right, "type": "CO_OCCURS"})
        if entities[left]["kind"] == "invoice" and entities[right]["kind"] == "amount":
            relations.append({"from": left, "to": right, "type": "HAS_AMOUNT"})
        if entities[left]["kind"] == "invoice" and entities[right]["kind"] == "entity":
            relations.append({"from": left, "to": right, "type": "MENTIONS_PARTY"})
    return {"entities": list(entities.values()), "relations": relations}


def _llm_graph(text: str, filename: str, model: str | None = None) -> dict[str, Any]:
    if not (text or "").strip():
        return {}
    from app.services.llm import complete_json

    data = complete_json(
        (
            f"Extract named entities and relations from {filename}. "
            'Return JSON {"entities":[{"name":"...","kind":"org|person|well|field|place|other"}],'
            '"relations":[{"from":"...","to":"...","type":"RELATED"}]}. '
            "Max 12 entities. Text:\n"
            f"{(text or '')[:4000]}"
        ),
        model=model,
    )
    if not isinstance(data, dict):
        return {}
    return data

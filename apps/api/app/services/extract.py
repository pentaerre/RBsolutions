from __future__ import annotations

import re
from typing import Any

from app.services.classify import STRUCTURED_TYPES


def extract_records(
    doc_type: str, parsed: dict[str, Any], filename: str, model: str | None = None
) -> list[dict[str, Any]]:
    if doc_type not in STRUCTURED_TYPES and not parsed.get("tables"):
        return []
    if parsed.get("tables"):
        records = []
        for table in parsed["tables"]:
            for row in table.get("rows") or []:
                records.append(
                    {
                        "kind": doc_type or "spreadsheet",
                        "payload": {"filename": filename, "sheet": table.get("sheet"), **row},
                    }
                )
        if records:
            return records[:200]
    text = parsed.get("text") or ""
    heuristic = _heuristic_invoice(text, filename) if doc_type == "invoice" else {
        "filename": filename,
        "summary": text[:800],
    }
    payload = {**heuristic}
    for key, value in _llm_fields(text, filename, doc_type, model=model).items():
        if value not in (None, "", [], {}):
            payload[key] = value
    return [{"kind": doc_type or "document", "payload": payload}]


def _heuristic_invoice(text: str, filename: str) -> dict[str, Any]:
    number = _first(r"(?:invoice|factura)\s*(?:no\.?|number|#)?\s*[:.]?\s*([A-Z0-9-]{3,})", text)
    total = _first(r"(?:total|amount due|importe)\s*[:.]?\s*([0-9][0-9.,]+)", text)
    date = _first(r"(?:date|fecha)\s*[:.]?\s*([0-9]{1,4}[-/.][0-9]{1,2}[-/.][0-9]{1,4})", text)
    return {
        "filename": filename,
        "invoice_number": number,
        "total": total,
        "date": date,
        "summary": text[:800],
    }


def _first(pattern: str, text: str) -> str:
    match = re.search(pattern, text, flags=re.IGNORECASE)
    return match.group(1).strip() if match else ""


def _llm_fields(text: str, filename: str, doc_type: str, model: str | None = None) -> dict[str, Any]:
    from app.services.llm import complete_json

    prompt = (
        f"Extract structured fields from this {doc_type} named {filename}. "
        "Return JSON only with keys that are present. Text:\n"
        f"{text[:6000]}"
    )
    try:
        data = complete_json(prompt, model=model)
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}

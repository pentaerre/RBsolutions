from __future__ import annotations

from pathlib import Path

DOC_TYPES = (
    "invoice",
    "contract",
    "policy",
    "report",
    "spreadsheet",
    "presentation",
    "form",
    "other",
)

STRUCTURED_TYPES = {"invoice", "spreadsheet", "form"}

_KEYWORDS: list[tuple[str, tuple[str, ...]]] = [
    ("invoice", ("invoice", "factura", "vat", "iban", "bill to", "tax invoice")),
    ("contract", ("contract", "agreement", "nda", "terms of service", "whereas")),
    ("policy", ("policy", "handbook", "standard operating", "code of conduct")),
    ("form", ("application form", "request form", "please fill")),
    ("report", ("report", "minutes", "quarterly", "findings")),
]


def classify_document(path: Path, text: str = "", model: str | None = None) -> str:
    guessed = _llm_type(path.name, text, model=model)
    if guessed in DOC_TYPES and guessed != "other":
        return guessed
    heuristic = _heuristic_type(path, text)
    if heuristic:
        return heuristic
    if guessed in DOC_TYPES:
        return guessed
    return "other"


def _heuristic_type(path: Path, text: str) -> str:
    suffix = Path(path).suffix.lower()
    blob = f"{path.name}\n{text[:4000]}".lower()
    for doc_type, tokens in _KEYWORDS:
        if any(token in blob for token in tokens):
            return doc_type
    if suffix in {".xlsx", ".csv", ".xls"}:
        return "spreadsheet"
    if suffix in {".pptx", ".ppt"}:
        return "presentation"
    if suffix in {".docx", ".doc"}:
        return "report"
    return ""


def _llm_type(filename: str, text: str, model: str | None = None) -> str:
    if not (text or "").strip():
        return ""
    from app.services.llm import complete_json

    data = complete_json(
        (
            f"Classify this file as one of: {', '.join(DOC_TYPES)}. "
            f"Name: {filename}\nText:\n{(text or '')[:2500]}\n"
            'Return JSON {"type":"..."}.'
        ),
        model=model,
    )
    return str(data.get("type") or "").strip().lower()

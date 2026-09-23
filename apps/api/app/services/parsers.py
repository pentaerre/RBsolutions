from __future__ import annotations

from pathlib import Path
from typing import Any

from pypdf import PdfReader

SUPPORTED_SUFFIXES = {".pdf", ".xlsx", ".pptx", ".docx", ".csv", ".txt", ".md"}


def parse_file(path: Path) -> dict[str, Any]:
    path = Path(path)
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        return _parse_pdf(path)
    if suffix == ".xlsx":
        return _parse_xlsx(path)
    if suffix == ".pptx":
        return _parse_pptx(path)
    if suffix == ".docx":
        return _parse_docx(path)
    if suffix == ".csv":
        return _parse_csv(path)
    if suffix in {".txt", ".md"}:
        text = path.read_text(encoding="utf-8", errors="ignore")
        return {"text": text, "pages": 1, "kind": "text", "tables": []}
    return {"text": "", "pages": 0, "kind": "unsupported", "tables": [], "error": f"unsupported type {suffix}"}


def _parse_pdf(path: Path) -> dict[str, Any]:
    reader = PdfReader(str(path))
    pages = [(page.extract_text() or "") for page in reader.pages]
    return {"text": "\n\n".join(pages), "pages": len(pages), "kind": "pdf", "tables": []}


def _parse_xlsx(path: Path) -> dict[str, Any]:
    from openpyxl import load_workbook

    workbook = load_workbook(path, read_only=True, data_only=True)
    tables: list[dict[str, Any]] = []
    parts: list[str] = []
    sheet_count = 0
    for sheet in workbook.worksheets:
        sheet_count += 1
        rows = list(sheet.iter_rows(values_only=True))
        if not rows:
            continue
        headers = [_cell(value) for value in rows[0]]
        body = []
        for raw in rows[1:201]:
            record = {headers[index] or f"col_{index}": _cell(raw[index] if index < len(raw) else "") for index in range(len(headers))}
            if any(str(value).strip() for value in record.values()):
                body.append(record)
        tables.append({"sheet": sheet.title, "headers": headers, "rows": body})
        parts.append(f"# Sheet {sheet.title}")
        parts.append(" | ".join(headers))
        for record in body[:40]:
            parts.append(" | ".join(str(record.get(header, "")) for header in headers))
    workbook.close()
    return {"text": "\n".join(parts), "pages": sheet_count or len(tables), "kind": "spreadsheet", "tables": tables}


def _parse_pptx(path: Path) -> dict[str, Any]:
    from pptx import Presentation

    deck = Presentation(str(path))
    slides: list[str] = []
    for index, slide in enumerate(deck.slides, start=1):
        bits = [f"# Slide {index}"]
        for shape in slide.shapes:
            if hasattr(shape, "text") and shape.text:
                bits.append(shape.text)
        slides.append("\n".join(bits))
    return {"text": "\n\n".join(slides), "pages": len(slides), "kind": "presentation", "tables": []}


def _parse_docx(path: Path) -> dict[str, Any]:
    from docx import Document

    document = Document(str(path))
    paragraphs = [item.text for item in document.paragraphs if item.text]
    return {"text": "\n".join(paragraphs), "pages": max(1, len(paragraphs) // 40), "kind": "document", "tables": []}


def _parse_csv(path: Path) -> dict[str, Any]:
    import csv

    with path.open(newline="", encoding="utf-8", errors="ignore") as handle:
        reader = csv.DictReader(handle)
        rows = [dict(row) for _, row in zip(range(200), reader)]
        headers = reader.fieldnames or []
    lines = [" | ".join(headers)]
    for row in rows[:40]:
        lines.append(" | ".join(str(row.get(header, "")) for header in headers))
    return {
        "text": "\n".join(lines),
        "pages": 1,
        "kind": "spreadsheet",
        "tables": [{"sheet": path.stem, "headers": headers, "rows": rows}],
    }


def _cell(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()

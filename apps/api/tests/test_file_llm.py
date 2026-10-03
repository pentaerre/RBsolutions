from pathlib import Path

from app.config import settings
from app.services.classify import classify_document as triage_document
from app.services.entities import extract_graph
from app.services.extract import extract_records
from app.services.reader import read_document
from app.services.taxonomy import classify_document, default_config


def test_reader_prefers_llm_summary(tmp_path: Path, monkeypatch) -> None:
    previous = settings.file_llm
    settings.file_llm = True
    try:
        monkeypatch.setattr(
            "app.services.llm.complete_json",
            lambda prompt, model=None, **kwargs: {
                "summary": "Mud report from the wellsite covering standpipe pressure.",
                "keywords": ["mud", "standpipe", "wellsite"],
            },
        )
        path = tmp_path / "daily-mud-report.txt"
        path.write_text("Daily drilling mud report. BHA trip and standpipe pressure.\n")
        card = read_document(path)
        assert "wellsite" in card["summary"]
        assert "mud" in card["keywords"]
    finally:
        settings.file_llm = previous


def test_reader_falls_back_without_llm(tmp_path: Path) -> None:
    path = tmp_path / "daily-mud-report.txt"
    path.write_text("Daily drilling mud report. BHA trip and standpipe pressure.\n")
    card = read_document(path)
    assert card["summary"]
    assert card["keywords"]


def test_taxonomy_keeps_strong_path_without_llm() -> None:
    placed = classify_document(
        "inbox/wells/drilling/daily-mud-report.txt",
        "daily-mud-report.txt",
        "Standpipe pressure and BHA trip.",
        default_config(),
    )
    assert placed["l1"] == "wells"
    assert placed["l2"] == "drilling"
    assert placed["method"] == "heuristic"
    assert placed["note"].startswith("off:")


def test_taxonomy_llm_wins_over_path(monkeypatch) -> None:
    previous = settings.file_llm
    settings.file_llm = True
    try:
        monkeypatch.setattr(
            "app.services.llm.complete_json",
            lambda prompt, model=None, **kwargs: {"l1": "hse", "l2": "incidents"},
        )
        placed = classify_document(
            "inbox/wells/drilling/daily-mud-report.txt",
            "daily-mud-report.txt",
            "Standpipe pressure and BHA trip.",
            default_config(),
        )
        assert placed["l1"] == "hse"
        assert placed["l2"] == "incidents"
        assert placed["method"] == "llm"
    finally:
        settings.file_llm = previous


def test_taxonomy_invoice_uses_llm_when_it_answers(monkeypatch) -> None:
    previous = settings.file_llm
    settings.file_llm = True
    try:
        monkeypatch.setattr(
            "app.services.llm.complete_json",
            lambda prompt, model=None, **kwargs: {"l1": "commercial", "l2": "invoices"},
        )
        placed = classify_document(
            "inbox/wells/1000+ PDF_Invoice_Folder/invoice_Tony Molinari_25880.pdf",
            "invoice_Tony Molinari_25880.pdf",
            "Invoice number 25880 total 120.00 due on receipt.",
            default_config(),
        )
        assert placed["l1"] == "commercial"
        assert placed["l2"] == "invoices"
        assert placed["method"] == "llm"
    finally:
        settings.file_llm = previous


def test_taxonomy_records_heuristic_when_llm_silent(monkeypatch) -> None:
    previous = settings.file_llm
    settings.file_llm = True
    try:
        monkeypatch.setattr("app.services.llm.complete_json", lambda prompt, model=None, **kwargs: {})
        placed = classify_document(
            "inbox/wells/invoices/invoice_Tom Zandusky_2964.pdf",
            "invoice_Tom Zandusky_2964.pdf",
            "Invoice number 2964 total 80.00",
            default_config(),
        )
        assert placed["l1"] == "commercial"
        assert placed["l2"] == "invoices"
        assert placed["method"] == "heuristic"
        assert "timeout" in placed["note"]
    finally:
        settings.file_llm = previous


def test_triage_llm_wins_over_keywords(tmp_path: Path, monkeypatch) -> None:
    previous = settings.file_llm
    settings.file_llm = True
    try:
        monkeypatch.setattr(
            "app.services.llm.complete_json",
            lambda prompt, model=None, **kwargs: {"type": "report"},
        )
        path = tmp_path / "supplier-invoice.pdf"
        path.write_bytes(b"%PDF-1.4")
        assert triage_document(path, "Invoice number INV-9 total 12.00") == "report"
    finally:
        settings.file_llm = previous


def test_extractor_llm_wins_over_regex(monkeypatch) -> None:
    previous = settings.file_llm
    settings.file_llm = True
    try:
        monkeypatch.setattr(
            "app.services.llm.complete_json",
            lambda prompt, model=None, **kwargs: {"invoice_number": "LLM-1", "total": "99"},
        )
        rows = extract_records(
            "invoice",
            {"text": "Invoice number INV-9 total 12.00", "tables": []},
            "inv.txt",
        )
        assert rows[0]["payload"]["invoice_number"] == "LLM-1"
        assert rows[0]["payload"]["total"] == "99"
        assert rows[0]["payload"]["filename"] == "inv.txt"
    finally:
        settings.file_llm = previous


def test_graphsmith_llm_entities_then_heuristic(monkeypatch) -> None:
    previous = settings.file_llm
    settings.file_llm = True
    try:
        monkeypatch.setattr(
            "app.services.llm.complete_json",
            lambda prompt, model=None, **kwargs: {
                "entities": [{"name": "Cantarell", "kind": "field"}],
                "relations": [],
            },
        )
        extracted = extract_graph("Invoice INV-99 from Acme Metals.", "f.pdf", use_llm=True)
        names = {item["name"] for item in extracted["entities"]}
        assert "Cantarell" in names
        assert "INV-99" in names
    finally:
        settings.file_llm = previous

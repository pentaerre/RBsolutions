from pathlib import Path

from app.config import settings
from app.db.seed import CANONICAL_ROUTES
from app.runtime.routing import choose_agent_slug
from app.services import pipeline
from app.services.classify import classify_document
from app.services.entities import extract_graph
from app.services.mailroom import poll_mailbox
from app.services.parsers import parse_file
from app.services.telegram import poll_updates, telegram_configured


def test_classify_invoice_and_spreadsheet(tmp_path: Path) -> None:
    invoice = tmp_path / "supplier-invoice.pdf"
    invoice.write_bytes(b"%PDF-1.4")
    assert classify_document(invoice, "Invoice number INV-9 total 12.00") == "invoice"
    sheet = tmp_path / "budget.xlsx"
    assert classify_document(sheet, "") == "spreadsheet"


def test_csv_pipeline_writes_sql_and_files(tmp_path: Path) -> None:
    previous = settings.documents_dir
    settings.documents_dir = str(tmp_path)
    try:
        inbox = tmp_path / "inbox"
        inbox.mkdir()
        csv_path = inbox / "supplier-invoice.csv"
        csv_path.write_text("invoice_number,total,date\nINV-1,100,2026-01-01\nINV-2,40,2026-01-02\n")
        result = pipeline.process_file(csv_path)
        assert result["status"] == "processed"
        assert result["doc_type"] == "invoice"
        assert result["records"] == 2
        assert result["chunks"] >= 1
        filed = tmp_path / "classified" / "invoice" / "supplier-invoice.csv"
        assert filed.exists()
        rows = [item for item in pipeline.list_records() if item["filename"] == "supplier-invoice.csv"]
        assert len(rows) == 2
        assert {item["kind"] for item in rows} == {"invoice"}
    finally:
        settings.documents_dir = previous


def test_parse_xlsx(tmp_path: Path) -> None:
    from openpyxl import Workbook

    path = tmp_path / "q1-report.xlsx"
    book = Workbook()
    sheet = book.active
    sheet.title = "Q1"
    sheet.append(["account", "amount"])
    sheet.append(["travel", 12])
    sheet.append(["software", 90])
    book.save(path)
    parsed = parse_file(path)
    assert parsed["kind"] == "spreadsheet"
    assert parsed["tables"][0]["rows"][0]["account"] == "travel"
    assert "travel" in parsed["text"]


def test_mailroom_unconfigured() -> None:
    result = poll_mailbox(Path("/tmp/atrium-mail-test"))
    assert result["configured"] is False
    assert result["ok"] is False


def test_courier_unconfigured() -> None:
    assert telegram_configured() is False
    result = poll_updates(Path("/tmp/atrium-tg-test"))
    assert result["configured"] is False


def test_extract_graph_invoice_entities() -> None:
    extracted = extract_graph(
        "Invoice INV-99 from Acme Metals. Total EUR 120.00. Contact bills@acme.test",
        "supplier-invoice.pdf",
    )
    kinds = {item["kind"] for item in extracted["entities"]}
    assert "invoice" in kinds
    assert extracted["relations"]


def test_new_specialists_route() -> None:
    available = {rule["agent"] for rule in CANONICAL_ROUTES}
    available.add("orchestrator")
    assert choose_agent_slug("check the mailbox for attachments", CANONICAL_ROUTES, available) == "mailroom"
    assert choose_agent_slug("extract this invoice to sql", CANONICAL_ROUTES, available) == "extractor"
    assert choose_agent_slug("chunk the documents", CANONICAL_ROUTES, available) == "chunker"
    assert choose_agent_slug("check telegram for files", CANONICAL_ROUTES, available) == "courier"
    assert choose_agent_slug("who is connected to Acme", CANONICAL_ROUTES, available) == "pathfinder"
    assert choose_agent_slug("build the knowledge graph", CANONICAL_ROUTES, available) == "graphsmith"
    assert choose_agent_slug("show exceptions that need a human", CANONICAL_ROUTES, available) == "reviewer"
    assert choose_agent_slug("sync the context prompt", CANONICAL_ROUTES, available) == "scribe"
    assert choose_agent_slug("What does the handbook say about leave?", CANONICAL_ROUTES, available) == "librarian"

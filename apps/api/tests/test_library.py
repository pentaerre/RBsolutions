from pathlib import Path

from app.db.session import SessionLocal
from app.services import library
from app.services.taxonomy import classify_document, default_config


def test_taxonomy_uses_path_and_name() -> None:
    placed = classify_document(
        "inbox/wells/drilling/daily-mud-report.txt",
        "daily-mud-report.txt",
        "Standpipe pressure and BHA trip.",
        default_config(),
    )
    assert placed["l1"] == "wells"
    assert placed["l2"] == "drilling"


def test_taxonomy_invoice_beats_wells_dump_folder() -> None:
    dumped = classify_document(
        "inbox/wells/1000+ PDF_Invoice_Folder/1000+ PDF_Invoice_Folder/invoice_Tony Molinari_25880.pdf",
        "invoice_Tony Molinari_25880.pdf",
        "",
        default_config(),
    )
    assert dumped["l1"] == "commercial"
    assert dumped["l2"] == "invoices"
    assert dumped["method"] == "heuristic"
    assert dumped["note"].startswith("off:")
    nested = classify_document(
        "inbox/wells/invoices/invoice_Tom Zandusky_2964.pdf",
        "invoice_Tom Zandusky_2964.pdf",
        "Invoice number 2964 total 80.00",
        default_config(),
    )
    assert nested["l1"] == "commercial"
    assert nested["l2"] == "invoices"


def test_library_cycle_does_not_rag(tmp_path: Path, monkeypatch) -> None:
    from app.config import settings
    from app.deps import get_vectorstore

    previous = settings.documents_dir
    settings.documents_dir = str(tmp_path)
    try:
        nested = tmp_path / "inbox" / "wells" / "drilling"
        nested.mkdir(parents=True)
        path = nested / "mud-report.txt"
        path.write_text("Daily drilling mud report. BHA trip and standpipe pressure. Casing tally.\n" * 4)
        db = SessionLocal()
        try:
            store = get_vectorstore()
            before = store.count()
            result = library.run_cycle(db)
            assert result["read"] == 1
            assert result["classified"] == 1
            docs = library.list_documents(db)
            assert docs[0]["taxonomy_l1"] == "wells"
            assert docs[0]["taxonomy_l2"] == "drilling"
            assert docs[0]["summary"]
            assert docs[0]["rag_selected"] is False
            assert docs[0]["rel_path"] == "classified/wells/drilling/mud-report.txt"
            filed = Path(docs[0]["abs_path"])
            assert filed.exists()
            assert filed == tmp_path / "classified" / "wells" / "drilling" / "mud-report.txt"
            assert not path.exists()
            assert docs[0]["status"] == "filed"
            assert docs[0]["classify_method"] == "heuristic"
            assert docs[0]["classify_note"].startswith("off:")
            assert result["filed"] == 1
            again = library.run_cycle(db)
            assert again["registered"] == 0
            assert again["read"] == 0
            assert again["classified"] == 0
            assert again["filed"] == 0
            assert store.count() == before
            promoted = library.promote(db, ids=[docs[0]["id"]])
            assert promoted["files"][0]["chunks"] >= 1
            assert store.count() > before
        finally:
            db.close()
    finally:
        settings.documents_dir = previous


def test_reader_and_taxonomist_route() -> None:
    from app.db.seed import CANONICAL_ROUTES
    from app.runtime.routing import choose_agent_slug

    available = {rule["agent"] for rule in CANONICAL_ROUTES}
    available.add("orchestrator")
    assert choose_agent_slug("ocr this scanned pdf", CANONICAL_ROUTES, available) == "reader"
    assert choose_agent_slug("run the taxonomy on the inbox", CANONICAL_ROUTES, available) == "taxonomist"
    assert choose_agent_slug("What does the handbook say about leave?", CANONICAL_ROUTES, available) == "librarian"
    assert choose_agent_slug("organize the classified folder tree", CANONICAL_ROUTES, available) == "clerk"


def test_taxonomist_labels_clerk_moves(tmp_path: Path) -> None:
    from app.config import settings
    from app.db.session import SessionLocal
    from app.services import library

    previous = settings.documents_dir
    settings.documents_dir = str(tmp_path)
    try:
        nested = tmp_path / "inbox" / "wells" / "drilling"
        nested.mkdir(parents=True)
        path = nested / "mud-report.txt"
        path.write_text("Daily drilling mud report. BHA trip and standpipe pressure. Casing tally.\n" * 4)
        db = SessionLocal()
        try:
            library.register_arrivals(db)
            library.read_pending(db)
            labeled = library.classify_pending(db)
            assert labeled["count"] == 1
            assert path.exists()
            docs = library.list_documents(db)
            assert docs[0]["status"] == "classified"
            assert "inbox/" in (docs[0]["rel_path"] or "")
            tree = library.ensure_tree(db)
            assert any(item.endswith("wells/drilling") for item in tree["folders"])
            assert (tmp_path / "classified" / "wells" / "drilling").is_dir()
            listed = library.list_tree()
            assert any(folder["l1"] == "wells" for folder in listed["folders"])
            filed = library.file_classified(db)
            assert filed["count"] == 1
            assert not path.exists()
            docs = library.list_documents(db)
            assert docs[0]["status"] == "filed"
            assert docs[0]["rel_path"] == "classified/wells/drilling/mud-report.txt"
        finally:
            db.close()
    finally:
        settings.documents_dir = previous


def test_idp_file_pending_skips_library_inbox(tmp_path: Path) -> None:
    from app.config import settings
    from app.db.session import SessionLocal
    from app.services import library, pipeline

    previous = settings.documents_dir
    settings.documents_dir = str(tmp_path)
    try:
        inbox = tmp_path / "inbox"
        inbox.mkdir()
        library_file = inbox / "mud-report.txt"
        library_file.write_text("Daily drilling mud report. BHA trip and standpipe pressure.\n")
        leftover = inbox / "supplier-invoice.csv"
        leftover.write_text("invoice_number,total\nINV-1,10\n")
        db = SessionLocal()
        try:
            library.register_path(db, library_file)
            db.commit()
            moved = pipeline.file_pending()
            names = {item["filename"] for item in moved.get("files") or []}
            assert library_file.exists()
            assert "mud-report.txt" not in names
            assert "supplier-invoice.csv" in names
            assert not leftover.exists()
        finally:
            db.close()
    finally:
        settings.documents_dir = previous


def test_filed_heuristic_retries_with_llm(tmp_path: Path, monkeypatch) -> None:
    from app.config import settings

    previous = settings.documents_dir
    previous_llm = settings.file_llm
    settings.documents_dir = str(tmp_path)
    try:
        inbox = tmp_path / "inbox"
        inbox.mkdir()
        path = inbox / "invoice_retry_llm.txt"
        path.write_text("Invoice number RETRY-1 total 10.00\n")
        db = SessionLocal()
        try:
            settings.file_llm = False
            library.run_cycle(db)
            docs = [item for item in library.list_documents(db) if item["filename"] == "invoice_retry_llm.txt"]
            assert docs[0]["classify_method"] == "heuristic"
            assert docs[0]["rel_path"].startswith("classified/")
            settings.file_llm = True
            monkeypatch.setattr(
                "app.services.llm.complete_json",
                lambda prompt, model=None, **kwargs: {"l1": "commercial", "l2": "invoices"},
            )
            placed = library.classify_pending(db, filename="invoice_retry_llm.txt")
            assert placed["count"] == 1
            assert placed["files"][0]["classify_method"] == "llm"
            assert placed["files"][0]["taxonomy_l1"] == "commercial"
        finally:
            db.close()
    finally:
        settings.documents_dir = previous
        settings.file_llm = previous_llm


def test_library_api(client, tmp_path: Path, monkeypatch) -> None:
    from app.config import settings

    previous = settings.documents_dir
    settings.documents_dir = str(tmp_path)
    try:
        folder = tmp_path / "inbox" / "hse" / "incidents"
        folder.mkdir(parents=True)
        (folder / "spill-incident.txt").write_text("Near miss oil spill incident report at the wellsite.\n")
        ran = client.post("/api/library/run").json()
        assert ran["classified"] >= 1
        listed = client.get("/api/library").json()
        assert listed["taxonomy_name"] == "E&P"
        assert listed["taxonomist"] == "taxonomist"
        assert all(item["slug"] == "taxonomist" for item in listed["taxonomists"])
        doc = next(item for item in listed["documents"] if item["filename"] == "spill-incident.txt")
        assert doc["taxonomy_l1"] == "hse"
        assert "classified/hse/" in (doc.get("abs_path") or "")
        assert doc["status"] == "filed"
        card = client.get(f"/api/library/documents/{doc['id']}").json()
        assert card["abs_path"]
        assert Path(card["abs_path"]).exists()
        cadence = client.patch("/api/library/cadence", json={"cadence": "day"}).json()
        assert cadence["cadence"] == "day"
    finally:
        settings.documents_dir = previous

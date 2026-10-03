from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from app.config import settings
from app.db.models import ExtractedRecord, IntakeDocument
from app.db.session import SessionLocal
from app.deps import get_vectorstore
from app.services.classify import classify_document
from app.services.extract import extract_records
from app.services.llm_agents import catalog_chat_model
from app.services.graphstore import get_graphstore
from app.services.parsers import SUPPORTED_SUFFIXES, parse_file
from app.services.text import chunk_text
from app.services.vectorstore import VectorStore

SKIP_NAMES = {"readme.md"}


def inbox_dir(root: Path | None = None) -> Path:
    if root is not None:
        path = Path(root) / "inbox"
        path.mkdir(parents=True, exist_ok=True)
        return path
    from app.services.knobs import watch_root

    return watch_root()


def classified_dir(doc_type: str, root: Path | None = None) -> Path:
    path = Path(root or settings.documents_dir) / "classified" / doc_type
    path.mkdir(parents=True, exist_ok=True)
    return path


def discover_files(root: Path | None = None) -> list[Path]:
    documents = Path(root or settings.documents_dir)
    documents.mkdir(parents=True, exist_ok=True)
    from app.services.knobs import watch_recursive

    inbox = inbox_dir(root)
    recursive = True if root is not None else watch_recursive()
    found: list[Path] = []
    seen: set[str] = set()
    candidates = inbox.rglob("*") if recursive else inbox.iterdir()
    for path in sorted(candidates):
        if not path.is_file() or not _is_supported(path) or _is_classified(path, documents):
            continue
        key = str(path.resolve())
        if key in seen:
            continue
        found.append(path)
        seen.add(key)
    if root is not None:
        return found
    for path in sorted(documents.iterdir()):
        if path.is_file() and _is_supported(path) and not _is_classified(path) and str(path.resolve()) not in seen:
            found.append(path)
    return found


def list_files(store: VectorStore | None = None, root: Path | None = None) -> list[dict[str, Any]]:
    store = store or get_vectorstore()
    root = Path(root or settings.documents_dir)
    indexed = {item["filename"]: item for item in store.list_sources()}
    db = SessionLocal()
    try:
        intake: dict[str, IntakeDocument] = {}
        for row in db.query(IntakeDocument).all():
            intake[row.rel_path or row.filename] = row
            intake.setdefault(row.filename, row)
    finally:
        db.close()
    files: list[dict[str, Any]] = []
    seen: set[str] = set()
    classified_root = root / "classified"
    candidates = [*discover_files()]
    if classified_root.exists():
        candidates.extend(sorted(classified_root.rglob("*")))
    for path in candidates:
        if not path.is_file() or not _is_supported(path):
            continue
        key = str(path.resolve())
        if key in seen:
            continue
        seen.add(key)
        info = indexed.get(path.name, {})
        try:
            rel = str(path.resolve().relative_to(root.resolve())).replace("\\", "/")
        except ValueError:
            rel = path.name
        row = intake.get(rel) or intake.get(path.name)
        filed = path.parent.parent.name == "classified"
        files.append(
            {
                "filename": path.name,
                "rel_path": rel,
                "size_bytes": path.stat().st_size,
                "indexed": path.name in indexed or bool(row and row.rag_selected),
                "chunks": (row.chunks if row and row.chunks else info.get("chunks", 0)),
                "pages": (row.pages if row else info.get("pages", 0)),
                "path": str(path),
                "source": (row.source if row else "folder"),
                "doc_type": (row.doc_type if row else (path.parent.name if filed else "")),
                "taxonomy_l1": row.taxonomy_l1 if row else "",
                "taxonomy_l2": row.taxonomy_l2 if row else "",
                "status": (row.status if row else ("filed" if filed else "inbox")),
                "classify_method": (getattr(row, "classify_method", "") if row else ""),
                "classify_note": (getattr(row, "classify_note", "") if row else ""),
                "error": (row.error if row else ""),
                "records": row.records if row else 0,
            }
        )
    return files


def process_all(store: VectorStore | None = None, db: Session | None = None) -> dict[str, Any]:
    store = store or get_vectorstore()
    own_db = db is None
    db = db or SessionLocal()
    try:
        results = []
        root = Path(settings.documents_dir).resolve()
        done = {"classified", "indexed", "processed", "filed"}
        for path in discover_files():
            try:
                rel = str(path.resolve().relative_to(root)).replace("\\", "/")
            except ValueError:
                rel = path.name
            existing = (
                db.query(IntakeDocument).filter(IntakeDocument.rel_path == rel).first()
                or db.query(IntakeDocument).filter(IntakeDocument.filename == path.name).first()
            )
            if existing and existing.status in done:
                continue
            results.append(process_file(path, store, db))
        return {
            "files": len(results),
            "chunks": sum(item.get("chunks", 0) for item in results),
            "records": sum(item.get("records", 0) for item in results),
            "results": results,
        }
    finally:
        if own_db:
            db.close()


def process_file(path: Path, store: VectorStore | None = None, db: Session | None = None) -> dict[str, Any]:
    path = Path(path)
    if not _is_supported(path):
        return {"filename": path.name, "chunks": 0, "status": "skipped"}
    store = store or get_vectorstore()
    own_db = db is None
    db = db or SessionLocal()
    try:
        parsed = parse_file(path)
        if parsed.get("error"):
            return {"filename": path.name, "chunks": 0, "status": "skipped", "error": parsed["error"]}
        doc_type = classify_document(path, parsed.get("text") or "", model=catalog_chat_model(db, "triage"))
        chunks = chunk_text(parsed.get("text") or "", settings.chunk_size, settings.chunk_overlap)
        stored = 0
        if chunks:
            stored = store.upsert_chunks(
                filename=path.name,
                source_path=str(path),
                pages=int(parsed.get("pages") or 0),
                chunks=chunks,
                file_id=_file_id(path),
            )
            try:
                get_graphstore().upsert_document(path.name, int(parsed.get("pages") or 0), chunks)
            except Exception:
                pass
        records = extract_records(doc_type, parsed, path.name, model=catalog_chat_model(db, "extractor"))
        row = _upsert_intake(db, path, parsed, doc_type, stored, source=_source_for(path))
        _replace_records(db, row, records)
        dest = classified_dir(doc_type) / path.name
        if path.resolve() != dest.resolve():
            shutil.move(str(path), str(dest))
        row.classified_path = str(dest)
        row.status = "processed"
        row.records = len(records)
        db.commit()
        _notify_processed(path.name, doc_type, stored, len(records))
        return {
            "filename": path.name,
            "pages": int(parsed.get("pages") or 0),
            "chunks": stored,
            "records": len(records),
            "doc_type": doc_type,
            "status": "processed",
            "path": str(dest),
        }
    except Exception as exc:
        db.rollback()
        return {"filename": path.name, "chunks": 0, "status": "error", "error": str(exc)}
    finally:
        if own_db:
            db.close()


def parse_pending() -> dict[str, Any]:
    results = []
    for path in discover_files():
        parsed = parse_file(path)
        results.append(
            {
                "filename": path.name,
                "kind": parsed.get("kind"),
                "pages": parsed.get("pages"),
                "chars": len(parsed.get("text") or ""),
            }
        )
    return {"ok": True, "files": results}


def classify_pending() -> dict[str, Any]:
    results = []
    for path in discover_files():
        parsed = parse_file(path)
        doc_type = classify_document(path, parsed.get("text") or "")
        results.append({"filename": path.name, "doc_type": doc_type})
    return {"ok": True, "files": results}


def chunk_pending(store: VectorStore | None = None) -> dict[str, Any]:
    store = store or get_vectorstore()
    results = []
    for path in discover_files():
        parsed = parse_file(path)
        chunks = chunk_text(parsed.get("text") or "", settings.chunk_size, settings.chunk_overlap)
        stored = store.upsert_chunks(
            filename=path.name,
            source_path=str(path),
            pages=int(parsed.get("pages") or 0),
            chunks=chunks,
            file_id=_file_id(path),
        )
        try:
            get_graphstore().upsert_document(path.name, int(parsed.get("pages") or 0), chunks)
        except Exception:
            pass
        results.append({"filename": path.name, "chunks": stored})
    return {"ok": True, "files": results, "chunks": sum(item["chunks"] for item in results)}


def extract_pending(db: Session | None = None) -> dict[str, Any]:
    own_db = db is None
    db = db or SessionLocal()
    try:
        results = []
        for path in discover_files():
            parsed = parse_file(path)
            doc_type = classify_document(path, parsed.get("text") or "", model=catalog_chat_model(db, "triage"))
            records = extract_records(doc_type, parsed, path.name, model=catalog_chat_model(db, "extractor"))
            row = _upsert_intake(db, path, parsed, doc_type, 0, source=_source_for(path))
            _replace_records(db, row, records)
            row.records = len(records)
            results.append({"filename": path.name, "doc_type": doc_type, "records": len(records)})
        db.commit()
        return {"ok": True, "files": results, "records": sum(item["records"] for item in results)}
    finally:
        if own_db:
            db.close()


def file_pending() -> dict[str, Any]:
    held = _library_hold_paths()
    moved = []
    for path in discover_files():
        if str(path.resolve()) in held:
            continue
        parsed = parse_file(path)
        doc_type = classify_document(path, parsed.get("text") or "")
        dest = classified_dir(doc_type) / path.name
        if path.resolve() != dest.resolve():
            shutil.move(str(path), str(dest))
        moved.append({"filename": path.name, "doc_type": doc_type, "path": str(dest)})
    return {"ok": True, "files": moved}


def _library_hold_paths() -> set[str]:
    db = SessionLocal()
    try:
        held: set[str] = set()
        keep = {"received", "read", "classified", "filed", "indexed", "missing", "failed"}
        for row in db.query(IntakeDocument).all():
            if not (row.taxonomy_l1 or row.taxonomist_slug or (row.status or "") in keep):
                continue
            if row.abs_path:
                held.add(str(Path(row.abs_path).resolve()))
        return held
    finally:
        db.close()


def list_records(db: Session | None = None, limit: int = 100) -> list[dict[str, Any]]:
    own_db = db is None
    db = db or SessionLocal()
    try:
        rows = db.query(ExtractedRecord).order_by(ExtractedRecord.created_at.desc()).limit(limit).all()
        items = []
        for row in rows:
            items.append(
                {
                    "id": row.id,
                    "kind": row.kind,
                    "filename": row.document.filename if row.document else "",
                    "payload": json.loads(row.payload_json or "{}"),
                    "created_at": row.created_at.isoformat() if row.created_at else "",
                }
            )
        return items
    finally:
        if own_db:
            db.close()


def build_knowledge_graph() -> dict[str, Any]:
    root = Path(settings.documents_dir)
    files = []
    for path in [*discover_files(root)]:
        files.append(path)
    classified = root / "classified"
    if classified.exists():
        files.extend(p for p in classified.rglob("*") if p.is_file() and _is_supported(p))
    built = []
    store = get_graphstore()
    for path in files:
        parsed = parse_file(path)
        chunks = chunk_text(parsed.get("text") or "", settings.chunk_size, settings.chunk_overlap)
        if not chunks:
            continue
        try:
            stats = store.rebuild_from_chunks(path.name, int(parsed.get("pages") or 0), chunks)
        except Exception as exc:
            built.append({"filename": path.name, "status": "error", "error": str(exc)})
            continue
        built.append({"filename": path.name, "status": "ok", **stats, "chunks": len(chunks)})
    return {"ok": True, "files": built, "count": len(built)}


def _notify_processed(filename: str, doc_type: str, chunks: int, records: int) -> None:
    from app.services.telegram import send_message, telegram_configured

    if not telegram_configured():
        return
    try:
        send_message(f"Atrium processed {filename} as {doc_type}: {chunks} chunks, {records} SQL rows.")
    except Exception:
        pass


def _is_supported(path: Path) -> bool:
    return path.suffix.lower() in SUPPORTED_SUFFIXES and path.name.lower() not in SKIP_NAMES


def _is_classified(path: Path, root: Path | None = None) -> bool:
    root = Path(root or settings.documents_dir)
    classified = (root / "classified").resolve()
    try:
        Path(path).resolve().relative_to(classified)
        return True
    except ValueError:
        return False


def _source_for(path: Path, root: Path | None = None) -> str:
    root = Path(root or settings.documents_dir)
    if path.parent == inbox_dir(root):
        return "inbox"
    return "folder"


def _file_id(path: Path) -> str:
    stat = path.stat()
    raw = f"{path.name}:{stat.st_size}:{stat.st_mtime_ns}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def _upsert_intake(
    db: Session,
    path: Path,
    parsed: dict[str, Any],
    doc_type: str,
    chunks: int,
    source: str,
) -> IntakeDocument:
    rel = str(path.name)
    root = Path(settings.documents_dir)
    try:
        rel = str(path.resolve().relative_to(root.resolve())).replace("\\", "/")
    except ValueError:
        rel = path.name
    row = db.query(IntakeDocument).filter(IntakeDocument.rel_path == rel).first()
    if row is None:
        row = db.query(IntakeDocument).filter(IntakeDocument.filename == path.name).first()
    if row is None:
        row = IntakeDocument(filename=path.name, rel_path=rel)
        db.add(row)
    row.filename = path.name
    row.rel_path = rel
    row.abs_path = str(path.resolve())
    row.source = source
    row.suffix = path.suffix.lower()
    row.doc_type = doc_type
    row.pages = int(parsed.get("pages") or 0)
    row.chunks = chunks
    row.size_bytes = int(path.stat().st_size)
    row.text_preview = (parsed.get("text") or "")[:2000]
    row.status = "received"
    db.flush()
    return row


def _replace_records(db: Session, document: IntakeDocument, records: list[dict[str, Any]]) -> None:
    db.query(ExtractedRecord).filter(ExtractedRecord.document_id == document.id).delete()
    for item in records:
        db.add(
            ExtractedRecord(
                document_id=document.id,
                kind=str(item.get("kind") or document.doc_type),
                payload_json=json.dumps(item.get("payload") or {}, default=str),
            )
        )

from __future__ import annotations

import fcntl
import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from app.config import settings
from app.db.models import Agent, IntakeDocument
from app.deps import get_vectorstore
from app.services import knobs, pipeline
from app.services.llm_agents import catalog_chat_model
from app.services.reader import read_document
from app.services.taxonomy import (
    active_slug,
    classify_document,
    in_scope,
    list_agents as list_taxonomists,
    load_config,
    owner_slug,
    resolve_slug,
    tree as taxonomy_tree,
)
from app.services.text import chunk_text
from app.services.graphstore import get_graphstore

READ_STATUSES = ("received", "missing", "failed", "")
CLASSIFY_STATUSES = ("received", "read")
RETRY_STATUSES = ("classified", "filed")
RETRY_LIMIT = 4


def documents_root() -> Path:
    root = Path(settings.documents_dir)
    root.mkdir(parents=True, exist_ok=True)
    return root


def rel_path_for(path: Path) -> str:
    root = documents_root().resolve()
    resolved = Path(path).resolve()
    try:
        return str(resolved.relative_to(root)).replace("\\", "/")
    except ValueError:
        return Path(path).name


def register_path(db: Session, path: Path, source: str = "folder", source_ref: str = "") -> IntakeDocument | None:
    path = Path(path)
    if not path.is_file() or not pipeline._is_supported(path):
        return None
    if pipeline._is_classified(path):
        return None
    rel = rel_path_for(path)
    row = db.query(IntakeDocument).filter(IntakeDocument.rel_path == rel).first()
    if row is None:
        row = db.query(IntakeDocument).filter(IntakeDocument.filename == path.name).first()
    if row is None:
        row = IntakeDocument(filename=path.name, rel_path=rel)
        db.add(row)
    stat = path.stat()
    row.filename = path.name
    row.rel_path = rel
    row.abs_path = str(path.resolve())
    row.suffix = path.suffix.lower()
    row.source = source or row.source or "folder"
    if source_ref:
        row.source_ref = source_ref
    row.size_bytes = int(stat.st_size)
    row.file_created_at = datetime.utcfromtimestamp(stat.st_mtime)
    if not row.status:
        row.status = "received"
    db.flush()
    return row


def register_arrivals(db: Session, source: str = "folder") -> dict[str, Any]:
    created = 0
    files = []
    for path in pipeline.discover_files():
        before = db.query(IntakeDocument).filter(IntakeDocument.rel_path == rel_path_for(path)).first()
        row = register_path(db, path, source=source)
        if row is None:
            continue
        if before is None:
            created += 1
            row.status = "received"
        files.append(_to_dict(row))
    db.commit()
    return {"ok": True, "registered": created, "files": files, "count": len(files)}


def read_pending(db: Session, filename: str | None = None) -> dict[str, Any]:
    register_arrivals(db)
    rows = _pending_rows(db, filename, statuses=READ_STATUSES)
    results = []
    for row in rows:
        results.append(read_row(db, row))
        db.commit()
    return {"ok": True, "files": results, "count": len(results)}


def read_row(db: Session, row: IntakeDocument) -> dict[str, Any]:
    path = Path(row.abs_path or "") if row.abs_path else documents_root() / (row.rel_path or row.filename)
    if not path.exists():
        row.status = "missing"
        row.error = "file not found"
        return _to_dict(row)
    parsed = read_document(path, pages=knobs.reader_pages(db), model=catalog_chat_model(db, "reader"))
    row.pages = int(parsed.get("pages") or 0)
    row.read_pages = int(parsed.get("read_pages") or 0)
    row.ocr_used = 1 if parsed.get("ocr_used") else 0
    row.summary = parsed.get("summary") or ""
    row.keywords = json.dumps(parsed.get("keywords") or [])
    row.text_preview = (parsed.get("text") or "")[:4000]
    row.error = parsed.get("error") or ""
    if row.status in {"received", "missing", "failed", ""}:
        row.status = "read"
    return {**_to_dict(row), "kind": parsed.get("kind")}


def classify_pending(db: Session, filename: str | None = None, slug: str = "taxonomist") -> dict[str, Any]:
    config = load_config(db, slug)
    owners = _owner_table(db, extra_slug=config.get("slug") or slug)
    rows = _pending_rows(db, filename, statuses=CLASSIFY_STATUSES)
    seen = {row.id for row in rows}
    extra = _llm_retry_rows(db, filename)
    if not filename:
        extra = extra[:RETRY_LIMIT]
    for row in extra:
        if row.id not in seen:
            rows.append(row)
            seen.add(row.id)
    results = []
    for row in rows:
        rel = row.rel_path or row.filename
        claimed = (row.taxonomist_slug or "") == (config.get("slug") or slug)
        if not claimed:
            if owner_slug(rel, owners) != (config.get("slug") or slug):
                continue
            if not in_scope(rel, config.get("scope_path")):
                continue
        path = Path(row.abs_path or "") if row.abs_path else documents_root() / rel
        if not path.exists():
            row.status = "missing"
            row.error = "file not found"
            row.classify_method = ""
            row.classify_note = "missing"
            db.commit()
            continue
        placed = classify_document(
            rel,
            row.filename,
            row.text_preview or row.summary or "",
            config,
            model=catalog_chat_model(db, config.get("slug") or slug),
        )
        row.taxonomy_l1 = placed["l1"]
        row.taxonomy_l2 = placed["l2"]
        row.taxonomist_slug = config.get("slug") or slug
        row.classify_method = placed.get("method") or ""
        row.classify_note = placed.get("note") or ""
        if row.status in {"received", "read"}:
            row.status = "classified"
        results.append(_to_dict(row))
        db.commit()
    return {"ok": True, "files": results, "count": len(results), "taxonomy": config["taxonomy"].get("name"), "taxonomist": config.get("slug") or slug}


def run_cycle(db: Session, slug: str | None = None) -> dict[str, Any]:
    lock = _acquire_cycle_lock()
    if lock is None:
        config = load_config(db, slug) if slug else load_config(db)
        return {
            "ok": True,
            "registered": 0,
            "read": 0,
            "classified": 0,
            "filed": 0,
            "files": [],
            "cadence": config.get("cadence"),
            "taxonomy": (config.get("taxonomy") or {}).get("name") if slug else None,
            "taxonomist": slug or "all",
        }
    try:
        return _run_cycle_hops(db, slug)
    finally:
        _release_cycle_lock(lock)


def _run_cycle_hops(db: Session, slug: str | None = None) -> dict[str, Any]:
    registered = register_arrivals(db)
    from app.runtime.tools import invoke_tool

    invoke_tool(db, "folders.ensure", {})
    # One live LLM call at a time on this host. Per-file hops free Clerk/UI to show progress; they do not mean concurrent Qwen workers.
    retry_ids = {row.id for row in _llm_retry_rows(db, None)[:RETRY_LIMIT]}
    rows = _hop_rows(db, retry_ids)
    owners = _owner_table(db, extra_slug=slug)
    files: list[dict[str, Any]] = []
    read = 0
    classified = 0
    filed = 0
    last_name = "E&P"
    cadence = "hour"
    for row in rows:
        if row.status in READ_STATUSES:
            read_row(db, row)
            read += 1
            db.commit()
        owner = slug or owner_slug(row.rel_path or row.filename or "", owners)
        if row.status in CLASSIFY_STATUSES or row.id in retry_ids:
            placed = classify_pending(db, filename=row.filename, slug=owner)
            files.extend(placed.get("files") or [])
            classified += int(placed.get("count") or 0)
            last_name = placed.get("taxonomy") or last_name
            cadence = load_config(db, owner).get("cadence") or cadence
            db.refresh(row)
        if row.taxonomy_l1:
            moved = file_classified(db, filename=row.filename)
            filed += int(moved.get("count") or 0)
    return {
        "ok": True,
        "registered": registered.get("registered", 0),
        "read": read,
        "classified": classified,
        "filed": filed,
        "files": files,
        "cadence": cadence if slug else load_config(db).get("cadence"),
        "taxonomy": last_name if slug else None,
        "taxonomist": slug or "all",
    }


def promote(db: Session, ids: list[str] | None = None, filenames: list[str] | None = None) -> dict[str, Any]:
    rows = []
    if ids:
        rows = db.query(IntakeDocument).filter(IntakeDocument.id.in_(ids)).all()
    elif filenames:
        rows = db.query(IntakeDocument).filter(IntakeDocument.filename.in_(filenames)).all()
    store = get_vectorstore()
    results = []
    for row in rows:
        path = Path(row.abs_path) if row.abs_path else documents_root() / (row.rel_path or row.filename)
        if not path.exists():
            results.append({"id": row.id, "filename": row.filename, "status": "missing"})
            continue
        parsed = read_document(path, pages=50, model=catalog_chat_model(db, "reader"))
        text = parsed.get("full_text") or parsed.get("text") or ""
        chunks = chunk_text(text, settings.chunk_size, settings.chunk_overlap)
        stored = 0
        if chunks:
            stored = store.upsert_chunks(
                filename=row.filename,
                source_path=str(path),
                pages=int(parsed.get("pages") or 0),
                chunks=chunks,
                file_id=pipeline._file_id(path),
            )
            try:
                get_graphstore().upsert_document(row.filename, int(parsed.get("pages") or 0), chunks)
            except Exception:
                pass
        row.chunks = stored
        row.rag_selected = 1
        row.status = "indexed"
        results.append({"id": row.id, "filename": row.filename, "chunks": stored, "status": "indexed"})
    db.commit()
    return {"ok": True, "files": results, "count": len(results)}


def list_documents(
    db: Session,
    day: str | None = None,
    l1: str | None = None,
    l2: str | None = None,
    q: str | None = None,
    rag: str | None = None,
    source: str | None = None,
    taxonomist: str | None = None,
) -> list[dict[str, Any]]:
    register_arrivals(db)
    rows = db.query(IntakeDocument).all()
    items = [_to_dict(row) for row in rows]
    if taxonomist:
        owners = _owner_table(db, extra_slug=taxonomist)
        items = [
            item
            for item in items
            if (item.get("taxonomist_slug") or owner_slug(item.get("rel_path") or item.get("filename") or "", owners))
            == taxonomist
        ]
    if day:
        items = [item for item in items if (item.get("file_created_at") or item.get("created_at") or "").startswith(day)]
    if l1:
        items = [item for item in items if item.get("taxonomy_l1") == l1]
    if l2:
        items = [item for item in items if item.get("taxonomy_l2") == l2]
    if source:
        items = [item for item in items if item.get("source") == source]
    if rag == "yes":
        items = [item for item in items if item.get("rag_selected")]
    if rag == "no":
        items = [item for item in items if not item.get("rag_selected")]
    needle = (q or "").strip().lower()
    if needle:
        items = [
            item
            for item in items
            if needle in (item.get("filename") or "").lower()
            or needle in (item.get("rel_path") or "").lower()
            or needle in (item.get("summary") or "").lower()
            or needle in " ".join(item.get("keywords") or []).lower()
            or needle in (item.get("taxonomy_l1") or "").lower()
            or needle in (item.get("taxonomy_l2") or "").lower()
        ]
    items.sort(key=lambda item: item.get("file_created_at") or item.get("created_at") or "", reverse=True)
    return items


def get_document(db: Session, document_id: str) -> dict[str, Any] | None:
    row = db.query(IntakeDocument).filter(IntakeDocument.id == document_id).first()
    if row is None:
        return None
    return _to_dict(row)


def meta(db: Session, slug: str | None = None) -> dict[str, Any]:
    chosen = resolve_slug(db, slug)
    config = load_config(db, chosen)
    live = list_taxonomists(db, live_only=True) or list_taxonomists(db)
    return {
        "cadence": config.get("cadence") or "hour",
        "taxonomy_name": (config.get("taxonomy") or {}).get("name") or "E&P",
        "tree": taxonomy_tree(config),
        "inbox": str(pipeline.inbox_dir()),
        "scope_path": config.get("scope_path") or "inbox",
        "taxonomist": config.get("slug") or chosen,
        "taxonomists": [
            {
                "slug": agent.slug,
                "name": agent.name,
                "taxonomy_name": (load_config(db, agent.slug).get("taxonomy") or {}).get("name") or agent.name,
                "scope_path": load_config(db, agent.slug).get("scope_path") or "inbox",
                "cadence": load_config(db, agent.slug).get("cadence") or "hour",
                "model": agent.model or "",
                "status": agent.status,
            }
            for agent in live
        ],
    }


def set_cadence(db: Session, cadence: str, slug: str = "taxonomist") -> dict[str, Any]:
    allowed = {"hour", "day", "week"}
    value = (cadence or "hour").strip().lower()
    if value not in allowed:
        value = "hour"
    agent = db.query(Agent).filter(Agent.slug == slug).first()
    if agent is None:
        return {"ok": False, "cadence": value, "taxonomist": slug}
    payload = json.loads(agent.config_json or "{}")
    payload["cadence"] = value
    if not payload.get("taxonomy"):
        payload["taxonomy"] = load_config(db, slug)["taxonomy"]
    agent.config_json = json.dumps(payload)
    db.commit()
    return {"ok": True, "cadence": value, "taxonomist": slug}


def _owner_table(db: Session, extra_slug: str | None = None) -> list[tuple[str, str]]:
    rows = []
    seen: set[str] = set()
    agents = list(list_taxonomists(db, live_only=True))
    if extra_slug and extra_slug not in {agent.slug for agent in agents}:
        extra = db.query(Agent).filter(Agent.slug == extra_slug).first()
        if extra is not None:
            agents.append(extra)
    if not agents:
        agents = list(list_taxonomists(db))
    for agent in agents:
        if agent.slug in seen:
            continue
        seen.add(agent.slug)
        cfg = load_config(db, agent.slug)
        rows.append((agent.slug, str(cfg.get("scope_path") or "inbox")))
    if not rows:
        rows.append(("taxonomist", "inbox"))
    return rows


def ensure_tree(db: Session, slug: str | None = None) -> dict[str, Any]:
    if slug:
        slugs = [slug]
    else:
        slugs = [agent.slug for agent in list_taxonomists(db, live_only=True)] or [active_slug(db)]
    created: list[str] = []
    for name in slugs:
        for group in taxonomy_tree(load_config(db, name)):
            l1 = str(group.get("id") or "other")
            children = group.get("children") or [{"id": "other"}]
            if not children:
                children = [{"id": "other"}]
            for child in children:
                l2 = str(child.get("id") or "other")
                dest = documents_root() / "classified" / l1 / l2
                dest.mkdir(parents=True, exist_ok=True)
                created.append(f"classified/{l1}/{l2}")
    root = documents_root() / "classified"
    return {"ok": True, "root": str(root.resolve()), "folders": created, "count": len(created)}


def list_tree() -> dict[str, Any]:
    root = documents_root() / "classified"
    folders: list[dict[str, Any]] = []
    if root.exists():
        for l1 in sorted(path for path in root.iterdir() if path.is_dir()):
            children = sorted(path.name for path in l1.iterdir() if path.is_dir())
            files = [path.name for path in l1.rglob("*") if path.is_file()]
            folders.append({"l1": l1.name, "l2": children, "files": files, "count": len(files)})
    return {"ok": True, "root": str(root.resolve()) if root.exists() else str(root), "folders": folders}


def file_classified(db: Session, filename: str | None = None, document_id: str | None = None) -> dict[str, Any]:
    query = (
        db.query(IntakeDocument)
        .filter(IntakeDocument.taxonomy_l1.isnot(None))
        .filter(IntakeDocument.taxonomy_l1 != "")
    )
    if filename:
        query = query.filter(IntakeDocument.filename == filename)
    if document_id:
        query = query.filter(IntakeDocument.id == document_id)
    rows = query.all()
    moved = []
    for row in rows:
        if row.status in {"failed", "missing"}:
            continue
        src = Path(row.abs_path) if row.abs_path else documents_root() / (row.rel_path or row.filename or "")
        already = False
        try:
            rel = str(src.resolve().relative_to(documents_root().resolve())).replace("\\", "/")
            already = rel.startswith(f"classified/{row.taxonomy_l1}/")
        except ValueError:
            already = False
        if already:
            if row.status == "classified":
                row.status = "filed"
                row.classified_path = str(src.resolve()) if src.exists() else (row.classified_path or row.abs_path)
                db.commit()
            continue
        _file_into_tree(row, row.taxonomy_l1, row.taxonomy_l2 or "other")
        if row.status in {"classified", "read", "received"}:
            row.status = "filed"
        moved.append(_to_dict(row))
        db.commit()
    return {"ok": True, "files": moved, "count": len(moved)}


def _hop_rows(db: Session, retry_ids: set[str]) -> list[IntakeDocument]:
    rows = _pending_rows(db, None, statuses=(*READ_STATUSES, "read", "classified"))
    seen = {row.id for row in rows}
    for row in _pending_rows(db, None, statuses=RETRY_STATUSES):
        if row.id in retry_ids and row.id not in seen:
            rows.append(row)
            seen.add(row.id)
    return rows


def _acquire_cycle_lock():
    path = documents_root() / ".run_cycle.lock"
    handle = path.open("a")
    try:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        handle.close()
        return None
    return handle


def _release_cycle_lock(handle) -> None:
    try:
        fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
    finally:
        handle.close()


def _llm_retry_rows(db: Session, filename: str | None = None) -> list[IntakeDocument]:
    if not settings.file_llm:
        return []
    rows = []
    for row in _pending_rows(db, filename, statuses=RETRY_STATUSES):
        method = getattr(row, "classify_method", "") or ""
        note = getattr(row, "classify_note", "") or ""
        if method == "llm" or "timeout" in note:
            continue
        rows.append(row)
    return rows


def _pending_rows(db: Session, filename: str | None = None, statuses: tuple[str, ...] | None = None) -> list[IntakeDocument]:
    query = db.query(IntakeDocument)
    if filename:
        query = query.filter(IntakeDocument.filename == filename)
    if statuses:
        query = query.filter(IntakeDocument.status.in_(statuses))
    return query.all()


def _file_into_tree(row: IntakeDocument, l1: str, l2: str) -> Path:
    dest_dir = documents_root() / "classified" / (l1 or "other") / (l2 or "other")
    dest_dir.mkdir(parents=True, exist_ok=True)
    src = Path(row.abs_path) if row.abs_path else documents_root() / (row.rel_path or row.filename)
    dest = dest_dir / (row.filename or src.name)
    if dest.exists() and (not src.exists() or src.resolve() != dest.resolve()):
        dest = dest_dir / f"{src.stem}-{row.id[:8]}{src.suffix}"
    if src.exists() and src.resolve() != dest.resolve():
        shutil.move(str(src), str(dest))
    resolved = dest if dest.exists() else (src if src.exists() else dest)
    row.abs_path = str(resolved.resolve()) if resolved.exists() else str(dest)
    row.classified_path = row.abs_path
    try:
        row.rel_path = str(Path(row.abs_path).resolve().relative_to(documents_root().resolve())).replace("\\", "/")
    except ValueError:
        row.rel_path = f"classified/{l1 or 'other'}/{l2 or 'other'}/{resolved.name}"
    return dest


def _to_dict(row: IntakeDocument) -> dict[str, Any]:
    try:
        keys = json.loads(row.keywords or "[]")
    except json.JSONDecodeError:
        keys = [part.strip() for part in (row.keywords or "").split(",") if part.strip()]
    return {
        "id": row.id,
        "filename": row.filename,
        "rel_path": row.rel_path or row.filename,
        "abs_path": row.abs_path or "",
        "source": row.source,
        "suffix": row.suffix,
        "doc_type": row.doc_type,
        "status": row.status,
        "pages": row.pages,
        "read_pages": row.read_pages,
        "chunks": row.chunks,
        "records": row.records,
        "size_bytes": row.size_bytes or 0,
        "summary": row.summary or "",
        "keywords": keys if isinstance(keys, list) else [],
        "taxonomy_l1": row.taxonomy_l1 or "",
        "taxonomy_l2": row.taxonomy_l2 or "",
        "taxonomist_slug": row.taxonomist_slug or "",
        "classified_path": row.classified_path or "",
        "classify_method": getattr(row, "classify_method", "") or "",
        "classify_note": getattr(row, "classify_note", "") or "",
        "ocr_used": bool(row.ocr_used),
        "rag_selected": bool(row.rag_selected),
        "file_created_at": row.file_created_at.isoformat() if row.file_created_at else "",
        "created_at": row.created_at.isoformat() if row.created_at else "",
        "error": row.error or "",
        "text_preview": row.text_preview or "",
    }

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.config import settings
from app.db.models import Tool
from app.deps import get_vectorstore
from app.services import pipeline
from app.services.ingest import IngestService
from app.services.mailroom import poll_mailbox


class ToolError(RuntimeError):
    pass


def invoke_tool(db: Session, slug: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    payload = payload or {}
    tool = db.query(Tool).filter(Tool.slug == slug).first()
    if tool is None:
        raise ToolError(f"Unknown tool: {slug}")
    if tool.status != "live":
        raise ToolError(f"Tool is not live: {slug}")

    if tool.kind == "http":
        return _invoke_http(tool, payload)
    handler = BUILTIN.get(slug)
    if handler is None:
        raise ToolError(f"No builtin handler for {slug}")
    return handler(db, payload)


def _invoke_http(tool: Tool, payload: dict[str, Any]) -> dict[str, Any]:
    import json

    import httpx

    config = json.loads(tool.config_json or "{}")
    url = config.get("url")
    if not url:
        raise ToolError(f"HTTP tool {tool.slug} is missing config.url")
    method = str(config.get("method") or "POST").upper()
    response = httpx.request(method, url, json=payload, timeout=30.0)
    response.raise_for_status()
    try:
        body = response.json()
    except ValueError:
        body = {"text": response.text}
    return {"ok": True, "tool": tool.slug, "result": body}


def _search(_db: Session, payload: dict[str, Any]) -> dict[str, Any]:
    question = str(payload.get("query") or payload.get("message") or "")
    store = get_vectorstore()
    hits = store.query(question, int(payload.get("top_k") or settings.rag_top_k))
    from app.services.graphstore import get_graphstore

    hits = get_graphstore().hybrid_search(question, hits)
    return {"ok": True, "tool": "knowledge.search", "mode": "graphrag", "hits": hits}


def _ingest(db: Session, _: dict[str, Any]) -> dict[str, Any]:
    result = pipeline.process_all(get_vectorstore(), db)
    return {"ok": True, "tool": "knowledge.ingest", **result}


def _list_documents(_db: Session, _: dict[str, Any]) -> dict[str, Any]:
    ingest = IngestService(settings, get_vectorstore())
    return {"ok": True, "tool": "documents.list", "files": ingest.list_files()}


def _list_inbox(_db: Session, _: dict[str, Any]) -> dict[str, Any]:
    files = [item for item in pipeline.list_files() if item.get("status") != "processed"]
    return {"ok": True, "tool": "intake.list", "inbox": str(pipeline.inbox_dir()), "files": files}


def _poll_mail(db: Session, _: dict[str, Any]) -> dict[str, Any]:
    result = poll_mailbox(pipeline.inbox_dir())
    for item in result.get("saved") or []:
        from app.db.models import IntakeDocument

        row = db.query(IntakeDocument).filter(IntakeDocument.filename == item["filename"]).first()
        if row is None:
            row = IntakeDocument(filename=item["filename"])
            db.add(row)
        row.source = "email"
        row.source_ref = item.get("subject") or item.get("from") or ""
        row.status = "received"
    if result.get("saved"):
        db.commit()
    return {"ok": result.get("ok", False), "tool": "intake.poll_mail", **result}


def _parse(_db: Session, _: dict[str, Any]) -> dict[str, Any]:
    return {"ok": True, "tool": "documents.parse", **pipeline.parse_pending()}


def _classify(_db: Session, _: dict[str, Any]) -> dict[str, Any]:
    return {"ok": True, "tool": "documents.classify", **pipeline.classify_pending()}


def _chunk(_db: Session, _: dict[str, Any]) -> dict[str, Any]:
    return {"ok": True, "tool": "documents.chunk", **pipeline.chunk_pending()}


def _file(_db: Session, _: dict[str, Any]) -> dict[str, Any]:
    return {"ok": True, "tool": "documents.file", **pipeline.file_pending()}


def _extract(db: Session, _: dict[str, Any]) -> dict[str, Any]:
    return {"ok": True, "tool": "records.extract", **pipeline.extract_pending(db)}


def _list_records(db: Session, _: dict[str, Any]) -> dict[str, Any]:
    return {"ok": True, "tool": "records.list", "records": pipeline.list_records(db)}


def _list_models(_db: Session, _: dict[str, Any]) -> dict[str, Any]:
    import httpx

    from app.services.ollama_client import normalize_models

    response = httpx.get(f"{settings.ollama_base_url.rstrip('/')}/api/tags", timeout=10.0)
    response.raise_for_status()
    models = [item["name"] for item in normalize_models(response.json().get("models", []))]
    return {"ok": True, "tool": "models.list", "models": models}


def _explain(db: Session, _: dict[str, Any]) -> dict[str, Any]:
    from app.services.platform_map import explain_platform

    return {"ok": True, "tool": "platform.explain", "text": explain_platform(db)}


def _docs_sync(db: Session, _: dict[str, Any]) -> dict[str, Any]:
    from app.services.scribe import sync_docs

    result = sync_docs(db)
    return {"ok": bool(result.get("ok")), "tool": "docs.sync", **result}


def _graph_build(_db: Session, _: dict[str, Any]) -> dict[str, Any]:
    result = pipeline.build_knowledge_graph()
    return {"ok": True, "tool": "knowledge.graph_build", **result}


def _graph_search(_db: Session, payload: dict[str, Any]) -> dict[str, Any]:
    from app.services.graphstore import get_graphstore

    query = str(payload.get("query") or payload.get("message") or "")
    result = get_graphstore().entity_search(query)
    return {"ok": True, "tool": "knowledge.graph_search", **result}


def _telegram_poll(db: Session, _: dict[str, Any]) -> dict[str, Any]:
    from app.db.models import IntakeDocument
    from app.services.telegram import poll_updates

    result = poll_updates(pipeline.inbox_dir())
    for item in result.get("saved") or []:
        row = db.query(IntakeDocument).filter(IntakeDocument.filename == item["filename"]).first()
        if row is None:
            row = IntakeDocument(filename=item["filename"])
            db.add(row)
        row.source = "telegram"
        row.source_ref = item.get("chat_id") or ""
        row.status = "received"
    if result.get("saved"):
        db.commit()
    return {"ok": result.get("ok", False), "tool": "telegram.poll", **result}


def _telegram_send(_db: Session, payload: dict[str, Any]) -> dict[str, Any]:
    from app.services.telegram import send_message

    text = str(payload.get("text") or payload.get("message") or "")
    result = send_message(text)
    return {"ok": result.get("ok", False), "tool": "telegram.send", **result}


def _review_list(db: Session, _: dict[str, Any]) -> dict[str, Any]:
    from app.services.reviewer import list_exceptions

    return {"ok": True, "tool": "review.list", **list_exceptions(db)}


BUILTIN = {
    "knowledge.search": _search,
    "knowledge.ingest": _ingest,
    "knowledge.graph_build": _graph_build,
    "knowledge.graph_search": _graph_search,
    "documents.list": _list_documents,
    "documents.parse": _parse,
    "documents.classify": _classify,
    "documents.chunk": _chunk,
    "documents.file": _file,
    "intake.list": _list_inbox,
    "intake.poll_mail": _poll_mail,
    "records.extract": _extract,
    "records.list": _list_records,
    "telegram.poll": _telegram_poll,
    "telegram.send": _telegram_send,
    "review.list": _review_list,
    "models.list": _list_models,
    "platform.explain": _explain,
    "docs.sync": _docs_sync,
}

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.config import settings
from app.db.models import Tool
from app.deps import get_vectorstore
from app.services import library, pipeline
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


def _list_inbox(db: Session, _: dict[str, Any]) -> dict[str, Any]:
    result = library.register_arrivals(db)
    files = [item for item in result.get("files") or [] if item.get("status") != "processed"]
    return {"ok": True, "tool": "intake.list", "inbox": str(pipeline.inbox_dir()), "files": files}


def _register(db: Session, _: dict[str, Any]) -> dict[str, Any]:
    result = library.register_arrivals(db)
    return {"ok": True, "tool": "intake.register", **result}


def _poll_mail(db: Session, _: dict[str, Any]) -> dict[str, Any]:
    from app.services.sentinel import store_letters

    result = poll_mailbox(pipeline.inbox_dir())
    for item in result.get("saved") or []:
        path = pipeline.inbox_dir() / item["filename"]
        library.register_path(db, path, source="email", source_ref=item.get("subject") or item.get("from") or "")
    stored = store_letters(db, result.get("letters") or [])
    if result.get("saved") or stored:
        db.commit()
    return {"ok": result.get("ok", False), "tool": "intake.poll_mail", **result}


def _read(db: Session, payload: dict[str, Any]) -> dict[str, Any]:
    return {"ok": True, "tool": "documents.read", **library.read_pending(db, filename=payload.get("filename"))}


def _taxonomy_run(db: Session, payload: dict[str, Any]) -> dict[str, Any]:
    slug = str(payload.get("agent") or payload.get("taxonomist") or "")
    return {"ok": True, "tool": "taxonomy.run", **library.run_cycle(db, slug or None)}


def _taxonomy_list(db: Session, payload: dict[str, Any]) -> dict[str, Any]:
    slug = str(payload.get("agent") or payload.get("taxonomist") or "") or None
    documents = library.list_documents(
        db,
        day=payload.get("day"),
        l1=payload.get("l1"),
        l2=payload.get("l2"),
        q=payload.get("query") or payload.get("q") or payload.get("message"),
        rag=payload.get("rag"),
        source=payload.get("source"),
        taxonomist=slug,
    )
    return {"ok": True, "tool": "taxonomy.list", "documents": documents, **library.meta(db, slug)}


def _taxonomy_get(db: Session, payload: dict[str, Any]) -> dict[str, Any]:
    document_id = str(payload.get("id") or payload.get("document_id") or "")
    item = library.get_document(db, document_id) if document_id else None
    if item is None:
        files = library.list_documents(db, q=str(payload.get("query") or payload.get("message") or ""))
        item = files[0] if files else None
    return {"ok": True, "tool": "taxonomy.get", "document": item}


def _promote(db: Session, payload: dict[str, Any]) -> dict[str, Any]:
    ids = payload.get("ids") or []
    filenames = payload.get("filenames") or []
    if payload.get("filename"):
        filenames = [*filenames, payload["filename"]]
    return {"ok": True, "tool": "knowledge.promote", **library.promote(db, ids=ids, filenames=filenames)}


def _parse(_db: Session, _: dict[str, Any]) -> dict[str, Any]:
    return {"ok": True, "tool": "documents.parse", **pipeline.parse_pending()}


def _classify(_db: Session, _: dict[str, Any]) -> dict[str, Any]:
    return {"ok": True, "tool": "documents.classify", **pipeline.classify_pending()}


def _chunk(_db: Session, _: dict[str, Any]) -> dict[str, Any]:
    return {"ok": True, "tool": "documents.chunk", **pipeline.chunk_pending()}


def _file(db: Session, payload: dict[str, Any]) -> dict[str, Any]:
    tree = library.ensure_tree(db)
    filed = library.file_classified(
        db,
        filename=payload.get("filename"),
        document_id=payload.get("id") or payload.get("document_id"),
    )
    typed = pipeline.file_pending()
    return {
        "ok": True,
        "tool": "documents.file",
        "count": int(filed.get("count") or 0),
        "files": filed.get("files") or [],
        "folders": tree,
        "typed": typed,
    }


def _folders_ensure(db: Session, payload: dict[str, Any]) -> dict[str, Any]:
    slug = str(payload.get("agent") or payload.get("taxonomist") or "") or None
    return {"ok": True, "tool": "folders.ensure", **library.ensure_tree(db, slug)}


def _folders_list(_db: Session, _: dict[str, Any]) -> dict[str, Any]:
    return {"ok": True, "tool": "folders.list", **library.list_tree()}


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
    from app.services.telegram import poll_updates

    result = poll_updates(pipeline.inbox_dir())
    for item in result.get("saved") or []:
        path = pipeline.inbox_dir() / item["filename"]
        library.register_path(db, path, source="telegram", source_ref=item.get("chat_id") or "")
    if result.get("saved"):
        db.commit()
    return {"ok": result.get("ok", False), "tool": "telegram.poll", **result}


def _telegram_send(_db: Session, payload: dict[str, Any]) -> dict[str, Any]:
    from app.services.telegram import send_message

    text = str(payload.get("text") or payload.get("message") or "")
    result = send_message(text)
    return {"ok": result.get("ok", False), "tool": "telegram.send", **result}


def _teams_send(db: Session, payload: dict[str, Any]) -> dict[str, Any]:
    from app.services.channels import deliver

    text = str(payload.get("text") or payload.get("message") or "")
    result = deliver(db, "teams", text)
    return {"ok": result.get("ok", False), "tool": "teams.send", **result}


def _mail_send(db: Session, payload: dict[str, Any]) -> dict[str, Any]:
    from app.services.channels import deliver

    text = str(payload.get("text") or payload.get("message") or "")
    result = deliver(db, "post", text)
    return {"ok": result.get("ok", False), "tool": "mail.send", **result}


def _review_list(db: Session, _: dict[str, Any]) -> dict[str, Any]:
    from app.services.reviewer import list_exceptions

    return {"ok": True, "tool": "review.list", **list_exceptions(db)}


def _signals_scan(db: Session, payload: dict[str, Any]) -> dict[str, Any]:
    from app.services.sentinel import scan

    letters = payload.get("letters")
    if isinstance(letters, dict):
        letters = [letters]
    result = scan(db, letters if isinstance(letters, list) else None)
    return {"ok": True, "tool": "signals.scan", **result}


def _signals_list(db: Session, _: dict[str, Any]) -> dict[str, Any]:
    from app.services.sentinel import list_signals

    return {"ok": True, "tool": "signals.list", **list_signals(db)}


BUILTIN = {
    "knowledge.search": _search,
    "knowledge.ingest": _ingest,
    "knowledge.promote": _promote,
    "knowledge.graph_build": _graph_build,
    "knowledge.graph_search": _graph_search,
    "documents.list": _list_documents,
    "documents.parse": _parse,
    "documents.read": _read,
    "documents.classify": _classify,
    "documents.chunk": _chunk,
    "documents.file": _file,
    "folders.ensure": _folders_ensure,
    "folders.list": _folders_list,
    "intake.list": _list_inbox,
    "intake.register": _register,
    "intake.poll_mail": _poll_mail,
    "taxonomy.run": _taxonomy_run,
    "taxonomy.list": _taxonomy_list,
    "taxonomy.get": _taxonomy_get,
    "records.extract": _extract,
    "records.list": _list_records,
    "telegram.poll": _telegram_poll,
    "telegram.send": _telegram_send,
    "teams.send": _teams_send,
    "mail.send": _mail_send,
    "review.list": _review_list,
    "signals.scan": _signals_scan,
    "signals.list": _signals_list,
    "models.list": _list_models,
    "platform.explain": _explain,
    "docs.sync": _docs_sync,
}

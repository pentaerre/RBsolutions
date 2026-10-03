from __future__ import annotations

import json
from collections.abc import AsyncIterator

from sqlalchemy.orm import Session

from app.config import settings
from app.runtime.graph import get_compiled_graph
from app.services.llm import stream_llm
from app.services.rag import build_messages, sse


class Orchestrator:
    def __init__(self, db: Session) -> None:
        self._db = db

    async def stream_chat(self, message: str, model: str | None = None) -> AsyncIterator[str]:
        graph = get_compiled_graph()
        state: dict = {"message": message}
        final: dict = {}
        for update in graph.stream(state, {"configurable": {"db": self._db}}):
            for node_name, delta in update.items():
                final.update(delta)
                if node_name == "router":
                    yield sse(
                        {
                            "type": "route",
                            "agent": delta.get("route"),
                            "name": delta.get("agent_name"),
                        }
                    )
                    yield ":" + (" " * 2048) + "\n\n"

        if final.get("error"):
            yield sse({"type": "error", "message": final["error"]})
            yield sse({"type": "done"})
            return

        if final.get("ingest_result"):
            result = final["ingest_result"]
            yield sse({"type": "tool", "slug": result.get("tool"), "ok": True, "result": result})
            yield sse({"type": "token", "content": _summarize_tool(result)})
            yield sse({"type": "done"})
            return

        if final.get("explain_text"):
            yield sse({"type": "tool", "slug": "platform.explain", "ok": True})
            yield sse({"type": "token", "content": final["explain_text"]})
            yield sse({"type": "done"})
            return

        hits = final.get("hits") or []
        yield sse({"type": "tool", "slug": "knowledge.search", "ok": True})
        yield sse(
            {
                "type": "sources",
                "items": [
                    {
                        "filename": hit.get("filename"),
                        "chunk_index": hit.get("chunk_index"),
                        "distance": hit.get("distance"),
                        "entities": hit.get("entities") or [],
                        "via": hit.get("via") or "vector",
                    }
                    for hit in hits
                ],
            }
        )
        yield ":" + (" " * 1024) + "\n\n"
        chosen = model or _agent_model(self._db, final.get("route")) or settings.ollama_chat_model
        yield sse({"type": "model", "name": chosen})
        yield ":" + (" " * 1024) + "\n\n"
        prompt = _librarian_prompt(self._db)
        messages = build_messages(message, hits[:3], system_prompt=prompt)
        try:
            async for token in stream_llm(messages, chosen):
                yield sse({"type": "token", "content": token})
        except Exception as exc:
            yield sse({"type": "error", "message": str(exc)})
        yield sse({"type": "done"})


def _agent_model(db: Session, slug: str | None) -> str:
    from app.db.models import Agent

    if not slug:
        return ""
    row = db.query(Agent).filter(Agent.slug == slug).first()
    return (row.model or "") if row else ""


def _librarian_prompt(db: Session) -> str:
    from app.db.models import Agent

    row = db.query(Agent).filter(Agent.slug == "librarian").first()
    if row and row.system_prompt:
        return row.system_prompt
    return (
        "You are Atrium's librarian. Answer using the provided document excerpts "
        "when they are relevant. If they are not, say so and then use general knowledge. "
        "Cite source filenames. Be concise."
    )


def _summarize_tool(result: dict) -> str:
    tool = result.get("tool")
    if tool == "knowledge.ingest":
        return (
            f"Pipeline finished: {result.get('files', 0)} files, "
            f"{result.get('chunks', 0)} chunks, {result.get('records', 0)} SQL rows."
        )
    if tool == "signals.judge":
        signals = result.get("signals") or []
        if not signals:
            return (
                f"Sentinel classified {result.get('scanned', 0)} letter(s). "
                "No new legal, opportunity, or churn brief."
            )
        lines = [item.get("brief") or "" for item in signals[:6]]
        return (
            f"Sentinel classified {len(signals)} letter(s). "
            "Pathfinder, Recorder, and Reviewer finish the brief from the Brief room.\n"
            + "\n\n".join(lines)
        )
    if tool == "signals.scan":
        signals = result.get("signals") or []
        if not signals:
            return (
                f"Sentinel scanned {result.get('scanned', 0)} letter(s). "
                "No new legal, opportunity, or churn brief."
            )
        from app.services.channels import alarm_text

        lines = [alarm_text(item) for item in signals[:6]]
        channel = result.get("channel") or "courier"
        if result.get("notified"):
            notified = f"Delivered {result.get('notified')} high brief(s) via {channel}."
        else:
            notified = str(result.get("delivery") or f"No delivery on {channel}.")
        return f"Sentinel wrote {len(signals)} brief(s). {notified}\n" + "\n\n".join(lines)
    if tool == "signals.list":
        signals = result.get("signals") or []
        if not signals:
            return "No open briefs. Shared-inbox letters have not raised a signal."
        return f"{len(signals)} open brief(s):\n" + "\n".join(item.get("brief") or "" for item in signals[:8])
    if tool == "intake.poll_mail":
        if not result.get("configured"):
            return str(result.get("message") or "Mailroom is not configured.")
        saved = result.get("saved") or []
        if not saved:
            return "Mailbox checked. No new supported attachments."
        names = ", ".join(item.get("filename", "") for item in saved[:8])
        return f"Downloaded {len(saved)} attachment(s) into inbox: {names}."
    if tool == "intake.list":
        files = result.get("files") or []
        if not files:
            return f"Inbox is empty. Drop PDF/XLSX/PPTX into {result.get('inbox') or 'data/documents/inbox'}."
        names = ", ".join(item.get("filename", "") for item in files[:8])
        return f"{len(files)} file(s) waiting: {names}."
    if tool in {"documents.parse", "documents.classify", "documents.chunk", "documents.file", "records.extract"}:
        files = result.get("files") or []
        extra = []
        if "chunks" in result:
            extra.append(f"{result['chunks']} chunks")
        if "records" in result:
            extra.append(f"{result['records']} SQL rows")
        suffix = f" ({', '.join(extra)})" if extra else ""
        names = ", ".join(item.get("filename", "") for item in files[:8]) or "none"
        return f"{tool} handled {len(files)} file(s){suffix}: {names}."
    if tool == "knowledge.graph_build":
        return f"Graphsmith wrote entities for {result.get('count', 0)} file(s)."
    if tool == "knowledge.graph_search":
        entities = result.get("entities") or []
        if not result.get("enabled", True) and not entities:
            return "Neo4j is off, so Pathfinder has no graph yet."
        if not entities:
            return "No matching entities. Ask Graphsmith to build the knowledge graph after ingest."
        lines = []
        for item in entities[:8]:
            neighbors = ", ".join(item.get("neighbors") or []) or "none"
            files = ", ".join(item.get("files") or []) or "none"
            lines.append(f"{item.get('name')} ({item.get('kind')}): neighbors={neighbors}; files={files}")
        return "Pathfinder (GraphRAG):\n" + "\n".join(lines)
    if tool == "telegram.poll":
        if not result.get("configured"):
            return str(result.get("message") or "Courier is not configured.")
        saved = result.get("saved") or []
        notes = result.get("messages") or []
        return (
            f"Telegram: {len(saved)} file(s) saved, {len(notes)} text message(s). "
            + (", ".join(item.get('filename', '') for item in saved[:6]) or "no files")
        )
    if tool == "telegram.send":
        if not result.get("configured"):
            return str(result.get("message") or "Courier is not configured.")
        return "Telegram message sent." if result.get("ok") else str(result.get("message") or "Send failed.")
    if tool == "review.list":
        items = result.get("items") or []
        if not items:
            return "Reviewer queue is empty. No exceptions need a human."
        return f"{len(items)} exception(s): " + "; ".join(
            f"{item.get('filename')} ({item.get('reason')})" for item in items[:8]
        )
    if tool == "records.list":
        records = result.get("records") or []
        if not records:
            return "No extracted SQL rows yet. Run extract on an invoice or spreadsheet."
        kinds = ", ".join(sorted({item.get("kind", "") for item in records}))
        return f"{len(records)} SQL row(s). Kinds: {kinds}."
    files = result.get("files") or []
    if files:
        names = ", ".join(item.get("filename", "") for item in files[:8])
        return f"{len(files)} file(s): {names}."
    return json.dumps(result, indent=2, default=str)

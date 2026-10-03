"""Pathfinder and Recorder hops for a direction brief.

Pathfinder names a project only when that neighbor is already in Neo4j.
Recorder writes a figure only when that value is already a SQL row.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from sqlalchemy.orm import Session

from app.db.models import OperationalSignal

logger = logging.getLogger("atrium.brief")

LEDGER_HINTS = ("penalty", "penalizacion", "penalización", "contract", "contrato", "clause", "clausula", "cláusula")


def attach_graph(db: Session, ids: list[str] | None = None) -> dict[str, Any]:
    rows = _pending(db, ids, "graph_json")
    crossed = 0
    for row in rows:
        graph = lookup_party(db, row.party)
        clause = graph_clause(row.party, graph)
        if clause:
            row.brief = _append(row.brief, clause)
        row.graph_json = json.dumps(graph, ensure_ascii=False)
        crossed += 1
    db.commit()
    return {"ok": True, "crossed": crossed}


def attach_book(db: Session, ids: list[str] | None = None) -> dict[str, Any]:
    from app.runtime.tools import invoke_tool

    rows = _pending(db, ids, "ledger_json")
    if not rows:
        return {"ok": True, "crossed": 0}
    listed = invoke_tool(db, "records.list", {})
    records = listed.get("records") or []
    crossed = 0
    for row in rows:
        ledger = match_book(records, row.party)
        clause = book_clause(row.party, ledger)
        if clause:
            row.brief = _append(row.brief, clause)
        row.ledger_json = json.dumps(ledger, ensure_ascii=False)
        crossed += 1
    db.commit()
    return {"ok": True, "crossed": crossed}


def lookup_party(db: Session, party: str) -> dict[str, Any]:
    if not party:
        return {"enabled": False, "entities": []}
    try:
        from app.runtime.tools import invoke_tool

        found = invoke_tool(db, "knowledge.graph_search", {"query": party})
    except Exception:
        logger.debug("Pathfinder lookup failed", exc_info=True)
        return {"enabled": False, "entities": []}
    entities = []
    for item in (found.get("entities") or [])[:5]:
        entities.append(
            {
                "name": item.get("name") or "",
                "kind": item.get("kind") or "",
                "neighbors": list(item.get("neighbors") or [])[:8],
                "files": list(item.get("files") or [])[:5],
            }
        )
    return {"enabled": bool(found.get("enabled")), "entities": entities}


def match_book(records: list[dict[str, Any]], party: str) -> list[dict[str, str]]:
    needle = party.strip().lower()
    if len(needle) < 3:
        return []
    found: list[dict[str, str]] = []
    for record in records[:80]:
        payload = record.get("payload")
        if not isinstance(payload, dict):
            continue
        blob = json.dumps(payload, ensure_ascii=False).lower()
        if needle not in blob:
            continue
        hint = ""
        for key, value in payload.items():
            if str(key).lower() in LEDGER_HINTS and value not in (None, ""):
                hint = f"{key}={value}"
                break
        found.append({"kind": str(record.get("kind") or ""), "hint": hint[:160]})
        if len(found) >= 3:
            break
    return found


def graph_clause(party: str, graph: dict[str, Any]) -> str:
    who = party or "remitente desconocido"
    entities = graph.get("entities") or []
    bits = []
    for item in entities[:3]:
        neighbors = [name for name in (item.get("neighbors") or []) if str(name).strip()]
        if not neighbors:
            continue
        label = item.get("name") or who
        bits.append(f"{label} → {', '.join(neighbors)}")
    if bits:
        return "Grafo: " + "; ".join(bits) + "."
    if entities and graph.get("enabled"):
        return f"Grafo: {who}, sin proyecto vecino."
    if graph.get("enabled"):
        return f"El grafo no tiene a {who}."
    return "Sin cruce de grafo (Neo4j apagado)."


def book_clause(party: str, ledger: list[dict[str, str]]) -> str:
    if not ledger:
        return ""
    who = party or "remitente desconocido"
    hints = [item["hint"] for item in ledger if item.get("hint")]
    if hints:
        return "Libro: " + "; ".join(hints) + "."
    return f"Libro: {len(ledger)} fila(s) mencionan a {who}."


def _pending(db: Session, ids: list[str] | None, column: str) -> list[OperationalSignal]:
    rows = (
        db.query(OperationalSignal)
        .filter(OperationalSignal.status == "open")
        .order_by(OperationalSignal.created_at.asc())
        .all()
    )
    wanted = {str(item) for item in ids} if ids else None
    pending: list[OperationalSignal] = []
    for row in rows:
        raw = getattr(row, column) or ""
        if raw not in ("",):
            continue
        if wanted is not None and row.id not in wanted:
            continue
        pending.append(row)
    return pending


def _append(brief: str, clause: str) -> str:
    text = (brief or "").rstrip()
    extra = clause.strip()
    if not extra:
        return text
    if extra in text:
        return text
    return f"{text} {extra}".strip()

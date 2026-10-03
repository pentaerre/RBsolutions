"""Sentinel — briefs for direction from shared inboxes.

Mailroom stores the letter. This oficio decides whether direction should see it,
then crosses the party with Neo4j and the SQL ledger. It does not answer the
employee who received the mail, and it does not call the 32b model.
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
import unicodedata
from datetime import datetime
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from app.config import settings
from app.db.models import ExtractedRecord, MailboxLetter, OperationalSignal

logger = logging.getLogger("atrium.sentinel")

KINDS = ("legal", "opportunity", "churn")
SEVERITY_RANK = {"high": 3, "medium": 2, "low": 1}
KIND_RANK = {"churn": 3, "legal": 2, "opportunity": 1}

# Folded (no accents). First match inside a kind wins; the strongest kind wins overall.
RULES: dict[str, list[tuple[str, str]]] = {
    "legal": [
        ("responsabilidad ilimitada", "high"),
        ("unlimited liability", "high"),
        ("penalizacion no estandar", "high"),
        ("non-standard penalty", "high"),
        ("clausula penal", "medium"),
        ("penalty clause", "medium"),
    ],
    "opportunity": [
        ("tambien haceis", "medium"),
        ("vosotros tambien", "medium"),
        ("do you also", "medium"),
        ("auditoria iso", "medium"),
        ("ampliacion de servicio", "medium"),
        ("presupuesto para", "medium"),
    ],
    "churn": [
        ("tercera vez", "high"),
        ("departamento legal", "high"),
        ("cancelacion", "high"),
        ("me doy de baja", "high"),
        ("se va a retrasar", "high"),
        ("retraso de dos semanas", "high"),
        ("delivery will be delayed", "high"),
        ("inaceptable", "medium"),
    ],
}

LEDGER_HINTS = ("penalty", "penalizacion", "penalización", "contract", "contrato", "clause", "clausula", "cláusula")
FREE_HOSTS = {"gmail", "outlook", "hotmail", "yahoo", "mail", "googlemail"}


def signals_drop() -> Path:
    root = Path(settings.documents_dir).resolve()
    path = root / "signals-drop"
    path.mkdir(parents=True, exist_ok=True)
    return path


def classify_letter(sender: str, subject: str, body: str) -> dict[str, str] | None:
    """Deterministic JSON-shaped pass. Same contract a local model would return."""
    folded = _fold(f"{subject}\n{body}")
    best: dict[str, str] | None = None
    for kind, rules in RULES.items():
        for phrase, severity in rules:
            if phrase in folded:
                candidate = {"kind": kind, "severity": severity, "evidence": phrase, "party": party_of(sender, body)}
                if best is None or _outranks(candidate, best):
                    best = candidate
                break
    return best


def party_of(sender: str, body: str) -> str:
    raw = sender or ""
    name = raw.split("<")[0].strip().strip('"')
    if name and "@" not in name and name.lower() not in {"noreply", "no-reply"}:
        return name[:120]
    match = re.search(r"[\w.+-]+@([A-Za-z0-9.-]+)", raw)
    if match:
        label = match.group(1).lower().split(".")[0]
        if label not in FREE_HOSTS:
            return label[:120]
    found = re.search(r"\b(?:proveedor|cliente|supplier)\s+([A-ZÁÉÍÓÚÑ][\w&.-]{1,40})", body or "")
    if found:
        return found.group(1)[:120]
    return name[:120]


def store_letters(db: Session, letters: list[dict[str, Any]] | None) -> int:
    added = 0
    for raw in letters or []:
        key = message_key(raw)
        exists = db.query(MailboxLetter).filter(MailboxLetter.message_key == key).first()
        if exists:
            continue
        db.add(
            MailboxLetter(
                message_key=key,
                mailbox=str(raw.get("mailbox") or "INBOX")[:120],
                sender=str(raw.get("sender") or raw.get("from") or "")[:300],
                subject=str(raw.get("subject") or "")[:400],
                body=str(raw.get("body") or "")[:8000],
                received_at=parse_when(raw.get("received_at")),
                scanned=0,
            )
        )
        added += 1
    if added:
        db.flush()
    return added


def scan(db: Session, letters: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    from app.services.knobs import agent_config

    cfg = agent_config(db, "sentinel")
    allowed = _mailboxes(cfg)
    enabled = _enabled(cfg)
    stale_hours = _stale_hours(cfg)
    stored = store_letters(db, letters)
    stored += _ingest_drop(db)
    pending = (
        db.query(MailboxLetter)
        .filter(MailboxLetter.scanned == 0)
        .order_by(MailboxLetter.created_at.asc())
        .all()
    )
    created: list[dict[str, Any]] = []
    for letter in pending:
        letter.scanned = 1
        if letter.mailbox.strip().lower() not in allowed:
            continue
        hit = classify_letter(letter.sender, letter.subject, letter.body)
        if hit is None or hit["kind"] not in enabled:
            continue
        age = _age_hours(letter.received_at)
        severity = hit["severity"]
        if hit["kind"] == "opportunity" and age is not None and age >= stale_hours:
            severity = "high"
        graph = cross_graph(hit["party"])
        ledger = cross_ledger(db, hit["party"])
        brief = render_brief(
            kind=hit["kind"],
            severity=severity,
            party=hit["party"],
            subject=letter.subject,
            evidence=hit["evidence"],
            graph=graph,
            ledger=ledger,
            age_hours=age if severity == "high" and hit["kind"] == "opportunity" else None,
            stale_hours=stale_hours,
        )
        row = OperationalSignal(
            letter_id=letter.id,
            kind=hit["kind"],
            severity=severity,
            party=hit["party"],
            evidence=hit["evidence"],
            brief=brief,
            graph_json=json.dumps(graph, ensure_ascii=False),
            ledger_json=json.dumps(ledger, ensure_ascii=False),
            status="open",
            notified=0,
        )
        db.add(row)
        db.flush()
        created.append(_signal_dict(row, letter.subject, letter.sender))
    notified, channel, delivery = _notify_new(db, created)
    db.commit()
    return {
        "ok": True,
        "stored": stored,
        "scanned": len(pending),
        "created": len(created),
        "notified": notified,
        "channel": channel,
        "delivery": delivery,
        "signals": created,
        "open": list_signals(db).get("signals") or [],
    }


def list_signals(db: Session, limit: int = 40) -> dict[str, Any]:
    rows = (
        db.query(OperationalSignal)
        .filter(OperationalSignal.status == "open")
        .order_by(OperationalSignal.created_at.desc())
        .limit(limit)
        .all()
    )
    signals = [
        _signal_dict(row, row.letter.subject if row.letter else "", row.letter.sender if row.letter else "")
        for row in rows
    ]
    return {"ok": True, "count": len(signals), "signals": signals}


def cross_graph(party: str) -> dict[str, Any]:
    if not party:
        return {"enabled": False, "entities": []}
    try:
        from app.services.graphstore import get_graphstore

        result = get_graphstore().entity_search(party)
    except Exception:
        logger.debug("Graph cross failed", exc_info=True)
        return {"enabled": False, "entities": []}
    entities = []
    for item in (result.get("entities") or [])[:5]:
        entities.append(
            {
                "name": item.get("name") or "",
                "kind": item.get("kind") or "",
                "neighbors": list(item.get("neighbors") or [])[:8],
                "files": list(item.get("files") or [])[:5],
            }
        )
    return {"enabled": bool(result.get("enabled")), "entities": entities}


def cross_ledger(db: Session, party: str) -> list[dict[str, str]]:
    needle = party.strip().lower()
    if len(needle) < 3:
        return []
    found: list[dict[str, str]] = []
    rows = db.query(ExtractedRecord).order_by(ExtractedRecord.created_at.desc()).limit(80).all()
    for row in rows:
        try:
            payload = json.loads(row.payload_json or "{}")
        except json.JSONDecodeError:
            continue
        blob = json.dumps(payload, ensure_ascii=False).lower()
        if needle not in blob:
            continue
        hint = ""
        if isinstance(payload, dict):
            for key, value in payload.items():
                if str(key).lower() in LEDGER_HINTS and value not in (None, ""):
                    hint = f"{key}={value}"
                    break
        found.append({"kind": row.kind, "hint": hint[:160]})
        if len(found) >= 3:
            break
    return found


def render_brief(
    *,
    kind: str,
    severity: str,
    party: str,
    subject: str,
    evidence: str,
    graph: dict[str, Any],
    ledger: list[dict[str, str]],
    age_hours: float | None,
    stale_hours: int,
) -> str:
    titles = {
        "legal": "Riesgo legal",
        "opportunity": "Oportunidad",
        "churn": "Riesgo de cliente",
    }
    level = {"high": "alto", "medium": "medio", "low": "bajo"}.get(severity, severity)
    who = party or "remitente desconocido"
    title = subject.strip() or "(sin asunto)"
    parts = [f"{titles.get(kind, kind)} {level}: {who} en «{title}». Señal: «{evidence}»."]
    if age_hours is not None and kind == "opportunity":
        parts.append(f"Lleva más de {stale_hours} h sin atención.")
    entities = graph.get("entities") or []
    if entities:
        bits = []
        for item in entities[:3]:
            neighbors = ", ".join(item.get("neighbors") or [])
            label = item.get("name") or who
            bits.append(f"{label} → {neighbors}" if neighbors else label)
        parts.append("Grafo: " + "; ".join(bits) + ".")
    elif graph.get("enabled"):
        parts.append(f"El grafo no tiene a {who}.")
    else:
        parts.append("Sin cruce de grafo (Neo4j apagado).")
    if ledger:
        hints = [item["hint"] for item in ledger if item.get("hint")]
        if hints:
            parts.append("Libro: " + "; ".join(hints) + ".")
        else:
            parts.append(f"Libro: {len(ledger)} fila(s) mencionan a {who}.")
    return " ".join(parts)


def message_key(raw: dict[str, Any]) -> str:
    explicit = str(raw.get("message_id") or raw.get("message_key") or "").strip()
    if explicit:
        basis = explicit
    else:
        basis = "|".join(
            [
                str(raw.get("mailbox") or "INBOX"),
                str(raw.get("sender") or raw.get("from") or ""),
                str(raw.get("subject") or ""),
                str(raw.get("body") or "")[:400],
            ]
        )
    return hashlib.sha256(basis.encode("utf-8", errors="ignore")).hexdigest()[:40]


def parse_when(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        return value.replace(tzinfo=None)
    text = str(value or "").strip()
    if not text:
        return None
    try:
        return parsedate_to_datetime(text).replace(tzinfo=None)
    except (TypeError, ValueError, IndexError, OverflowError):
        pass
    try:
        return datetime.fromisoformat(text.replace("Z", ""))
    except ValueError:
        return None


def _ingest_drop(db: Session) -> int:
    folder = signals_drop()
    added = 0
    seen = folder / "seen"
    for path in sorted(folder.glob("*.json")):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            logger.warning("Skipping unreadable signal drop %s", path.name)
            continue
        letters = payload if isinstance(payload, list) else [payload]
        added += store_letters(db, [item for item in letters if isinstance(item, dict)])
        seen.mkdir(parents=True, exist_ok=True)
        target = seen / path.name
        if target.exists():
            target = seen / f"{path.stem}-{message_key({'message_id': path.name})}{path.suffix}"
        path.replace(target)
    return added


def _notify_new(db: Session, created: list[dict[str, Any]]) -> tuple[int, str, str]:
    from app.services.channels import alarm_text, deliver
    from app.services.knobs import agent_config

    channel = str(agent_config(db, "sentinel").get("notify") or "courier")
    highs = [item for item in created if item.get("severity") == "high"]
    if not highs:
        return 0, channel, ""
    text = "Sentinel\n\n" + "\n\n".join(alarm_text(item) for item in highs[:8])
    result = deliver(db, channel, text)
    if not result.get("ok"):
        return 0, channel, str(result.get("message") or "")
    ids = [item["id"] for item in highs if item.get("id")]
    if ids:
        db.query(OperationalSignal).filter(OperationalSignal.id.in_(ids)).update(
            {OperationalSignal.notified: 1},
            synchronize_session=False,
        )
    return len(ids), channel, ""


def _signal_dict(row: OperationalSignal, subject: str, sender: str = "") -> dict[str, Any]:
    try:
        graph = json.loads(row.graph_json or "{}")
    except json.JSONDecodeError:
        graph = {}
    try:
        ledger = json.loads(row.ledger_json or "[]")
    except json.JSONDecodeError:
        ledger = []
    return {
        "id": row.id,
        "kind": row.kind,
        "severity": row.severity,
        "party": row.party,
        "subject": subject,
        "sender": sender,
        "evidence": row.evidence,
        "brief": row.brief,
        "status": row.status,
        "notified": bool(row.notified),
        "graph": graph,
        "ledger": ledger,
    }


def _mailboxes(cfg: dict[str, Any]) -> set[str]:
    raw = str(cfg.get("mailboxes") or "INBOX")
    names = {part.strip().lower() for part in raw.split(",") if part.strip()}
    return names or {"inbox"}


def _enabled(cfg: dict[str, Any]) -> set[str]:
    raw = str(cfg.get("signals") or ",".join(KINDS))
    found = {part.strip().lower() for part in raw.split(",") if part.strip() in KINDS}
    return found or set(KINDS)


def _stale_hours(cfg: dict[str, Any]) -> int:
    try:
        hours = int(cfg.get("stale_hours") or 24)
    except (TypeError, ValueError):
        hours = 24
    return max(1, min(hours, 24 * 30))


def _age_hours(when: datetime | None) -> float | None:
    if when is None:
        return None
    return (datetime.utcnow() - when).total_seconds() / 3600


def _outranks(candidate: dict[str, str], current: dict[str, str]) -> bool:
    rank = (SEVERITY_RANK[candidate["severity"]], KIND_RANK[candidate["kind"]])
    other = (SEVERITY_RANK[current["severity"]], KIND_RANK[current["kind"]])
    return rank > other


def _fold(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text.lower())
    return "".join(char for char in normalized if not unicodedata.combining(char))


def sentinel_poll_seconds(db: Session | None = None) -> int:
    from app.services.knobs import agent_config

    own = db is None
    if own:
        from app.db.session import SessionLocal

        db = SessionLocal()
    try:
        cfg = agent_config(db, "sentinel")
        try:
            return max(0, int(cfg.get("poll_seconds") or 0))
        except (TypeError, ValueError):
            return 0
    finally:
        if own and db is not None:
            db.close()

"""Sentinel — classifies a shared-inbox letter.

Mailroom stores the letter. This oficio only decides legal, opportunity, or churn
and writes the brief with subject and sender. Pathfinder crosses Neo4j, Recorder
reads the SQL book, Reviewer holds the exception, and the channel agent notifies.
It does not answer the employee who received the mail, and it does not call the 32b model.
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
from app.db.models import MailboxLetter, OperationalSignal

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


def judge(db: Session) -> dict[str, Any]:
    """Classify stored letters. Does not read the graph, the book, or a channel."""
    from app.services.knobs import agent_config

    cfg = agent_config(db, "sentinel")
    allowed = _mailboxes(cfg)
    enabled = _enabled(cfg)
    stale_hours = _stale_hours(cfg)
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
        brief = render_judgment(
            kind=hit["kind"],
            severity=severity,
            party=hit["party"],
            subject=letter.subject,
            evidence=hit["evidence"],
            sender=letter.sender,
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
            graph_json="",
            ledger_json="",
            status="open",
            notified=0,
        )
        db.add(row)
        db.flush()
        created.append(signal_dict(row))
    db.commit()
    return {
        "ok": True,
        "scanned": len(pending),
        "created": len(created),
        "signals": created,
    }


def scan(db: Session, letters: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    """Brief line: each oficio is another agent's tool. Sentinel only judges."""
    from app.services.brief_line import run_line

    return run_line(db, letters)


def list_signals(db: Session, limit: int = 40) -> dict[str, Any]:
    rows = (
        db.query(OperationalSignal)
        .filter(OperationalSignal.status == "open")
        .order_by(OperationalSignal.created_at.desc())
        .limit(limit)
        .all()
    )
    signals = [
        signal_dict(row)
        for row in rows
    ]
    return {"ok": True, "count": len(signals), "signals": signals}


def render_judgment(
    *,
    kind: str,
    severity: str,
    party: str,
    subject: str,
    evidence: str,
    sender: str,
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
    who_sent = (sender or "").strip() or "desconocido"
    parts = [f"{titles.get(kind, kind)} {level}: {who} en «{title}». Señal: «{evidence}». De: {who_sent}"]
    if age_hours is not None and kind == "opportunity":
        parts.append(f"Lleva más de {stale_hours} h sin atención.")
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


def ingest_drop(db: Session) -> int:
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


def signal_dict(row: OperationalSignal) -> dict[str, Any]:
    subject = row.letter.subject if row.letter else ""
    sender = row.letter.sender if row.letter else ""
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

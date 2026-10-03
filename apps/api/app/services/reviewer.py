from __future__ import annotations

import json
from typing import Any

from sqlalchemy.orm import Session

from app.db.models import ExtractedRecord, IntakeDocument, OperationalSignal


def list_exceptions(db: Session) -> dict[str, Any]:
    items: list[dict[str, Any]] = []
    for row in db.query(IntakeDocument).order_by(IntakeDocument.updated_at.desc()).limit(50).all():
        if row.status == "error":
            items.append(_item(row.filename, "ingest_error", row.error or "processing failed"))
        elif row.doc_type == "other":
            items.append(_item(row.filename, "unclassified", "Triage could not assign a business type"))
    for rec in db.query(ExtractedRecord).order_by(ExtractedRecord.created_at.desc()).limit(50).all():
        payload = json.loads(rec.payload_json or "{}")
        if rec.kind == "invoice" and not payload.get("invoice_number"):
            filename = rec.document.filename if rec.document else ""
            items.append(_item(filename, "weak_invoice", "Invoice row has no invoice_number"))
    items.extend(hold_signals(db).get("items") or [])
    return {"ok": True, "count": len(items), "items": items[:40]}


def hold_signals(db: Session) -> dict[str, Any]:
    """Keep open briefs for a person. The sender stays on the exception."""
    items: list[dict[str, str]] = []
    signals = (
        db.query(OperationalSignal)
        .filter(OperationalSignal.status == "open")
        .order_by(OperationalSignal.created_at.desc())
        .limit(40)
        .all()
    )
    for signal in signals:
        subject = signal.letter.subject if signal.letter else signal.party
        sender = (signal.letter.sender if signal.letter else "") or ""
        detail = f"De: {sender}\n{signal.brief}" if sender else signal.brief
        items.append(_item(subject or signal.party or "signal", f"signal_{signal.kind}", detail))
    return {"ok": True, "count": len(items), "items": items}


def _item(filename: str, reason: str, detail: str) -> dict[str, str]:
    return {"filename": filename, "reason": reason, "detail": detail, "status": "pending"}

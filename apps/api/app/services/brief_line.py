"""Brief line. Each hop is another agent's tool. This module only calls them."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.db.models import OperationalSignal

CHANNEL_TOOL = {
    "courier": "telegram.send",
    "teams": "teams.send",
    "post": "mail.send",
}


def run_line(db: Session, letters: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    from app.runtime.tools import invoke_tool
    from app.services.sentinel import list_signals, signal_dict

    stored = invoke_tool(db, "intake.store_letters", {"letters": letters or []})
    judged = invoke_tool(db, "signals.judge", {})
    ids = [item["id"] for item in judged.get("signals") or [] if item.get("id")]
    invoke_tool(db, "signals.graph", {"ids": ids})
    invoke_tool(db, "signals.book", {"ids": ids})
    invoke_tool(db, "review.hold", {"ids": ids})
    notified = invoke_tool(db, "signals.notify", {"ids": ids})
    final: list[dict[str, Any]] = []
    if ids:
        rows = db.query(OperationalSignal).filter(OperationalSignal.id.in_(ids)).all()
        order = {item_id: index for index, item_id in enumerate(ids)}
        rows.sort(key=lambda row: order.get(row.id, 0))
        final = [signal_dict(row) for row in rows]
    return {
        "ok": True,
        "stored": int(stored.get("stored") or 0),
        "scanned": int(judged.get("scanned") or 0),
        "created": int(judged.get("created") or 0),
        "notified": int(notified.get("notified") or 0),
        "channel": str(notified.get("channel") or ""),
        "delivery": str(notified.get("delivery") or ""),
        "signals": final,
        "open": list_signals(db).get("signals") or [],
    }


def notify_signals(db: Session, ids: list[str] | None) -> dict[str, Any]:
    from app.runtime.tools import invoke_tool
    from app.services.channels import alarm_text
    from app.services.knobs import agent_config

    channel = str(agent_config(db, "sentinel").get("notify") or "courier")
    if channel not in CHANNEL_TOOL:
        channel = "courier"
    if not ids:
        return {"ok": True, "notified": 0, "channel": channel, "delivery": ""}
    rows = (
        db.query(OperationalSignal)
        .filter(
            OperationalSignal.id.in_(ids),
            OperationalSignal.severity == "high",
            OperationalSignal.notified == 0,
            OperationalSignal.status == "open",
        )
        .all()
    )
    if not rows:
        return {"ok": True, "notified": 0, "channel": channel, "delivery": ""}
    parts = []
    for row in rows[:8]:
        subject = row.letter.subject if row.letter else ""
        sender = row.letter.sender if row.letter else ""
        parts.append(alarm_text({"subject": subject, "sender": sender, "brief": row.brief}))
    result = invoke_tool(db, CHANNEL_TOOL[channel], {"text": "Sentinel\n\n" + "\n\n".join(parts)})
    if not result.get("ok"):
        return {
            "ok": True,
            "notified": 0,
            "channel": channel,
            "delivery": str(result.get("message") or ""),
        }
    for row in rows:
        row.notified = 1
    db.commit()
    return {"ok": True, "notified": len(rows), "channel": channel, "delivery": ""}

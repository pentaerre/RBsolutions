"""Channel workers that deliver a Sentinel brief.

Courier (Telegram) is the worker in use. Teams and Post are the same job on
another channel: parked until someone enables that agent and sets the secret
in the environment. Secrets never go on the graph.
"""

from __future__ import annotations

import smtplib
from email.message import EmailMessage
from typing import Any

import httpx
from sqlalchemy.orm import Session

from app.config import settings
from app.db.models import Agent


WORKERS = ("courier", "teams", "post")


def alarm_text(item: dict[str, Any]) -> str:
    subject = str(item.get("subject") or "").strip() or "(sin asunto)"
    sender = str(item.get("sender") or "").strip() or "desconocido"
    brief = str(item.get("brief") or "").strip()
    lines = [f"Asunto: {subject}", f"De: {sender}"]
    if brief:
        lines.append(brief)
    return "\n".join(lines)


def deliver(db: Session, channel: str, text: str) -> dict[str, Any]:
    chosen = channel if channel in WORKERS else "courier"
    agent = db.query(Agent).filter(Agent.slug == chosen).first()
    if agent is None or agent.status != "live":
        name = agent.name if agent else chosen
        return {
            "ok": False,
            "configured": False,
            "channel": chosen,
            "message": (
                f"{name} is parked. Enable that worker in Admin before Sentinel delivers there. "
                "Courier is the Telegram chatbot in use."
            ),
        }
    if chosen == "teams":
        return send_teams(text)
    if chosen == "post":
        return send_post(text)
    from app.services.telegram import send_message

    result = send_message(text)
    result["channel"] = "courier"
    return result


def send_teams(text: str) -> dict[str, Any]:
    url = (settings.teams_webhook_url or "").strip()
    if not url:
        return {
            "ok": False,
            "configured": False,
            "channel": "teams",
            "message": "Teams worker has no webhook. Set TEAMS_WEBHOOK_URL. The secret stays off the graph.",
        }
    body = text[:3900]
    response = httpx.post(
        url,
        json={
            "text": body,
            "attachments": [
                {
                    "contentType": "application/vnd.microsoft.card.adaptive",
                    "content": {
                        "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
                        "type": "AdaptiveCard",
                        "version": "1.4",
                        "body": [{"type": "TextBlock", "text": body, "wrap": True}],
                    },
                }
            ],
        },
        timeout=20.0,
    )
    return {"ok": response.status_code < 300, "configured": True, "channel": "teams", "status_code": response.status_code}


def send_post(text: str) -> dict[str, Any]:
    host = (settings.smtp_host or "").strip()
    target = (settings.smtp_to or "").strip()
    if not host or not target:
        return {
            "ok": False,
            "configured": False,
            "channel": "post",
            "message": "Post worker has no mailbox binding. Set SMTP_HOST and SMTP_TO. The secret stays off the graph.",
        }
    message = EmailMessage()
    message["Subject"] = "Sentinel"
    message["From"] = (settings.smtp_from or settings.smtp_user or "sentinel@localhost").strip()
    message["To"] = target
    message.set_content(text[:8000])
    with smtplib.SMTP(host, int(settings.smtp_port or 587), timeout=20) as client:
        if int(settings.smtp_port or 587) != 25:
            client.starttls()
        if settings.smtp_user:
            client.login(settings.smtp_user, settings.smtp_password)
        client.send_message(message)
    return {"ok": True, "configured": True, "channel": "post"}

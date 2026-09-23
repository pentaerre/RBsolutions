from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import httpx

from app.config import settings
from app.services.parsers import SUPPORTED_SUFFIXES

logger = logging.getLogger("atrium.courier")
API = "https://api.telegram.org"


def telegram_configured() -> bool:
    return bool(settings.telegram_bot_token)


def send_message(text: str, chat_id: str | None = None) -> dict[str, Any]:
    if not telegram_configured():
        return {
            "ok": False,
            "configured": False,
            "message": "Courier is not configured. Set TELEGRAM_BOT_TOKEN (and TELEGRAM_CHAT_ID to notify).",
        }
    target = chat_id or settings.telegram_chat_id
    if not target:
        return {"ok": False, "configured": True, "message": "No chat id. Write the bot once, or set TELEGRAM_CHAT_ID."}
    response = httpx.post(
        f"{API}/bot{settings.telegram_bot_token}/sendMessage",
        json={"chat_id": target, "text": text[:3900]},
        timeout=20.0,
    )
    body = response.json() if response.content else {}
    return {"ok": bool(body.get("ok")), "configured": True, "result": body}


def poll_updates(dest: Path) -> dict[str, Any]:
    dest = Path(dest)
    dest.mkdir(parents=True, exist_ok=True)
    if not telegram_configured():
        return {
            "ok": False,
            "configured": False,
            "saved": [],
            "messages": [],
            "message": "Courier is not configured. Set TELEGRAM_BOT_TOKEN.",
        }
    response = httpx.get(
        f"{API}/bot{settings.telegram_bot_token}/getUpdates",
        params={"timeout": 0, "limit": 20},
        timeout=25.0,
    )
    payload = response.json() if response.content else {}
    if not payload.get("ok"):
        return {"ok": False, "configured": True, "saved": [], "messages": [], "message": str(payload)}
    saved: list[dict[str, str]] = []
    messages: list[dict[str, str]] = []
    last_id = 0
    for update in payload.get("result") or []:
        last_id = max(last_id, int(update.get("update_id") or 0))
        note = update.get("message") or update.get("channel_post") or {}
        chat_id = str((note.get("chat") or {}).get("id") or "")
        if note.get("text"):
            messages.append({"chat_id": chat_id, "text": note["text"]})
        for key in ("document", "audio"):
            blob = note.get(key)
            if not blob:
                continue
            filename = blob.get("file_name") or f"{blob.get('file_id')}.bin"
            if Path(filename).suffix.lower() not in SUPPORTED_SUFFIXES:
                continue
            raw = _download_file(blob["file_id"])
            if not raw:
                continue
            target = dest / Path(filename).name
            target.write_bytes(raw)
            saved.append({"filename": target.name, "chat_id": chat_id})
    if last_id:
        httpx.get(
            f"{API}/bot{settings.telegram_bot_token}/getUpdates",
            params={"offset": last_id + 1, "timeout": 0},
            timeout=15.0,
        )
    return {"ok": True, "configured": True, "saved": saved, "messages": messages, "count": len(saved)}


def _download_file(file_id: str) -> bytes:
    meta = httpx.get(
        f"{API}/bot{settings.telegram_bot_token}/getFile",
        params={"file_id": file_id},
        timeout=20.0,
    ).json()
    path = ((meta.get("result") or {}).get("file_path")) if meta.get("ok") else None
    if not path:
        return b""
    response = httpx.get(f"{API}/file/bot{settings.telegram_bot_token}/{path}", timeout=60.0)
    response.raise_for_status()
    return response.content

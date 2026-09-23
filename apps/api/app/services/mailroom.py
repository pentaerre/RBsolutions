from __future__ import annotations

import email
import imaplib
import logging
from email.header import decode_header
from pathlib import Path
from typing import Any

from app.config import settings
from app.services.parsers import SUPPORTED_SUFFIXES

logger = logging.getLogger("atrium.mailroom")


def mail_configured() -> bool:
    return bool(settings.imap_host and settings.imap_user and settings.imap_password)


def poll_mailbox(dest: Path) -> dict[str, Any]:
    dest = Path(dest)
    dest.mkdir(parents=True, exist_ok=True)
    if not mail_configured():
        return {
            "ok": False,
            "configured": False,
            "saved": [],
            "message": "IMAP is not configured. Set IMAP_HOST, IMAP_USER, IMAP_PASSWORD to let Mailroom download attachments.",
        }

    saved: list[dict[str, str]] = []
    client = imaplib.IMAP4_SSL(settings.imap_host, settings.imap_port)
    try:
        client.login(settings.imap_user, settings.imap_password)
        client.select(settings.imap_folder)
        status, message_ids = client.search(None, "(UNSEEN)")
        if status != "OK":
            return {"ok": False, "configured": True, "saved": [], "message": "IMAP search failed"}
        for raw_id in (message_ids[0] or b"").split():
            status, payload = client.fetch(raw_id, "(RFC822)")
            if status != "OK" or not payload or not payload[0]:
                continue
            message = email.message_from_bytes(payload[0][1])
            sender = str(message.get("From") or "")
            subject = _decode(message.get("Subject"))
            for filename, data in _iter_attachments(message):
                suffix = Path(filename).suffix.lower()
                if suffix not in SUPPORTED_SUFFIXES:
                    continue
                target = _unique_path(dest, filename)
                target.write_bytes(data)
                saved.append(
                    {
                        "filename": target.name,
                        "from": sender,
                        "subject": subject,
                    }
                )
            client.store(raw_id, "+FLAGS", "\\Seen")
    finally:
        try:
            client.logout()
        except Exception:
            logger.debug("IMAP logout failed", exc_info=True)
    return {"ok": True, "configured": True, "saved": saved, "count": len(saved)}


def _iter_attachments(message: email.message.Message):
    for part in message.walk():
        disposition = str(part.get("Content-Disposition") or "")
        filename = part.get_filename()
        if not filename and "attachment" not in disposition.lower():
            continue
        filename = _decode(filename) or "attachment.bin"
        payload = part.get_payload(decode=True)
        if payload:
            yield filename, payload


def _decode(value: str | None) -> str:
    if not value:
        return ""
    parts = decode_header(value)
    chunks: list[str] = []
    for data, encoding in parts:
        if isinstance(data, bytes):
            chunks.append(data.decode(encoding or "utf-8", errors="ignore"))
        else:
            chunks.append(data)
    return "".join(chunks)


def _unique_path(folder: Path, filename: str) -> Path:
    target = folder / Path(filename).name
    if not target.exists():
        return target
    stem, suffix = target.stem, target.suffix
    index = 2
    while True:
        candidate = folder / f"{stem}-{index}{suffix}"
        if not candidate.exists():
            return candidate
        index += 1

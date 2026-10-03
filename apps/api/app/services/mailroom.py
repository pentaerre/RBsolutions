from __future__ import annotations

import email
import imaplib
import logging
import re
from email.header import decode_header
from pathlib import Path
from typing import Any

from app.config import settings
from app.services.parsers import SUPPORTED_SUFFIXES

logger = logging.getLogger("atrium.mailroom")


def mail_configured() -> bool:
    return bool(settings.imap_host and settings.imap_user and settings.imap_password)


def poll_mailbox(dest: Path, folder: str | None = None) -> dict[str, Any]:
    dest = Path(dest)
    dest.mkdir(parents=True, exist_ok=True)
    if not mail_configured():
        return {
            "ok": False,
            "configured": False,
            "saved": [],
            "letters": [],
            "message": "IMAP is not configured. Set IMAP_HOST, IMAP_USER, IMAP_PASSWORD to let Mailroom download attachments.",
        }

    mailbox = folder or settings.imap_folder
    saved: list[dict[str, str]] = []
    letters: list[dict[str, str]] = []
    client = imaplib.IMAP4_SSL(settings.imap_host, settings.imap_port)
    try:
        client.login(settings.imap_user, settings.imap_password)
        client.select(mailbox)
        status, message_ids = client.search(None, "(UNSEEN)")
        if status != "OK":
            return {"ok": False, "configured": True, "saved": [], "letters": [], "message": "IMAP search failed"}
        for raw_id in (message_ids[0] or b"").split():
            status, payload = client.fetch(raw_id, "(RFC822)")
            if status != "OK" or not payload or not payload[0]:
                continue
            message = email.message_from_bytes(payload[0][1])
            sender = str(message.get("From") or "")
            subject = _decode(message.get("Subject"))
            letters.append(
                {
                    "message_id": _decode(message.get("Message-ID")) or raw_id.decode(errors="ignore"),
                    "mailbox": mailbox,
                    "sender": sender,
                    "subject": subject,
                    "body": _body_text(message),
                    "received_at": str(message.get("Date") or ""),
                }
            )
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
    return {"ok": True, "configured": True, "saved": saved, "letters": letters, "count": len(saved)}


def _body_text(message: email.message.Message) -> str:
    chunks: list[str] = []
    if message.is_multipart():
        for part in message.walk():
            if part.get_content_maintype() == "multipart":
                continue
            disposition = str(part.get("Content-Disposition") or "").lower()
            if disposition.startswith("attachment"):
                continue
            if part.get_content_type() not in {"text/plain", "text/html"}:
                continue
            payload = part.get_payload(decode=True)
            if not payload:
                continue
            charset = part.get_content_charset() or "utf-8"
            text = payload.decode(charset, errors="ignore")
            if part.get_content_type() == "text/html":
                text = re.sub(r"<[^>]+>", " ", text)
            chunks.append(text)
            if part.get_content_type() == "text/plain":
                break
    else:
        payload = message.get_payload(decode=True)
        if isinstance(payload, bytes):
            chunks.append(payload.decode(message.get_content_charset() or "utf-8", errors="ignore"))
        elif isinstance(payload, str):
            chunks.append(payload)
    return re.sub(r"\s+", " ", " ".join(chunks)).strip()[:8000]


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

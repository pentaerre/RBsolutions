from __future__ import annotations

import logging
import time
from threading import Event, Thread

from app.db.session import SessionLocal
from app.services import knobs, library, pipeline
from app.services.mailroom import poll_mailbox
from app.services.sentinel import scan, sentinel_poll_seconds, store_letters
from app.services.taxonomy import cadence_seconds, list_agents as list_taxonomists, load_config

logger = logging.getLogger("atrium.scheduler")

_stop = Event()


def start_scheduler() -> Event:
    _stop.clear()
    Thread(target=_mail_loop, name="atrium-mail", daemon=True).start()
    Thread(target=_sentinel_loop, name="atrium-sentinel", daemon=True).start()
    Thread(target=_taxonomy_loop, name="atrium-taxonomy", daemon=True).start()
    return _stop


def stop_scheduler() -> None:
    _stop.set()


def _mail_loop() -> None:
    last = 0.0
    while not _stop.is_set():
        interval = knobs.mailroom_poll_seconds()
        now = time.time()
        if interval > 0 and (last == 0 or now - last >= interval):
            try:
                dest = pipeline.inbox_dir()
                result = poll_mailbox(dest, folder=knobs.mailroom_folder())
                db = SessionLocal()
                try:
                    for item in result.get("saved") or []:
                        path = dest / item["filename"]
                        library.register_path(db, path, source="email", source_ref=item.get("subject") or "")
                    stored = store_letters(db, result.get("letters") or [])
                    if result.get("saved") or stored:
                        db.commit()
                finally:
                    db.close()
            except Exception:
                logger.exception("Mailroom poll failed")
            last = now
        if _stop.wait(5):
            return


def _sentinel_loop() -> None:
    last = 0.0
    while not _stop.is_set():
        interval = sentinel_poll_seconds()
        now = time.time()
        if interval > 0 and (last == 0 or now - last >= interval):
            db = SessionLocal()
            try:
                scan(db)
                logger.info("Sentinel scan finished")
            except Exception:
                logger.exception("Sentinel scan failed")
            finally:
                db.close()
            last = now
        if _stop.wait(5):
            return


def _taxonomy_loop() -> None:
    started = time.time()
    last_run: dict[str, float] = {}
    while not _stop.is_set():
        now = time.time()
        db = SessionLocal()
        try:
            agents = list_taxonomists(db, live_only=True) or []
            specs = []
            for agent in agents:
                cfg = load_config(db, agent.slug)
                specs.append((agent.slug, cadence_seconds(cfg.get("cadence"))))
        finally:
            db.close()
        if not specs:
            specs = [("taxonomist", 3600)]
        for slug, wait in specs:
            previous = last_run.get(slug, 0.0)
            due = previous == 0 and now - started >= 15
            if previous and now - previous >= wait:
                due = True
            if not due:
                continue
            db = SessionLocal()
            try:
                library.run_cycle(db, slug)
                logger.info("Taxonomist cycle finished slug=%s", slug)
                last_run[slug] = time.time()
            except Exception:
                logger.exception("Taxonomist cycle failed slug=%s", slug)
                last_run[slug] = time.time()
            finally:
                db.close()
        if _stop.wait(5):
            return

from __future__ import annotations

from pathlib import Path

from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer

from app.config import Settings, settings
from app.db.session import SessionLocal
from app.services import library, pipeline
from app.services.parsers import SUPPORTED_SUFFIXES

_observer: Observer | None = None


class DocumentHandler(FileSystemEventHandler):
    def __init__(self, root: Path) -> None:
        self._root = root

    def on_created(self, event: FileSystemEvent) -> None:
        self._maybe_register(event)

    def on_modified(self, event: FileSystemEvent) -> None:
        self._maybe_register(event)

    def _maybe_register(self, event: FileSystemEvent) -> None:
        if event.is_directory:
            return
        path = Path(str(event.src_path))
        if path.suffix.lower() not in SUPPORTED_SUFFIXES:
            return
        if path.name.lower() in {"readme.md"}:
            return
        if pipeline._is_classified(path, Path(settings.documents_dir)):
            return
        db = SessionLocal()
        try:
            library.register_path(db, path, source="folder")
            db.commit()
        except Exception:
            db.rollback()
        finally:
            db.close()


def start_folder_watcher(app_settings: Settings | None = None) -> Observer | None:
    global _observer
    cfg = app_settings or settings
    if not cfg.watch_documents:
        return None
    from app.services.knobs import watch_recursive, watch_root

    folder = watch_root()
    folder.mkdir(parents=True, exist_ok=True)
    stop_folder_watcher()
    observer = Observer()
    handler = DocumentHandler(Path(cfg.documents_dir))
    observer.schedule(handler, str(folder), recursive=watch_recursive())
    observer.daemon = True
    observer.start()
    _observer = observer
    return observer


def stop_folder_watcher() -> None:
    global _observer
    if _observer is None:
        return
    _observer.stop()
    _observer.join(timeout=2)
    _observer = None


def restart_folder_watcher() -> None:
    if not settings.watch_documents:
        return
    start_folder_watcher(settings)

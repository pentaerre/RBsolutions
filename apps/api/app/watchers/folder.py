from __future__ import annotations

from pathlib import Path

from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer

from app.config import Settings
from app.services.ingest import IngestService
from app.services.parsers import SUPPORTED_SUFFIXES


class DocumentHandler(FileSystemEventHandler):
    def __init__(self, ingest: IngestService, root: Path) -> None:
        self._ingest = ingest
        self._root = root

    def on_created(self, event: FileSystemEvent) -> None:
        self._maybe_ingest(event)

    def on_modified(self, event: FileSystemEvent) -> None:
        self._maybe_ingest(event)

    def _maybe_ingest(self, event: FileSystemEvent) -> None:
        if event.is_directory:
            return
        path = Path(str(event.src_path))
        if path.suffix.lower() not in SUPPORTED_SUFFIXES:
            return
        if path.name.lower() in {"readme.md"}:
            return
        classified = self._root / "classified"
        try:
            path.relative_to(classified)
            return
        except ValueError:
            pass
        self._ingest.ingest_file(path)


def start_folder_watcher(settings: Settings, ingest: IngestService) -> Observer:
    root = Path(settings.documents_dir)
    inbox = root / "inbox"
    inbox.mkdir(parents=True, exist_ok=True)
    observer = Observer()
    handler = DocumentHandler(ingest, root)
    observer.schedule(handler, str(root), recursive=False)
    observer.schedule(handler, str(inbox), recursive=False)
    observer.daemon = True
    observer.start()
    return observer

from __future__ import annotations

from pathlib import Path
from typing import Any

from app.config import Settings
from app.services import pipeline
from app.services.vectorstore import VectorStore


class IngestService:
    def __init__(self, settings: Settings, store: VectorStore) -> None:
        self._settings = settings
        self._store = store
        self._root = Path(settings.documents_dir)

    def list_files(self) -> list[dict[str, Any]]:
        return pipeline.list_files(self._store, self._root)

    def ingest_all(self) -> dict[str, Any]:
        return pipeline.process_all(self._store)

    def ingest_file(self, path: Path) -> dict[str, Any]:
        return pipeline.process_file(Path(path), self._store)

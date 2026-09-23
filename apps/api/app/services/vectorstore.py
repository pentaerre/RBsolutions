from __future__ import annotations

import hashlib
from typing import Any

from qdrant_client import QdrantClient
from qdrant_client.http import models as qmodels

from app.config import Settings

VECTOR_SIZE = 64


def embed_text(text: str) -> list[float]:
    digest = hashlib.sha256(text.encode("utf-8")).digest()
    values = [b / 255.0 for b in digest]
    while len(values) < VECTOR_SIZE:
        digest = hashlib.sha256(bytes(int(v * 255) for v in values[:32])).digest()
        values.extend(b / 255.0 for b in digest)
    return values[:VECTOR_SIZE]


def embed_texts(texts: list[str]) -> list[list[float]]:
    return [embed_text(text) for text in texts]


class VectorStore:
    """Qdrant-backed chunk index. Uses in-memory Qdrant when url is 'memory'."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._collection = settings.qdrant_collection
        url = (settings.qdrant_url or "memory").strip()
        if url in {"memory", ":memory:", "off"}:
            try:
                self._client = QdrantClient(":memory:")
            except Exception:
                self._client = QdrantClient(location=":memory:")
            self._mode = "memory"
        else:
            self._client = QdrantClient(url=url, timeout=10)
            self._mode = "http"
        self._ensure_collection()

    @property
    def mode(self) -> str:
        return self._mode

    def _ensure_collection(self) -> None:
        names = {item.name for item in self._client.get_collections().collections}
        if self._collection in names:
            return
        self._client.create_collection(
            collection_name=self._collection,
            vectors_config=qmodels.VectorParams(size=VECTOR_SIZE, distance=qmodels.Distance.COSINE),
        )

    def health(self) -> dict[str, Any]:
        try:
            self._client.get_collections()
            return {"ok": True, "mode": self._mode, "collection": self._collection}
        except Exception as exc:  # pragma: no cover
            return {"ok": False, "mode": self._mode, "error": str(exc)}

    def count(self) -> int:
        info = self._client.get_collection(self._collection)
        return int(info.points_count or 0)

    def list_sources(self) -> list[dict[str, Any]]:
        grouped: dict[str, dict[str, Any]] = {}
        offset = None
        while True:
            records, offset = self._client.scroll(
                collection_name=self._collection,
                limit=128,
                offset=offset,
                with_payload=True,
                with_vectors=False,
            )
            for point in records:
                payload = point.payload or {}
                name = payload.get("filename") or "unknown"
                entry = grouped.setdefault(
                    name,
                    {
                        "filename": name,
                        "chunks": 0,
                        "pages": payload.get("pages", 0),
                        "source_path": payload.get("source_path", ""),
                    },
                )
                entry["chunks"] += 1
            if offset is None:
                break
        return sorted(grouped.values(), key=lambda item: item["filename"])

    def delete_filename(self, filename: str) -> None:
        self._client.delete(
            collection_name=self._collection,
            points_selector=qmodels.FilterSelector(
                filter=qmodels.Filter(
                    must=[qmodels.FieldCondition(key="filename", match=qmodels.MatchValue(value=filename))]
                )
            ),
        )

    def upsert_chunks(
        self,
        *,
        filename: str,
        source_path: str,
        pages: int,
        chunks: list[str],
        file_id: str,
    ) -> int:
        self.delete_filename(filename)
        if not chunks:
            return 0
        vectors = embed_texts(chunks)
        points = []
        for index, (chunk, vector) in enumerate(zip(chunks, vectors)):
            points.append(
                qmodels.PointStruct(
                    id=abs(hash(f"{file_id}-{index}")) % (2**63),
                    vector=vector,
                    payload={
                        "filename": filename,
                        "source_path": source_path,
                        "pages": pages,
                        "chunk_index": index,
                        "file_id": file_id,
                        "text": chunk,
                    },
                )
            )
        self._client.upsert(collection_name=self._collection, points=points)
        return len(chunks)

    def query(self, question: str, top_k: int) -> list[dict[str, Any]]:
        if self.count() == 0:
            return []
        hits_raw = self._client.search(
            collection_name=self._collection,
            query_vector=embed_text(question),
            limit=min(top_k, self.count()),
            with_payload=True,
        )
        hits: list[dict[str, Any]] = []
        for point in hits_raw:
            payload = point.payload or {}
            hits.append(
                {
                    "text": payload.get("text", ""),
                    "filename": payload.get("filename"),
                    "chunk_index": payload.get("chunk_index"),
                    "distance": 1 - float(point.score or 0),
                }
            )
        return hits

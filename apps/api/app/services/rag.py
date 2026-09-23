from __future__ import annotations

import json
from collections.abc import AsyncIterator
from typing import Any

from app.config import Settings
from app.services.ollama_client import OllamaClient, OllamaError
from app.services.vectorstore import VectorStore

SYSTEM_PROMPT = """You are Atrium, a local workspace assistant.
Answer using the provided document excerpts when they are relevant.
If the excerpts do not contain the answer, say so and then use general knowledge.
Cite source filenames inline when you use them. Be concise and practical."""


def build_messages(
    question: str,
    hits: list[dict[str, Any]],
    system_prompt: str | None = None,
) -> list[dict[str, str]]:
    if hits:
        blocks = []
        for index, hit in enumerate(hits, start=1):
            blocks.append(
                f"[{index}] {hit.get('filename')} (chunk {hit.get('chunk_index')})"
                + (f" entities: {', '.join(hit.get('entities') or [])}" if hit.get("entities") else "")
                + (f" neighbors: {', '.join(hit.get('neighbors') or [])}" if hit.get("neighbors") else "")
                + f"\n{hit.get('text')}"
            )
        context = "\n\n".join(blocks)
        user = (
            f"Document excerpts:\n{context}\n\n"
            f"Question: {question}\n\n"
            "Answer the question. Prefer the excerpts."
        )
    else:
        user = (
            "There are no indexed document excerpts for this question.\n\n"
            f"Question: {question}"
        )
    return [
        {"role": "system", "content": system_prompt or SYSTEM_PROMPT},
        {"role": "user", "content": user},
    ]


class RagService:
    def __init__(self, settings: Settings, store: VectorStore, ollama: OllamaClient) -> None:
        self._settings = settings
        self._store = store
        self._ollama = ollama

    def retrieve(self, question: str) -> list[dict[str, Any]]:
        return self._store.query(question, self._settings.rag_top_k)

    async def stream_answer(
        self,
        question: str,
        model: str | None = None,
    ) -> AsyncIterator[str]:
        hits = self.retrieve(question)
        sources = [
            {
                "filename": hit.get("filename"),
                "chunk_index": hit.get("chunk_index"),
                "distance": hit.get("distance"),
            }
            for hit in hits
        ]
        yield sse({"type": "sources", "items": sources})
        # Padding so proxies/uvicorn flush the first event before Ollama starts.
        yield ":" + (" " * 2048) + "\n\n"
        messages = build_messages(question, hits)
        try:
            async for line in self._ollama.stream_chat(messages, model=model):
                event = json.loads(line)
                token = (event.get("message") or {}).get("content") or ""
                if token:
                    yield sse({"type": "token", "content": token})
                if event.get("done"):
                    break
        except OllamaError as exc:
            yield sse({"type": "error", "message": str(exc)})
        yield sse({"type": "done"})


def sse(payload: dict[str, Any]) -> str:
    return f"data: {json.dumps(payload)}\n\n"

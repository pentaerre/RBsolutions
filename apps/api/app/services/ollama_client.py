from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

import httpx

from app.config import Settings


class OllamaError(RuntimeError):
    pass


def model_name(item: dict[str, Any]) -> str:
    return str(item.get("name") or item.get("model") or "").strip()


def normalize_models(raw: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    models: list[dict[str, Any]] = []
    for item in raw:
        name = model_name(item)
        if not name or name in seen:
            continue
        seen.add(name)
        details = item.get("details") or {}
        models.append(
            {
                "name": name,
                "size": item.get("size"),
                "family": details.get("family"),
                "parameter_size": details.get("parameter_size"),
            }
        )
    return models


def pick_default_model(names: list[str], preferred: str) -> str:
    if preferred and preferred in names:
        return preferred
    return names[0] if names else preferred


class OllamaClient:
    def __init__(self, settings: Settings) -> None:
        self._base = settings.ollama_base_url.rstrip("/")
        self._default_model = settings.ollama_chat_model
        self._embed_model = settings.ollama_embed_model

    async def health(self) -> dict[str, Any]:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self._base}/api/tags")
                response.raise_for_status()
                payload = response.json()
        except httpx.HTTPError as exc:
            return {"ok": False, "error": str(exc), "models": []}

        catalog = normalize_models(payload.get("models", []))
        names = [item["name"] for item in catalog]
        default_model = pick_default_model(names, self._default_model)
        return {
            "ok": True,
            "models": names,
            "default_model": default_model,
            "default_available": default_model in names,
        }

    async def list_models(self) -> list[dict[str, Any]]:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{self._base}/api/tags")
            response.raise_for_status()
            return response.json().get("models", [])

    async def catalog(self) -> dict[str, Any]:
        raw = await self.list_models()
        models = normalize_models(raw)
        names = [item["name"] for item in models]
        default = pick_default_model(names, self._default_model)
        return {"default": default, "models": models}

    async def embeddings(self, text: str) -> list[float]:
        if not self._embed_model:
            raise OllamaError("OLLAMA_EMBED_MODEL is not configured")
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{self._base}/api/embeddings",
                json={"model": self._embed_model, "prompt": text},
            )
            response.raise_for_status()
            data = response.json()
        embedding = data.get("embedding")
        if not embedding:
            raise OllamaError("Ollama returned an empty embedding")
        return embedding

    async def stream_chat(
        self,
        messages: list[dict[str, str]],
        model: str | None = None,
    ) -> AsyncIterator[str]:
        payload = {
            "model": model or self._default_model,
            "messages": messages,
            "stream": True,
        }
        timeout = httpx.Timeout(600.0, connect=5.0)
        async with httpx.AsyncClient(timeout=timeout) as client:
            try:
                async with client.stream("POST", f"{self._base}/api/chat", json=payload) as response:
                    if response.status_code >= 400:
                        body = (await response.aread()).decode("utf-8", errors="replace")
                        raise OllamaError(f"Ollama chat failed ({response.status_code}): {body}")
                    async for line in response.aiter_lines():
                        if not line:
                            continue
                        yield line
            except httpx.HTTPError as exc:
                raise OllamaError(f"Cannot reach Ollama at {self._base}: {exc}") from exc

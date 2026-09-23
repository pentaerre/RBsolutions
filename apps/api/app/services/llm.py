from __future__ import annotations

from collections.abc import AsyncIterator

from app.config import settings
from app.services.ollama_client import OllamaClient, OllamaError


async def stream_llm(messages: list[dict[str, str]], model: str) -> AsyncIterator[str]:
    provider = (settings.llm_provider or "ollama").lower()
    if provider == "anthropic" and settings.anthropic_api_key:
        async for token in _stream_anthropic(messages, model):
            yield token
        return
    try:
        async for token in _stream_ollama_langchain(messages, model):
            yield token
        return
    except Exception:
        pass
    client = OllamaClient(settings)
    import json

    try:
        async for line in client.stream_chat(messages, model=model):
            event = json.loads(line)
            token = (event.get("message") or {}).get("content") or ""
            if token:
                yield token
            if event.get("done"):
                break
    except OllamaError as exc:
        raise RuntimeError(str(exc)) from exc


async def _stream_ollama_langchain(messages: list[dict[str, str]], model: str) -> AsyncIterator[str]:
    from langchain_core.messages import HumanMessage, SystemMessage
    from langchain_ollama import ChatOllama

    llm = ChatOllama(base_url=settings.ollama_base_url, model=model, timeout=600)
    converted = []
    for item in messages:
        if item["role"] == "system":
            converted.append(SystemMessage(content=item["content"]))
        else:
            converted.append(HumanMessage(content=item["content"]))
    async for chunk in llm.astream(converted):
        text = chunk.content if isinstance(chunk.content, str) else ""
        if text:
            yield text


async def _stream_anthropic(messages: list[dict[str, str]], model: str) -> AsyncIterator[str]:
    from langchain_anthropic import ChatAnthropic
    from langchain_core.messages import HumanMessage, SystemMessage

    chosen = model if model.startswith("claude") else "claude-3-5-sonnet-latest"
    llm = ChatAnthropic(api_key=settings.anthropic_api_key, model=chosen, timeout=120)
    converted = []
    for item in messages:
        if item["role"] == "system":
            converted.append(SystemMessage(content=item["content"]))
        else:
            converted.append(HumanMessage(content=item["content"]))
    async for chunk in llm.astream(converted):
        text = chunk.content if isinstance(chunk.content, str) else ""
        if text:
            yield text


def complete_json(prompt: str, model: str | None = None) -> dict:
    import json
    import re

    from langchain_core.messages import HumanMessage, SystemMessage
    from langchain_ollama import ChatOllama

    chosen = model or settings.ollama_chat_model
    llm = ChatOllama(base_url=settings.ollama_base_url, model=chosen, timeout=180)
    result = llm.invoke(
        [
            SystemMessage(content="Return a single JSON object. No markdown."),
            HumanMessage(content=prompt),
        ]
    )
    text = result.content if isinstance(result.content, str) else str(result.content)
    match = re.search(r"\{.*\}", text, flags=re.DOTALL)
    if not match:
        return {}
    try:
        data = json.loads(match.group(0))
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}

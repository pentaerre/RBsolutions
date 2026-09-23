from __future__ import annotations

import json
from typing import Any

from app.db.models import Agent, App, Tool


def app_to_dict(item: App) -> dict[str, Any]:
    return {
        "id": item.id,
        "slug": item.slug,
        "name": item.name,
        "kind": item.kind,
        "base_url": item.base_url,
        "status": item.status,
        "summary": item.summary,
    }


def tool_to_dict(item: Tool) -> dict[str, Any]:
    agents = [link.agent.slug for link in item.agent_links if link.agent]
    return {
        "id": item.id,
        "slug": item.slug,
        "name": item.name,
        "kind": item.kind,
        "status": item.status,
        "summary": item.summary,
        "entrypoint": item.entrypoint,
        "config": json.loads(item.config_json or "{}"),
        "agents": agents,
    }


def agent_to_dict(item: Agent) -> dict[str, Any]:
    tools = [link.tool.slug for link in item.tool_links if link.tool]
    return {
        "id": item.id,
        "slug": item.slug,
        "name": item.name,
        "role": item.role,
        "status": item.status,
        "summary": item.summary,
        "model": item.model,
        "system_prompt": item.system_prompt,
        "config": json.loads(item.config_json or "{}"),
        "tools": tools,
    }

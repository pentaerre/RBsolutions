from __future__ import annotations

import json
from typing import Any

from app.db.models import Agent, App, Tool
from app.services.llm_agents import agent_uses_llm


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
    from app.services.knobs import tool_knobs_for

    agents = [link.agent.slug for link in item.agent_links if link.agent]
    config = json.loads(item.config_json or "{}")
    return {
        "id": item.id,
        "slug": item.slug,
        "name": item.name,
        "kind": item.kind,
        "status": item.status,
        "summary": item.summary,
        "entrypoint": item.entrypoint,
        "config": config,
        "agents": agents,
        "knobs": tool_knobs_for(item.kind, config),
    }


def agent_to_dict(item: Agent) -> dict[str, Any]:
    from app.services.knobs import knobs_for

    tools = [link.tool.slug for link in item.tool_links if link.tool]
    config = json.loads(item.config_json or "{}")
    return {
        "id": item.id,
        "slug": item.slug,
        "name": item.name,
        "role": item.role,
        "status": item.status,
        "summary": item.summary,
        "model": item.model,
        "uses_llm": agent_uses_llm(item.slug),
        "system_prompt": item.system_prompt,
        "config": config,
        "tools": tools,
        "knobs": knobs_for(item.slug, config),
    }

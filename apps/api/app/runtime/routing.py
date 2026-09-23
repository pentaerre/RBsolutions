from __future__ import annotations

from typing import Any


def choose_agent_slug(message: str, routes: list[dict[str, Any]], available: set[str]) -> str:
    text = message.lower()
    fallback = "orchestrator"
    for rule in routes:
        agent = str(rule.get("agent") or "")
        match = rule.get("match") or []
        if not agent:
            continue
        if match == ["*"]:
            fallback = agent if agent in available else fallback
            continue
        if any(str(token).lower() in text for token in match):
            if agent in available:
                return agent
    if fallback in available:
        return fallback
    return next(iter(available), "orchestrator")

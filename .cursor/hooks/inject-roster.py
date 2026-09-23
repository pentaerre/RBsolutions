#!/usr/bin/env python3
"""Inject the live Atrium catalog into every new agent session."""

from __future__ import annotations

import json
import sys
import urllib.request
from pathlib import Path

sys.stdin.read()

lines = [
    "Atrium north star: sell outcomes on channels they already use, not another CRUD app.",
    "Every capability is a catalog agent + tool + graph edge. Admin → Graph is the picture of truth.",
    "Views: High-level architecture, Detailed architecture, RAG graphs.",
]


def _from_api() -> list[str] | None:
    try:
        with urllib.request.urlopen("http://127.0.0.1:8000/api/agents", timeout=2) as response:
            payload = json.load(response)
    except Exception:
        return None
    agents = payload.get("agents") or []
    if not agents:
        return None
    block = ["Live catalog (do not guess):"]
    for agent in agents:
        tools = ", ".join(agent.get("tools") or []) or "no tools"
        block.append(
            f"- {agent.get('name')} ({agent.get('slug')}) {agent.get('role')} · {tools}"
        )
    return block


def _from_agents_md() -> list[str] | None:
    path = Path("AGENTS.md")
    if not path.exists():
        return None
    text = path.read_text(encoding="utf-8")
    start = "<!-- atrium-roster:start -->"
    end = "<!-- atrium-roster:end -->"
    if start not in text or end not in text:
        return ["Read AGENTS.md if you get lost."]
    body = text.split(start, 1)[1].split(end, 1)[0].strip()
    return ["Roster from AGENTS.md (API was unreachable):", body]


extra = _from_api() or _from_agents_md() or ["Read AGENTS.md if you get lost."]
print(json.dumps({"additional_context": "\n".join(lines + extra)}))

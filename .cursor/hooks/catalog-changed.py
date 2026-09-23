#!/usr/bin/env python3
"""After catalog source files change, remind the agent to let Scribe refresh prompts."""

from __future__ import annotations

import json
import sys

raw = sys.stdin.read()
try:
    payload = json.loads(raw) if raw.strip() else {}
except json.JSONDecodeError:
    payload = {}

path = str(payload.get("file_path") or payload.get("path") or payload.get("file") or "")
print(
    json.dumps(
        {
            "additional_context": (
                "Catalog source changed"
                + (f" ({path})" if path else "")
                + ". Admin Graph hydrates from Postgres. Ask Scribe to 'sync the context prompt' "
                "so AGENTS.md matches the live agents, or reboot the API."
            )
        }
    )
)

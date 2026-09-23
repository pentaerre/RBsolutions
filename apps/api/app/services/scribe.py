from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from app.config import settings
from app.db.models import Agent

logger = logging.getLogger("atrium.scribe")

START = "<!-- atrium-roster:start -->"
END = "<!-- atrium-roster:end -->"

ROSTER_GROUPS: list[tuple[str, list[str], str]] = [
    ("Intake", ["watchman", "mailroom", "courier"], ", "),
    ("Line", ["parser", "triage", "chunker", "graphsmith", "extractor", "recorder", "clerk"], " → "),
    ("Memory", ["pathfinder", "librarian"], ", "),
    ("Governance", ["reviewer", "architect", "orchestrator", "ingestor", "scribe"], ", "),
]

HINTS = {
    "watchman": "folder",
    "mailroom": "IMAP",
    "courier": "Telegram",
    "graphsmith": "entities",
    "recorder": "SQL",
    "clerk": "file by type",
    "pathfinder": "GraphRAG retrieve",
    "librarian": "answer with that context",
    "reviewer": "exceptions",
    "architect": "explains the live map",
    "orchestrator": "routes",
    "ingestor": "runs the whole line",
    "scribe": "keeps prompts in sync",
}


def repo_root() -> Path | None:
    if settings.docs_root:
        root = Path(settings.docs_root)
        return root if (root / "AGENTS.md").exists() else None
    here = Path(__file__).resolve()
    candidates = [
        Path("/repo"),
        Path("/root/project"),
        here.parents[4] if len(here.parents) >= 5 else Path.cwd(),
        Path.cwd(),
    ]
    for root in candidates:
        if (root / "AGENTS.md").exists():
            return root
    return None


def render_roster(db: Session) -> str:
    agents = {row.slug: row for row in db.query(Agent).all()}
    used: set[str] = set()
    lines: list[str] = []
    for title, slugs, joiner in ROSTER_GROUPS:
        parts = []
        for slug in slugs:
            agent = agents.get(slug)
            if agent is None:
                continue
            used.add(slug)
            hint = HINTS.get(slug)
            parts.append(f"{agent.name} ({hint})" if hint else agent.name)
        if parts:
            lines.append(f"{title}: {joiner.join(parts)}.")
    leftover = [agent for slug, agent in sorted(agents.items()) if slug not in used]
    if leftover:
        names = ", ".join(agent.name for agent in leftover)
        lines.append(f"Also: {names}.")
    return "\n".join(lines)


def patch_markers(text: str, body: str) -> tuple[str, bool]:
    if START not in text or END not in text:
        return text, False
    before, rest = text.split(START, 1)
    _, after = rest.split(END, 1)
    updated = f"{before}{START}\n{body.strip()}\n{END}{after}"
    return updated, updated != text


def sync_docs(db: Session, root: Path | None = None) -> dict[str, Any]:
    target = root or repo_root()
    roster = render_roster(db)
    if target is None:
        return {"ok": False, "message": "AGENTS.md not mounted. Set DOCS_ROOT.", "roster": roster, "written": []}
    written: list[str] = []
    for relative in ("AGENTS.md", "docs/HOW_IT_WORKS.md"):
        path = target / relative
        if not path.exists():
            continue
        updated, changed = patch_markers(path.read_text(encoding="utf-8"), roster)
        if changed:
            path.write_text(updated, encoding="utf-8")
            written.append(relative)
    return {"ok": True, "roster": roster, "written": written, "root": str(target)}


def try_sync_docs(db: Session) -> dict[str, Any] | None:
    if not settings.sync_docs:
        return None
    try:
        return sync_docs(db)
    except Exception as exc:  # pragma: no cover - file permissions in some hosts
        logger.warning("Scribe could not sync docs: %s", exc)
        return {"ok": False, "message": str(exc)}

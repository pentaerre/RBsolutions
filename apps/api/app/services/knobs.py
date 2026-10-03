from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from app.config import settings
from app.db.models import Agent

# Operator-facing knobs. Secrets (IMAP password, bot token) stay in env.
AGENT_KNOBS: dict[str, list[dict[str, Any]]] = {
    "watchman": [
        {
            "key": "watch_path",
            "type": "string",
            "default": "inbox",
            "label_key": "knob.watch_path",
            "help_key": "knob.watch_path.help",
        },
        {
            "key": "recursive",
            "type": "bool",
            "default": True,
            "label_key": "knob.recursive",
            "help_key": "knob.recursive.help",
        },
    ],
    "mailroom": [
        {
            "key": "imap_folder",
            "type": "string",
            "default": "INBOX",
            "label_key": "knob.imap_folder",
            "help_key": "knob.imap_folder.help",
        },
        {
            "key": "poll_seconds",
            "type": "number",
            "default": 0,
            "label_key": "knob.poll_seconds",
            "help_key": "knob.poll_seconds.help",
        },
    ],
    "sentinel": [
        {
            "key": "mailboxes",
            "type": "string",
            "default": "INBOX",
            "label_key": "knob.mailboxes",
            "help_key": "knob.mailboxes.help",
        },
        {
            "key": "signals",
            "type": "string",
            "default": "legal,opportunity,churn",
            "label_key": "knob.signals",
            "help_key": "knob.signals.help",
        },
        {
            "key": "stale_hours",
            "type": "number",
            "default": 24,
            "label_key": "knob.stale_hours",
            "help_key": "knob.stale_hours.help",
        },
        {
            "key": "notify",
            "type": "select",
            "options": [
                {"value": "courier", "label_key": "knob.notify.courier"},
                {"value": "teams", "label_key": "knob.notify.teams"},
                {"value": "post", "label_key": "knob.notify.post"},
            ],
            "default": "courier",
            "label_key": "knob.notify",
            "help_key": "knob.notify.help",
        },
        {
            "key": "poll_seconds",
            "type": "number",
            "default": 0,
            "label_key": "knob.sentinel_poll",
            "help_key": "knob.sentinel_poll.help",
        },
    ],
    "reader": [
        {
            "key": "read_pages",
            "type": "number",
            "default": 2,
            "label_key": "knob.read_pages",
            "help_key": "knob.read_pages.help",
        },
    ],
    "taxonomist": [
        {
            "key": "cadence",
            "type": "select",
            "options": [
                {"value": "hour", "label_key": "knob.cadence.hour"},
                {"value": "day", "label_key": "knob.cadence.day"},
                {"value": "week", "label_key": "knob.cadence.week"},
            ],
            "default": "hour",
            "label_key": "knob.cadence",
            "help_key": "knob.cadence.help",
        },
        {
            "key": "scope_path",
            "type": "string",
            "default": "inbox",
            "label_key": "knob.scope_path",
            "help_key": "knob.scope_path.help",
        },
        {
            "key": "taxonomy.name",
            "type": "string",
            "default": "E&P",
            "label_key": "knob.taxonomy_name",
            "help_key": "knob.taxonomy_name.help",
        },
    ],
}

HTTP_TOOL_KNOBS: list[dict[str, Any]] = [
    {
        "key": "url",
        "type": "string",
        "default": "",
        "label_key": "knob.http_url",
        "help_key": "knob.http_url.help",
    },
    {
        "key": "method",
        "type": "select",
        "options": [
            {"value": "POST", "label_key": "knob.method.post"},
            {"value": "GET", "label_key": "knob.method.get"},
        ],
        "default": "POST",
        "label_key": "knob.http_method",
        "help_key": "knob.http_method.help",
    },
]

# Sold utilities: assemblies of unit-task agents. Not extra employees.
# Each library-* is the same utility sold to a different client tree.
UTILITIES: list[dict[str, Any]] = [
    {
        "slug": "library",
        "name": "Document library · E&P",
        "summary": "Folder and email intake → E&P Taxonomist. Drop under inbox. Operators promote selected files into GraphRAG.",
        "workspace_path": "/library",
        "agents": ["mailroom", "watchman", "reader", "taxonomist", "clerk"],
    },
    {
        "slug": "library-aircraft",
        "name": "Document library · Aircraft",
        "summary": "Same library utility bound to Aircraft Taxonomist. Drop files under inbox/aircraft.",
        "workspace_path": "/library",
        "agents": ["mailroom", "watchman", "reader", "taxonomist-aircraft", "clerk"],
    },
    {
        "slug": "library-car",
        "name": "Document library · Car",
        "summary": "Same library utility bound to Car Taxonomist. Drop files under inbox/car.",
        "workspace_path": "/library",
        "agents": ["mailroom", "watchman", "reader", "taxonomist-car", "clerk"],
    },
    {
        "slug": "library-factory",
        "name": "Document library · Factory",
        "summary": "Same library utility bound to Factory Taxonomist. Drop files under inbox/factory.",
        "workspace_path": "/library",
        "agents": ["mailroom", "watchman", "reader", "taxonomist-factory", "clerk"],
    },
    {
        "slug": "library-bars",
        "name": "Document library · Bars",
        "summary": "Same library utility bound to Bars Taxonomist (HORECA distributors). Drop files under inbox/bars.",
        "workspace_path": "/library",
        "agents": ["mailroom", "watchman", "reader", "taxonomist-bars", "clerk"],
    },
    {
        "slug": "library-advice",
        "name": "Document library · Advice",
        "summary": "Same library utility bound to Advice Taxonomist (labor + tax). Drop files under inbox/advice.",
        "workspace_path": "/library",
        "agents": ["mailroom", "watchman", "reader", "taxonomist-advice", "clerk"],
    },
    {
        "slug": "idp-line",
        "name": "Document line",
        "summary": "Explicit IDP run: parse, triage, extract SQL rows, file by type. Not fired on every arrival.",
        "workspace_path": "/documents",
        "agents": ["parser", "triage", "extractor", "recorder", "clerk", "ingestor"],
    },
    {
        "slug": "graphrag",
        "name": "GraphRAG answers",
        "summary": "Chunk, entity graph, and answers. Only documents someone chose to promote.",
        "workspace_path": "/chat",
        "agents": ["chunker", "graphsmith", "pathfinder", "librarian"],
    },
    {
        "slug": "operations",
        "name": "Operations brief",
        "summary": "Shared inboxes for direction: Sentinel flags legal risk, stale commercial asks, and churn, then crosses Neo4j and the SQL ledger. Reviewer holds the brief. Courier pings Telegram.",
        "workspace_path": "/chat",
        "agents": ["mailroom", "sentinel", "pathfinder", "recorder", "reviewer", "courier", "teams", "post"],
    },
]


def get_value(config: dict[str, Any], key: str, default: Any = None) -> Any:
    current: Any = config
    for part in key.split("."):
        if not isinstance(current, dict) or part not in current:
            return default
        current = current[part]
    return current


def set_value(config: dict[str, Any], key: str, value: Any) -> dict[str, Any]:
    parts = key.split(".")
    cursor = config
    for part in parts[:-1]:
        nxt = cursor.get(part)
        if not isinstance(nxt, dict):
            nxt = {}
            cursor[part] = nxt
        cursor = nxt
    cursor[parts[-1]] = value
    return config


def family_of(slug: str, config: dict[str, Any] | None = None) -> str:
    from app.services.taxonomy import is_taxonomist

    if is_taxonomist(slug, config):
        return "taxonomist"
    return slug if slug in AGENT_KNOBS else slug


def knobs_for(slug: str, config: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    config = config or {}
    rows = []
    for field in AGENT_KNOBS.get(family_of(slug, config)) or []:
        item = dict(field)
        item["value"] = get_value(config, field["key"], field.get("default"))
        rows.append(item)
    return rows


def tool_knobs_for(kind: str, config: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    if kind != "http":
        return []
    config = config or {}
    rows = []
    for field in HTTP_TOOL_KNOBS:
        item = dict(field)
        item["value"] = get_value(config, field["key"], field.get("default"))
        rows.append(item)
    return rows


def agent_config(db: Session, slug: str) -> dict[str, Any]:
    row = db.query(Agent).filter(Agent.slug == slug).first()
    if row is None:
        return {}
    try:
        return json.loads(row.config_json or "{}")
    except json.JSONDecodeError:
        return {}


def apply_knobs(db: Session, slug: str, updates: dict[str, Any]) -> dict[str, Any]:
    row = db.query(Agent).filter(Agent.slug == slug).first()
    if row is None:
        raise KeyError(slug)
    config = json.loads(row.config_json or "{}")
    family = family_of(slug, config)
    allowed = {field["key"] for field in AGENT_KNOBS.get(family) or []}
    for key, value in updates.items():
        if key not in allowed:
            continue
        field = next(item for item in AGENT_KNOBS[family] if item["key"] == key)
        config = set_value(config, key, _coerce(field, value))
    if family == "taxonomist":
        config.setdefault("specialist", "taxonomist")
        _safe_under_documents(str(config.get("scope_path") or "inbox"))
    row.config_json = json.dumps(config)
    db.flush()
    return config


def watch_root(db: Session | None = None) -> Path:
    own = db is None
    db = db or __session()
    try:
        cfg = agent_config(db, "watchman")
        rel = str(cfg.get("watch_path") or "inbox").strip() or "inbox"
        return _safe_under_documents(rel)
    finally:
        if own and db is not None:
            db.close()


def watch_recursive(db: Session | None = None) -> bool:
    own = db is None
    db = db or __session()
    try:
        cfg = agent_config(db, "watchman")
        value = cfg.get("recursive")
        if value is None:
            return True
        return bool(value)
    finally:
        if own and db is not None:
            db.close()


def reader_pages(db: Session | None = None) -> int:
    own = db is None
    db = db or __session()
    try:
        cfg = agent_config(db, "reader")
        try:
            pages = int(cfg.get("read_pages") or 2)
        except (TypeError, ValueError):
            pages = 2
        return max(1, min(pages, 20))
    finally:
        if own and db is not None:
            db.close()


def mailroom_poll_seconds(db: Session | None = None) -> int:
    own = db is None
    db = db or __session()
    try:
        cfg = agent_config(db, "mailroom")
        if "poll_seconds" in cfg:
            try:
                return max(0, int(cfg.get("poll_seconds") or 0))
            except (TypeError, ValueError):
                return 0
        return max(0, int(settings.imap_poll_seconds or 0))
    finally:
        if own and db is not None:
            db.close()


def mailroom_folder(db: Session | None = None) -> str:
    own = db is None
    db = db or __session()
    try:
        cfg = agent_config(db, "mailroom")
        return str(cfg.get("imap_folder") or settings.imap_folder or "INBOX")
    finally:
        if own and db is not None:
            db.close()


def list_utilities(db: Session) -> list[dict[str, Any]]:
    return [utility_payload(db, spec) for spec in UTILITIES]


def get_utility(db: Session, slug: str) -> dict[str, Any] | None:
    spec = next((item for item in UTILITIES if item["slug"] == slug), None)
    if spec is None:
        return None
    return utility_payload(db, spec)


def save_utility(db: Session, slug: str, values: dict[str, dict[str, Any]]) -> dict[str, Any]:
    spec = next((item for item in UTILITIES if item["slug"] == slug), None)
    if spec is None:
        raise KeyError(slug)
    allowed = set(spec["agents"])
    for agent_slug, updates in values.items():
        if agent_slug not in allowed:
            continue
        family = family_of(agent_slug, agent_config(db, agent_slug))
        if family in AGENT_KNOBS:
            apply_knobs(db, agent_slug, updates)
    db.commit()
    touch_runtime(*[name for name in values if name in allowed])
    return get_utility(db, slug) or {}


def touch_runtime(*slugs: str) -> None:
    if any(slug == "watchman" for slug in slugs):
        from app.watchers.folder import restart_folder_watcher

        restart_folder_watcher()
    from app.db.session import SessionLocal
    from app.services.taxonomy import is_taxonomist

    db = SessionLocal()
    try:
        if slugs and all(is_taxonomist(slug) for slug in slugs if slug):
            for slug in slugs:
                cfg = agent_config(db, slug)
                _safe_under_documents(str(cfg.get("scope_path") or "inbox"))
        else:
            ensure_taxonomist_scopes(db)
    finally:
        db.close()


def ensure_taxonomist_scopes(db: Session) -> None:
    from app.services.taxonomy import list_agents

    for agent in list_agents(db):
        cfg = json.loads(agent.config_json or "{}")
        _safe_under_documents(str(cfg.get("scope_path") or "inbox"))


def utility_payload(db: Session, spec: dict[str, Any]) -> dict[str, Any]:
    from app.db.serialize import agent_to_dict

    agents = []
    for slug in spec["agents"]:
        row = db.query(Agent).filter(Agent.slug == slug).first()
        if row is None:
            continue
        item = agent_to_dict(row)
        agents.append(item)
    return {
        "slug": spec["slug"],
        "name": spec["name"],
        "summary": spec["summary"],
        "workspace_path": spec["workspace_path"],
        "workspace_url": settings.workspace_url.rstrip("/") + spec["workspace_path"],
        "agents": agents,
    }


def _safe_under_documents(rel: str) -> Path:
    root = Path(settings.documents_dir).resolve()
    raw = Path(rel)
    candidate = raw.resolve() if raw.is_absolute() else (root / rel).resolve()
    try:
        candidate.relative_to(root)
    except ValueError:
        candidate = (root / "inbox").resolve()
    candidate.mkdir(parents=True, exist_ok=True)
    return candidate


def _coerce(field: dict[str, Any], value: Any) -> Any:
    kind = field.get("type")
    if kind == "bool":
        if isinstance(value, str):
            return value.strip().lower() in {"1", "true", "yes", "on"}
        return bool(value)
    if kind == "number":
        try:
            number = float(value)
        except (TypeError, ValueError):
            return field.get("default") or 0
        if float(number).is_integer():
            return int(number)
        return number
    if kind == "select":
        allowed = {str(option["value"]) for option in field.get("options") or []}
        text = str(value)
        return text if text in allowed else field.get("default")
    return str(value if value is not None else "")


def __session() -> Session:
    from app.db.session import SessionLocal

    return SessionLocal()

from __future__ import annotations

import copy
from collections import Counter
from typing import Any

from sqlalchemy.orm import Session

from app.db.models import Agent, IntakeDocument
from app.runtime.graph import HOP_LINE_GRAPH
from app.services.library import _to_dict
from app.services.llm_agents import agent_uses_llm
from app.services.taxonomy import INSTANCES, PACKS, in_scope, nested_scopes

# Library line the operator watches. Parser → Clerk is the other utility.
HOPS = [
    {
        "id": "watchman",
        "agent": "watchman",
        "status": "received",
        "label": "Watchman",
        "summary": "File landed. Registered. Not read yet.",
    },
    {
        "id": "reader",
        "agent": "reader",
        "status": "read",
        "label": "Reader",
        "summary": "First pages extracted. Summary and keywords written.",
    },
    {
        "id": "taxonomist",
        "agent": "taxonomist",
        "status": "classified",
        "label": "Taxonomist",
        "summary": "Two-level class. File still in the inbox until Clerk moves it.",
    },
    {
        "id": "clerk",
        "agent": "clerk",
        "status": "filed",
        "label": "Clerk",
        "summary": "Moved into classified/{class}/{subclass}. Still not in GraphRAG.",
    },
    {
        "id": "chunker",
        "agent": "chunker",
        "status": "indexed",
        "label": "GraphRAG",
        "summary": "Operator promoted this file. Chunker + Graphsmith.",
    },
    {
        "id": "reviewer",
        "agent": "reviewer",
        "status": "failed",
        "label": "Reviewer",
        "summary": "Missing or failed. Human gate.",
    },
]

STATUS_HOP = {
    "received": "watchman",
    "read": "reader",
    "classified": "taxonomist",
    "filed": "clerk",
    "indexed": "chunker",
    "failed": "reviewer",
    "missing": "reviewer",
}


def live_flow(db: Session, taxonomist: str | None = None) -> dict[str, Any]:
    items = [_to_dict(row) for row in db.query(IntakeDocument).all()]
    if taxonomist:
        items = [item for item in items if _belongs(item, taxonomist)]
    counts = Counter(item.get("status") or "received" for item in items)
    models = {
        row.slug: row.model
        for row in db.query(Agent).all()
        if agent_uses_llm(row.slug) and row.model
    }
    hops = []
    for hop in HOPS:
        if hop["id"] == "reviewer":
            files = [item for item in items if item.get("status") in {"failed", "missing"}]
        else:
            files = [item for item in items if _hop_for(item) == hop["id"]]
        files.sort(key=lambda item: item.get("created_at") or "", reverse=True)
        model = models.get(hop["agent"]) or ""
        hops.append({**hop, "count": len(files), "files": files[:8], "model": model})
    line = copy.deepcopy(HOP_LINE_GRAPH)
    by_node = {hop["id"]: 0 for hop in HOPS}
    by_node["graphsmith"] = 0
    for item in items:
        node = _hop_for(item)
        if node == "chunker":
            by_node["graphsmith"] += 1
        if node in by_node:
            by_node[node] += 1
    for node in line["nodes"]:
        if node["id"] not in by_node:
            continue
        node["count"] = by_node[node["id"]]
        node["detail"] = f"{by_node[node['id']]} in hop"
        node["hot"] = by_node[node["id"]] > 0
        if node["id"] in models:
            node["model"] = models[node["id"]]
    return {
        "hops": hops,
        "counts": dict(counts),
        "total": len(items),
        "line": line,
        "documents": sorted(items, key=lambda item: item.get("file_created_at") or item.get("created_at") or "", reverse=True),
    }


def _hop_for(item: dict[str, Any]) -> str:
    status = item.get("status") or ""
    rel = (item.get("rel_path") or "").replace("\\", "/")
    if status == "classified" and rel.startswith("classified/"):
        return "clerk"
    return STATUS_HOP.get(status) or ""


def _belongs(item: dict[str, Any], slug: str) -> bool:
    owned = item.get("taxonomist_slug") or ""
    if owned:
        return owned == slug
    path = (item.get("rel_path") or "").replace("\\", "/")
    spec = next((row for row in INSTANCES if row["slug"] == slug), None)
    if spec is None:
        return True
    if slug == "taxonomist":
        return not any(in_scope(path, scope) for scope in nested_scopes())
    return in_scope(path, str(PACKS[spec["pack"]]["scope_path"]))

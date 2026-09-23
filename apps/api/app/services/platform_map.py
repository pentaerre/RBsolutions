from __future__ import annotations

import copy
from typing import Any

from sqlalchemy.orm import Session

from app.db.models import Agent, AgentTool, App, Tool
from app.runtime.graph import DETAIL_GRAPH, HIGH_LEVEL_GRAPH, PIPELINE_GRAPH, RAG_METHOD_GRAPH, RUNTIME_GRAPH
from app.services.graphstore import get_graphstore

GROUP_DETAILS = {
    "intake": ["watchman", "mailroom", "courier"],
    "line": ["parser", "triage", "clerk"],
    "memory": ["chunker", "graphsmith", "pathfinder", "librarian"],
    "ledger": ["extractor", "recorder"],
    "governance": ["reviewer", "architect", "scribe"],
}


def platform_catalog_graph(db: Session) -> dict[str, list]:
    nodes: list[dict[str, Any]] = []
    edges: list[dict[str, str]] = []
    for app in db.query(App).all():
        nodes.append(
            {
                "id": f"app:{app.slug}",
                "label": app.name,
                "kind": "app",
                "detail": f"{app.kind} · {app.status}",
            }
        )
    for agent in db.query(Agent).all():
        nodes.append(
            {
                "id": f"agent:{agent.slug}",
                "label": agent.name,
                "kind": "agent" if agent.role != "router" else "router",
                "detail": f"{agent.role} · {agent.status}",
            }
        )
    for tool in db.query(Tool).all():
        nodes.append(
            {
                "id": f"tool:{tool.slug}",
                "label": tool.name,
                "kind": "tool",
                "detail": f"{tool.kind} · {tool.status}",
            }
        )
    for link in db.query(AgentTool).all():
        agent = link.agent
        tool = link.tool
        if agent and tool:
            edges.append(
                {
                    "from": f"agent:{agent.slug}",
                    "to": f"tool:{tool.slug}",
                    "label": "USES",
                }
            )
    edges.append({"from": "app:workspace", "to": "agent:orchestrator", "label": "CALLS"})
    edges.append({"from": "app:admin", "to": "agent:orchestrator", "label": "MANAGES"})
    for agent in db.query(Agent).filter(Agent.role != "router").all():
        edges.append(
            {
                "from": "agent:orchestrator",
                "to": f"agent:{agent.slug}",
                "label": "ROUTES",
            }
        )
    return {"nodes": nodes, "edges": edges}


def explain_platform(db: Session) -> str:
    apps = db.query(App).order_by(App.name).all()
    agents = db.query(Agent).order_by(Agent.role, Agent.name).all()
    tools = db.query(Tool).order_by(Tool.name).all()
    lines = [
        "Atrium is a multi-agent platform, not a single chatbot.",
        "",
        "Webs (apps):",
    ]
    for app in apps:
        lines.append(f"- {app.name} ({app.slug}) [{app.kind}/{app.status}] {app.base_url}")
    lines.append("")
    lines.append("Agents (LangGraph runtime):")
    for agent in agents:
        slugs = [link.tool.slug for link in agent.tool_links if link.tool]
        lines.append(f"- {agent.name} ({agent.role}) tools={', '.join(slugs) or 'none'}")
    lines.append("")
    lines.append("Tools:")
    for tool in tools:
        lines.append(f"- {tool.slug} [{tool.status}] {tool.summary}")
    lines.append("")
    lines.append("Data: Postgres = catalog + extracted SQL rows, Qdrant = chunk vectors, Neo4j = document graph.")
    lines.append("Document pipeline: folder/email → Watchman/Mailroom → Parser → Triage → Chunker (RAG) and/or Extractor→Recorder (SQL) → Clerk.")
    lines.append("Chat flow: user → orchestrator (LangGraph router) → specialist agents.")
    return "\n".join(lines)


def _named(db: Session, slugs: list[str]) -> str:
    names = {row.slug: row.name for row in db.query(Agent).all()}
    return " · ".join(names[slug] for slug in slugs if slug in names)


def architecture_graph(db: Session) -> dict[str, list]:
    graph = copy.deepcopy(HIGH_LEVEL_GRAPH)
    details = {key: _named(db, slugs) for key, slugs in GROUP_DETAILS.items()}
    for node in graph["nodes"]:
        if node["id"] in details and details[node["id"]]:
            node["detail"] = details[node["id"]]
    return graph


def _with_catalog_agents(template: dict[str, list], db: Session, from_id: str) -> dict[str, list]:
    graph = copy.deepcopy(template)
    known = {node["id"] for node in graph["nodes"]}
    extras = [agent for agent in db.query(Agent).order_by(Agent.name) if agent.slug not in known]
    for index, agent in enumerate(extras):
        graph["nodes"].append(
            {
                "id": agent.slug,
                "label": agent.name,
                "kind": "router" if agent.role == "router" else "agent",
                "detail": (agent.summary or agent.role)[:48],
                "layer": 2,
                "row": 10 + index,
            }
        )
        graph["edges"].append({"from": from_id, "to": agent.slug, "label": "route"})
    return graph


def full_graph(db: Session) -> dict[str, Any]:
    store = get_graphstore()
    knowledge = store.knowledge_graph()
    return {
        "architecture": architecture_graph(db),
        "detail": _with_catalog_agents(DETAIL_GRAPH, db, "orchestrator"),
        "rag": {
            "method": RAG_METHOD_GRAPH,
            "knowledge": knowledge,
        },
        "runtime": _with_catalog_agents(RUNTIME_GRAPH, db, "router"),
        "pipeline": PIPELINE_GRAPH,
        "platform": platform_catalog_graph(db),
        "knowledge": knowledge,
        "stores": {
            "postgres": "catalog of apps/tools/agents + extracted SQL rows",
            "qdrant": "document chunk vectors for RAG",
            "neo4j": "GraphRAG: documents, chunks, entities, relations" if store.enabled else "disabled",
        },
        "explain": explain_platform(db),
    }

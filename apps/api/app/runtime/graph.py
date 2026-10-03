from __future__ import annotations

from typing import Any, TypedDict

from langchain_core.runnables import RunnableConfig
from langgraph.graph import END, START, StateGraph
from sqlalchemy.orm import Session

from app.db.models import Agent
from app.runtime.routing import choose_agent_slug
from app.runtime.tools import ToolError, invoke_tool

TOOL_BY_AGENT = {
    "watchman": "intake.register",
    "mailroom": "intake.poll_mail",
    "parser": "documents.parse",
    "reader": "documents.read",
    "taxonomist": "taxonomy.run",
    "triage": "documents.classify",
    "chunker": "documents.chunk",
    "extractor": "records.extract",
    "recorder": "records.list",
    "clerk": "documents.file",
    "ingestor": "knowledge.ingest",
    "graphsmith": "knowledge.graph_build",
    "pathfinder": "knowledge.graph_search",
    "courier": "telegram.poll",
    "teams": "teams.send",
    "post": "mail.send",
    "reviewer": "review.list",
    "sentinel": "signals.judge",
    "scribe": "docs.sync",
}


class AgentState(TypedDict, total=False):
    message: str
    route: str
    agent_name: str
    hits: list
    ingest_result: dict
    explain_text: str
    error: str


def router_node(state: AgentState, config: RunnableConfig) -> AgentState:
    db: Session = config["configurable"]["db"]
    agents = {row.slug: row for row in db.query(Agent).filter(Agent.status == "live").all()}
    orchestrator = agents.get("orchestrator")
    routes = []
    if orchestrator and orchestrator.config_json:
        import json

        routes = json.loads(orchestrator.config_json).get("routes") or []
    target = choose_agent_slug(state.get("message") or "", routes, set(agents))
    agent = agents.get(target)
    return {
        "route": target,
        "agent_name": agent.name if agent else target,
    }


def specialist_node(state: AgentState, config: RunnableConfig) -> AgentState:
    db: Session = config["configurable"]["db"]
    route = state.get("route") or "ingestor"
    slug = TOOL_BY_AGENT.get(route)
    if slug is None and route.startswith("taxonomist"):
        slug = "taxonomy.run"
    if slug is None:
        slug = "documents.list"
    try:
        result = invoke_tool(
            db,
            slug,
            {
                "query": state.get("message") or "",
                "message": state.get("message") or "",
                "agent": route,
            },
        )
        return {"ingest_result": result}
    except ToolError as exc:
        return {"error": str(exc)}


def librarian_node(state: AgentState, config: RunnableConfig) -> AgentState:
    db: Session = config["configurable"]["db"]
    try:
        search = invoke_tool(db, "knowledge.search", {"query": state.get("message") or ""})
        return {"hits": search.get("hits") or []}
    except ToolError as exc:
        return {"error": str(exc), "hits": []}


def architect_node(state: AgentState, config: RunnableConfig) -> AgentState:
    db: Session = config["configurable"]["db"]
    try:
        result = invoke_tool(db, "platform.explain", {})
        return {"explain_text": result.get("text") or ""}
    except ToolError as exc:
        return {"error": str(exc)}


def _branch(state: AgentState) -> str:
    route = state.get("route") or "librarian"
    if route == "librarian":
        return "librarian"
    if route in {"architect", "orchestrator"}:
        return "architect"
    return "specialist"


def build_graph():
    graph = StateGraph(AgentState)
    graph.add_node("router", router_node)
    graph.add_node("specialist", specialist_node)
    graph.add_node("librarian", librarian_node)
    graph.add_node("architect", architect_node)
    graph.add_edge(START, "router")
    graph.add_conditional_edges(
        "router",
        _branch,
        {
            "specialist": "specialist",
            "librarian": "librarian",
            "architect": "architect",
        },
    )
    graph.add_edge("specialist", END)
    graph.add_edge("librarian", END)
    graph.add_edge("architect", END)
    return graph.compile()


RUNTIME_GRAPH: dict[str, list[dict[str, Any]]] = {
    "nodes": [
        {"id": "start", "label": "User message", "kind": "start", "detail": "Workspace or API"},
        {"id": "router", "label": "Orchestrator", "kind": "router", "detail": "LangGraph router"},
        {"id": "watchman", "label": "Watchman", "kind": "agent", "detail": "Folder drop"},
        {"id": "mailroom", "label": "Mailroom", "kind": "agent", "detail": "Email attachments"},
        {"id": "sentinel", "label": "Sentinel", "kind": "agent", "detail": "Classifies the letter"},
        {"id": "parser", "label": "Parser", "kind": "agent", "detail": "PDF / Office / text"},
        {"id": "reader", "label": "Reader", "kind": "agent", "detail": "OCR + first two pages"},
        {"id": "taxonomist", "label": "Taxonomist", "kind": "agent", "detail": "Two-level taxonomy"},
        {"id": "triage", "label": "Triage", "kind": "agent", "detail": "Classify"},
        {"id": "chunker", "label": "Chunker", "kind": "agent", "detail": "RAG chunks"},
        {"id": "extractor", "label": "Extractor", "kind": "agent", "detail": "LLM / fields"},
        {"id": "recorder", "label": "Recorder", "kind": "agent", "detail": "Postgres SQL"},
        {"id": "clerk", "label": "Clerk", "kind": "agent", "detail": "File by type"},
        {"id": "graphsmith", "label": "Graphsmith", "kind": "agent", "detail": "Entities in Neo4j"},
        {"id": "pathfinder", "label": "Pathfinder", "kind": "agent", "detail": "GraphRAG retrieve"},
        {"id": "courier", "label": "Courier", "kind": "agent", "detail": "Telegram"},
        {"id": "teams", "label": "Teams", "kind": "agent", "detail": "Parked webhook"},
        {"id": "post", "label": "Post", "kind": "agent", "detail": "Parked SMTP"},
        {"id": "reviewer", "label": "Reviewer", "kind": "agent", "detail": "Human exceptions"},
        {"id": "ingestor", "label": "Ingestor", "kind": "agent", "detail": "Full pipeline"},
        {"id": "librarian", "label": "Librarian", "kind": "agent", "detail": "Answers with GraphRAG"},
        {"id": "architect", "label": "Architect", "kind": "agent", "detail": "Explains graph"},
        {"id": "scribe", "label": "Scribe", "kind": "agent", "detail": "Syncs AGENTS.md"},
    ],
    "edges": [
        {"from": "start", "to": "router", "label": "chat"},
        {"from": "router", "to": "watchman", "label": "folder"},
        {"from": "router", "to": "mailroom", "label": "email"},
        {"from": "router", "to": "sentinel", "label": "shared inbox"},
        {"from": "router", "to": "courier", "label": "telegram"},
        {"from": "router", "to": "teams", "label": "teams"},
        {"from": "router", "to": "post", "label": "mail"},
        {"from": "router", "to": "parser", "label": "parse"},
        {"from": "router", "to": "reader", "label": "ocr"},
        {"from": "router", "to": "taxonomist", "label": "taxonomy"},
        {"from": "router", "to": "triage", "label": "classify"},
        {"from": "router", "to": "chunker", "label": "chunk"},
        {"from": "router", "to": "graphsmith", "label": "entities"},
        {"from": "router", "to": "extractor", "label": "extract"},
        {"from": "router", "to": "recorder", "label": "sql rows"},
        {"from": "router", "to": "reviewer", "label": "exceptions"},
        {"from": "router", "to": "clerk", "label": "organize"},
        {"from": "router", "to": "ingestor", "label": "pipeline"},
        {"from": "router", "to": "pathfinder", "label": "who is connected"},
        {"from": "router", "to": "librarian", "label": "ask"},
        {"from": "router", "to": "architect", "label": "how does this work"},
        {"from": "router", "to": "scribe", "label": "sync prompts"},
    ],
}


def _n(
    node_id: str,
    label: str,
    kind: str,
    detail: str,
    layer: int,
    row: int,
) -> dict[str, Any]:
    return {
        "id": node_id,
        "label": label,
        "kind": kind,
        "detail": detail,
        "layer": layer,
        "row": row,
    }


HIGH_LEVEL_GRAPH: dict[str, list[dict[str, Any]]] = {
    "nodes": [
        _n("people", "Operators", "start", "100–1000 person teams", 0, 0),
        _n("channels", "Channels", "start", "Folder · IMAP · Telegram", 0, 1),
        _n("workspace", "Workspace", "app", ":3000 operators", 1, 0),
        _n("admin", "Admin", "app", ":3001 control plane", 1, 1),
        _n("orchestrator", "Orchestrator", "router", "LangGraph router", 2, 1),
        _n("intake", "Intake", "agent", "Watchman · Mailroom · Courier", 3, 0),
        _n("library", "Library", "agent", "Reader · Taxonomist", 3, 1),
        _n("line", "Document line", "agent", "Parser → Triage → Clerk", 3, 2),
        _n("memory", "GraphRAG", "agent", "Chunker · Graphsmith · Pathfinder", 4, 0),
        _n("ledger", "Ledger", "agent", "Extractor · Recorder", 4, 1),
        _n("governance", "Governance", "agent", "Reviewer · Architect · Scribe", 4, 2),
        _n("postgres", "Postgres", "store", "Catalog + SQL rows", 5, 0),
        _n("qdrant", "Qdrant", "store", "Chunk vectors", 5, 1),
        _n("neo4j", "Neo4j", "store", "Entities + relations", 5, 2),
        _n("ollama", "Ollama", "store", "Local LLM", 5, 3),
    ],
    "edges": [
        {"from": "people", "to": "workspace", "label": "work"},
        {"from": "people", "to": "admin", "label": "govern"},
        {"from": "people", "to": "channels", "label": "send"},
        {"from": "channels", "to": "intake", "label": "files"},
        {"from": "workspace", "to": "orchestrator", "label": "chat"},
        {"from": "admin", "to": "orchestrator", "label": "catalog"},
        {"from": "admin", "to": "postgres", "label": "writes"},
        {"from": "orchestrator", "to": "intake", "label": "route"},
        {"from": "orchestrator", "to": "library", "label": ""},
        {"from": "orchestrator", "to": "line", "label": ""},
        {"from": "orchestrator", "to": "memory", "label": ""},
        {"from": "orchestrator", "to": "ledger", "label": ""},
        {"from": "orchestrator", "to": "governance", "label": ""},
        {"from": "intake", "to": "library", "label": "inbox"},
        {"from": "library", "to": "line", "label": "opt-in"},
        {"from": "library", "to": "workspace", "label": "calendar"},
        {"from": "line", "to": "memory", "label": "knowledge"},
        {"from": "line", "to": "ledger", "label": "structured"},
        {"from": "line", "to": "governance", "label": "exceptions"},
        {"from": "memory", "to": "qdrant", "label": "chunks"},
        {"from": "memory", "to": "neo4j", "label": "entities"},
        {"from": "memory", "to": "ollama", "label": "answer"},
        {"from": "ledger", "to": "postgres", "label": "rows"},
        {"from": "governance", "to": "channels", "label": "notify"},
    ],
}

DETAIL_GRAPH: dict[str, list[dict[str, Any]]] = {
    "nodes": [
        _n("folder", "Drop folder", "start", "inbox / documents", 0, 0),
        _n("email", "Mailbox", "start", "IMAP attachments", 0, 1),
        _n("telegram", "Telegram", "start", "Bot files / notify", 0, 2),
        _n("workspace", "Workspace", "app", ":3000", 0, 3),
        _n("admin", "Admin", "app", ":3001", 0, 4),
        _n("watchman", "Watchman", "agent", "Sees new files", 1, 0),
        _n("mailroom", "Mailroom", "agent", "Downloads attachments", 1, 1),
        _n("sentinel", "Sentinel", "agent", "Classifies the letter", 2, 5),
        _n("courier", "Courier", "agent", "Telegram in / out", 1, 2),
        _n("teams", "Teams", "agent", "Parked webhook", 1, 6),
        _n("post", "Post", "agent", "Parked SMTP", 1, 7),
        _n("orchestrator", "Orchestrator", "router", "Routes specialists", 1, 3),
        _n("parser", "Parser", "agent", "PDF XLSX PPT PPTX DOC DOCX TXT", 2, 0),
        _n("reader", "Reader", "agent", "OCR + first two pages", 2, 4),
        _n("ingestor", "Ingestor", "agent", "Runs the whole line", 2, 1),
        _n("architect", "Architect", "agent", "Explains the map", 2, 2),
        _n("scribe", "Scribe", "agent", "Keeps prompts in sync", 2, 3),
        _n("triage", "Triage", "agent", "invoice / policy / …", 3, 0),
        _n("taxonomist", "Taxonomist", "agent", "Two-level taxonomy", 3, 4),
        _n("chunker", "Chunker", "agent", "Split + embed", 4, 0),
        _n("extractor", "Extractor", "agent", "Structured fields", 4, 1),
        _n("clerk", "Clerk", "agent", "classified/{class}/{subclass}", 4, 2),
        _n("reviewer", "Reviewer", "agent", "Human gate", 4, 3),
        _n("qdrant", "Qdrant", "store", "Chunk vectors", 4, 4),
        _n("postgres", "Postgres", "store", "Catalog + ledger", 4, 5),
        _n("graphsmith", "Graphsmith", "agent", "Entities in Neo4j", 5, 0),
        _n("recorder", "Recorder", "agent", "SQL rows", 5, 1),
        _n("pathfinder", "Pathfinder", "agent", "Who is connected", 5, 2),
        _n("librarian", "Librarian", "agent", "Answer with GraphRAG", 5, 3),
        _n("neo4j", "Neo4j", "store", "Entity graph", 5, 4),
        _n("ollama", "Ollama", "store", "Local LLM", 5, 5),
    ],
    "edges": [
        {"from": "folder", "to": "watchman", "label": "file arrives"},
        {"from": "email", "to": "mailroom", "label": "attachment"},
        {"from": "email", "to": "sentinel", "label": "letter"},
        {"from": "mailroom", "to": "sentinel", "label": "stored letter"},
        {"from": "sentinel", "to": "pathfinder", "label": "party"},
        {"from": "pathfinder", "to": "recorder", "label": "brief book"},
        {"from": "recorder", "to": "reviewer", "label": "brief"},
        {"from": "reviewer", "to": "courier", "label": "brief"},
        {"from": "reviewer", "to": "teams", "label": "teams"},
        {"from": "reviewer", "to": "post", "label": "mail"},
        {"from": "telegram", "to": "courier", "label": "update"},
        {"from": "courier", "to": "watchman", "label": "saved file"},
        {"from": "watchman", "to": "reader", "label": "handoff"},
        {"from": "mailroom", "to": "watchman", "label": "saved"},
        {"from": "workspace", "to": "orchestrator", "label": "chat"},
        {"from": "admin", "to": "orchestrator", "label": "manage"},
        {"from": "orchestrator", "to": "ingestor", "label": "pipeline"},
        {"from": "orchestrator", "to": "architect", "label": "how does this work"},
        {"from": "orchestrator", "to": "scribe", "label": "sync prompts"},
        {"from": "reader", "to": "taxonomist", "label": "first pages"},
        {"from": "taxonomist", "to": "clerk", "label": "file"},
        {"from": "taxonomist", "to": "workspace", "label": "calendar"},
        {"from": "taxonomist", "to": "chunker", "label": "opt-in RAG"},
        {"from": "ingestor", "to": "parser", "label": "run line"},
        {"from": "parser", "to": "triage", "label": "text"},
        {"from": "triage", "to": "chunker", "label": "knowledge"},
        {"from": "triage", "to": "extractor", "label": "structured"},
        {"from": "triage", "to": "clerk", "label": "file"},
        {"from": "chunker", "to": "graphsmith", "label": "chunks"},
        {"from": "chunker", "to": "qdrant", "label": "upsert"},
        {"from": "graphsmith", "to": "pathfinder", "label": "entities"},
        {"from": "graphsmith", "to": "neo4j", "label": "write"},
        {"from": "pathfinder", "to": "librarian", "label": "neighbors"},
        {"from": "pathfinder", "to": "neo4j", "label": "1-hop"},
        {"from": "extractor", "to": "recorder", "label": "fields"},
        {"from": "extractor", "to": "reviewer", "label": "low confidence"},
        {"from": "recorder", "to": "postgres", "label": "rows"},
        {"from": "reviewer", "to": "courier", "label": "ask a human"},
        {"from": "librarian", "to": "qdrant", "label": "similar"},
        {"from": "librarian", "to": "ollama", "label": "complete"},
        {"from": "admin", "to": "postgres", "label": "catalog"},
    ],
}

RAG_METHOD_GRAPH: dict[str, list[dict[str, Any]]] = {
    "nodes": [
        _n("document", "Document", "document", "PDF / XLSX / PPTX", 0, 0),
        _n("query", "Question", "start", "Workspace chat", 0, 1),
        _n("chunker", "Chunker", "agent", "Split text", 1, 0),
        _n("graphsmith", "Graphsmith", "agent", "Extract entities", 1, 1),
        _n("pathfinder", "Pathfinder", "agent", "Walk relations", 1, 2),
        _n("librarian", "Librarian", "agent", "Answer", 1, 3),
        _n("qdrant", "Qdrant", "store", "Vector chunks", 2, 0),
        _n("neo4j", "Neo4j", "store", "Entity graph", 2, 1),
        _n("hybrid", "Hybrid retrieve", "tool", "Chunks + 1-hop neighbors", 3, 0),
        _n("answer", "Answer", "app", "Cited excerpts + entities", 4, 0),
    ],
    "edges": [
        {"from": "document", "to": "chunker", "label": "parse"},
        {"from": "document", "to": "graphsmith", "label": "text"},
        {"from": "chunker", "to": "qdrant", "label": "embed"},
        {"from": "graphsmith", "to": "neo4j", "label": "MENTIONS / RELATES"},
        {"from": "query", "to": "pathfinder", "label": "who is connected"},
        {"from": "query", "to": "librarian", "label": "ask"},
        {"from": "pathfinder", "to": "neo4j", "label": "lookup"},
        {"from": "librarian", "to": "qdrant", "label": "similar"},
        {"from": "qdrant", "to": "hybrid", "label": "chunks"},
        {"from": "neo4j", "to": "hybrid", "label": "entities"},
        {"from": "hybrid", "to": "answer", "label": "context"},
        {"from": "librarian", "to": "answer", "label": "write"},
    ],
}

HOP_LINE_GRAPH: dict[str, list[dict[str, Any]]] = {
    "nodes": [
        _n("watchman", "Watchman", "agent", "Landed", 0, 0),
        _n("reader", "Reader", "agent", "First pages", 1, 0),
        _n("taxonomist", "Taxonomist", "agent", "Two-level class", 2, 0),
        _n("clerk", "Clerk", "agent", "classified/{class}/{subclass}", 3, 0),
        _n("chunker", "GraphRAG", "store", "Promoted", 4, 0),
        _n("reviewer", "Reviewer", "tool", "Human gate", 2, 1),
    ],
    "edges": [
        {"from": "watchman", "to": "reader", "label": "handoff"},
        {"from": "reader", "to": "taxonomist", "label": "first pages"},
        {"from": "taxonomist", "to": "clerk", "label": "file"},
        {"from": "clerk", "to": "chunker", "label": "opt-in RAG"},
        {"from": "taxonomist", "to": "reviewer", "label": "exceptions"},
    ],
}

PIPELINE_GRAPH: dict[str, list[dict[str, Any]]] = {
    "nodes": [
        {"id": "folder", "label": "Drop folder", "kind": "start", "detail": "data/documents/inbox"},
        {"id": "email", "label": "Mailbox", "kind": "start", "detail": "IMAP attachments"},
        {"id": "telegram", "label": "Telegram", "kind": "start", "detail": "Bot messages / files"},
        {"id": "watchman", "label": "Watchman", "kind": "agent", "detail": "Sees new files"},
        {"id": "mailroom", "label": "Mailroom", "kind": "agent", "detail": "Downloads to inbox"},
        {"id": "sentinel", "label": "Sentinel", "kind": "agent", "detail": "Classifies the letter"},
        {"id": "parser", "label": "Parser", "kind": "agent", "detail": "PDF XLSX PPT PPTX DOC DOCX"},
        {"id": "reader", "label": "Reader", "kind": "agent", "detail": "OCR + first two pages"},
        {"id": "taxonomist", "label": "Taxonomist", "kind": "agent", "detail": "Two-level taxonomy"},
        {"id": "triage", "label": "Triage", "kind": "agent", "detail": "invoice / policy / …"},
        {"id": "chunker", "label": "Chunker", "kind": "agent", "detail": "Qdrant vectors"},
        {"id": "graphsmith", "label": "Graphsmith", "kind": "agent", "detail": "Neo4j entities"},
        {"id": "extractor", "label": "Extractor", "kind": "agent", "detail": "Fields via LLM"},
        {"id": "recorder", "label": "Recorder", "kind": "store", "detail": "Postgres rows"},
        {"id": "pathfinder", "label": "Pathfinder", "kind": "agent", "detail": "GraphRAG"},
        {"id": "librarian", "label": "Librarian", "kind": "agent", "detail": "Ask the corpus"},
        {"id": "reviewer", "label": "Reviewer", "kind": "agent", "detail": "Human gate"},
        {"id": "courier", "label": "Courier", "kind": "agent", "detail": "Telegram notify"},
        {"id": "teams", "label": "Teams", "kind": "agent", "detail": "Parked webhook"},
        {"id": "post", "label": "Post", "kind": "agent", "detail": "Parked SMTP"},
        {"id": "clerk", "label": "Clerk", "kind": "agent", "detail": "classified/{class}/{subclass}"},
    ],
    "edges": [
        {"from": "folder", "to": "watchman", "label": "file arrives"},
        {"from": "email", "to": "mailroom", "label": "attachment"},
        {"from": "email", "to": "sentinel", "label": "letter"},
        {"from": "mailroom", "to": "sentinel", "label": "stored letter"},
        {"from": "sentinel", "to": "pathfinder", "label": "party"},
        {"from": "pathfinder", "to": "recorder", "label": "brief book"},
        {"from": "recorder", "to": "reviewer", "label": "brief"},
        {"from": "reviewer", "to": "courier", "label": "brief"},
        {"from": "reviewer", "to": "teams", "label": "teams"},
        {"from": "reviewer", "to": "post", "label": "mail"},
        {"from": "telegram", "to": "courier", "label": "update"},
        {"from": "courier", "to": "watchman", "label": "saved file"},
        {"from": "watchman", "to": "reader", "label": "handoff"},
        {"from": "mailroom", "to": "watchman", "label": "saved"},
        {"from": "reader", "to": "taxonomist", "label": "first pages"},
        {"from": "taxonomist", "to": "clerk", "label": "file"},
        {"from": "taxonomist", "to": "chunker", "label": "opt-in RAG"},
        {"from": "parser", "to": "triage", "label": "text"},
        {"from": "triage", "to": "chunker", "label": "knowledge"},
        {"from": "triage", "to": "extractor", "label": "structured"},
        {"from": "chunker", "to": "graphsmith", "label": "chunks"},
        {"from": "graphsmith", "to": "pathfinder", "label": "entities"},
        {"from": "pathfinder", "to": "librarian", "label": "context"},
        {"from": "extractor", "to": "recorder", "label": "SQL"},
        {"from": "extractor", "to": "reviewer", "label": "low confidence"},
        {"from": "reviewer", "to": "courier", "label": "ask a human"},
        {"from": "triage", "to": "clerk", "label": "file"},
    ],
}

_compiled = None


def get_compiled_graph():
    global _compiled
    if _compiled is None:
        _compiled = build_graph()
    return _compiled

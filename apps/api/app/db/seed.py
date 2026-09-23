from __future__ import annotations

import json

from sqlalchemy.orm import Session

from app.config import settings
from app.db.models import Agent, AgentTool, App, Tool

CANONICAL_ROUTES = [
    {"match": ["telegram", "courier"], "agent": "courier"},
    {"match": ["email", "imap", "mailbox", "attachment", "mailroom"], "agent": "mailroom"},
    {"match": ["watch", "drop folder", "inbox folder", "waiting for a file"], "agent": "watchman"},
    {"match": ["classify", "triage", "what type"], "agent": "triage"},
    {"match": ["chunk"], "agent": "chunker"},
    {"match": ["extract entities", "build the knowledge graph", "graphsmith"], "agent": "graphsmith"},
    {
        "match": ["graphrag", "who is connected", "related to", "which entities", "pathfinder"],
        "agent": "pathfinder",
    },
    {"match": ["extract", "structured", "to sql", "into sql"], "agent": "extractor"},
    {"match": ["records", "sql rows"], "agent": "recorder"},
    {"match": ["exception", "review", "human gate", "approve"], "agent": "reviewer"},
    {"match": ["organize", "classified", "file them"], "agent": "clerk"},
    {"match": ["parse the", "parse files"], "agent": "parser"},
    {"match": ["ingest", "index", "reindex", "pipeline"], "agent": "ingestor"},
    {
        "match": ["architecture", "how does", "what agents", "platform", "langgraph"],
        "agent": "architect",
    },
    {"match": ["sync docs", "sync the context prompt", "refresh the context prompt", "update AGENTS.md", "scribe"], "agent": "scribe"},
    {"match": ["*"], "agent": "librarian"},
]


def seed_catalog(db: Session) -> None:
    apps = [
        App(
            slug="workspace",
            name="Workspace",
            kind="experience",
            base_url=settings.workspace_url,
            status="live",
            summary="Operator-facing portal: documents, knowledge chat, and extracted records.",
        ),
        App(
            slug="admin",
            name="Admin",
            kind="admin",
            base_url=settings.admin_url,
            status="live",
            summary="Control plane for apps, tools, and agents.",
        ),
    ]
    tools = [
        _tool("intake.list", "Watch inbox folder", "List files waiting in the drop folder / inbox.", "builtin:intake.list"),
        _tool("intake.poll_mail", "Poll mailbox", "Download supported email attachments into the inbox folder.", "builtin:intake.poll_mail"),
        _tool("documents.parse", "Parse documents", "Extract text from PDF, XLSX, PPTX, DOCX, CSV.", "builtin:documents.parse"),
        _tool("documents.classify", "Classify documents", "Triage files into invoice, contract, policy, report, spreadsheet, presentation, form, other.", "builtin:documents.classify"),
        _tool("documents.chunk", "Chunk for RAG", "Split parsed text and upsert chunks into Qdrant.", "builtin:documents.chunk"),
        _tool("documents.file", "File documents", "Move processed files into classified/{type} folders.", "builtin:documents.file"),
        _tool("documents.list", "List documents", "List files and their pipeline status.", "builtin:documents.list"),
        _tool("knowledge.ingest", "Run pipeline", "Parse, classify, chunk, extract to SQL, index, and file every pending document.", "builtin:knowledge.ingest"),
        _tool("knowledge.search", "GraphRAG search", "Hybrid retrieve: Qdrant vectors plus Neo4j entity neighbors.", "builtin:knowledge.search"),
        _tool("knowledge.graph_build", "Build knowledge graph", "Extract entities and relations from documents into Neo4j (Graphsmith).", "builtin:knowledge.graph_build"),
        _tool("knowledge.graph_search", "Search entities", "Look up entities and 1-hop neighbors in Neo4j (Pathfinder).", "builtin:knowledge.graph_search"),
        _tool("telegram.poll", "Poll Telegram", "Download supported files the bot was sent, and list recent texts.", "builtin:telegram.poll"),
        _tool("telegram.send", "Send Telegram", "Send a status message to the configured Telegram chat.", "builtin:telegram.send"),
        _tool("review.list", "List exceptions", "Show files and extracts that need a human (Reviewer).", "builtin:review.list"),
        _tool("records.extract", "Extract records", "Turn invoices and spreadsheets into structured rows (heuristic, optional LLM).", "builtin:records.extract"),
        _tool("records.list", "List SQL records", "Read structured rows written to Postgres.", "builtin:records.list"),
        _tool("models.list", "List Models", "List Ollama models available on this server.", "builtin:models.list"),
        _tool("platform.explain", "Explain Platform", "Describe live apps, agents, tools, and how work is routed.", "builtin:platform.explain"),
        _tool("docs.sync", "Sync context prompt", "Rewrite the generated roster in AGENTS.md and HOW_IT_WORKS from the live catalog (Scribe).", "builtin:docs.sync"),
    ]
    agents = [
        Agent(
            slug="orchestrator",
            name="Orchestrator",
            role="router",
            status="live",
            summary="Routes each request to a specialist agent.",
            model=settings.ollama_chat_model,
            system_prompt="You are the Atrium orchestrator. Route work; do not invent tools.",
            config_json=json.dumps({"routes": CANONICAL_ROUTES}),
        ),
        Agent(
            slug="watchman",
            name="Watchman",
            role="specialist",
            status="live",
            summary="Waits on the drop folder / inbox and reports files that have arrived.",
            model=settings.ollama_chat_model,
            system_prompt="You watch the documents inbox. Report pending files; do not guess contents.",
        ),
        Agent(
            slug="mailroom",
            name="Mailroom",
            role="specialist",
            status="live",
            summary="Polls IMAP, downloads PDF/XLSX/PPTX attachments onto the server inbox.",
            model=settings.ollama_chat_model,
            system_prompt="You collect email attachments. If IMAP is not configured, say exactly how to set it.",
        ),
        Agent(
            slug="parser",
            name="Parser",
            role="specialist",
            status="live",
            summary="Reads PDF, Excel, PowerPoint, and Word into plain text.",
            model=settings.ollama_chat_model,
            system_prompt="You parse office files. Prefer tool output over guessing.",
        ),
        Agent(
            slug="triage",
            name="Triage",
            role="specialist",
            status="live",
            summary="Classifies each file so later agents know whether to RAG it or extract it to SQL.",
            model=settings.ollama_chat_model,
            system_prompt="You classify documents. Use the classify tool.",
        ),
        Agent(
            slug="chunker",
            name="Chunker",
            role="specialist",
            status="live",
            summary="Splits text and sends chunks to Qdrant. Graphsmith then hangs entities on those chunks.",
            model=settings.ollama_chat_model,
            system_prompt="You chunk documents for retrieval. Report chunk counts.",
        ),
        Agent(
            slug="extractor",
            name="Extractor",
            role="specialist",
            status="live",
            summary="Asks the LLM (or heuristics) for structured fields, then writes them to Postgres.",
            model=settings.ollama_chat_model,
            system_prompt="You extract structured data for SQL. Prefer tool results.",
        ),
        Agent(
            slug="recorder",
            name="Recorder",
            role="specialist",
            status="live",
            summary="Reads the SQL table of extracted rows (invoices, spreadsheet lines).",
            model=settings.ollama_chat_model,
            system_prompt="You report extracted SQL records. Do not invent rows.",
        ),
        Agent(
            slug="clerk",
            name="Clerk",
            role="specialist",
            status="live",
            summary="Files processed documents into classified/{type} folders.",
            model=settings.ollama_chat_model,
            system_prompt="You organize files on disk after triage.",
        ),
        Agent(
            slug="ingestor",
            name="Ingestor",
            role="specialist",
            status="live",
            summary="Runs the full line: parse → classify → chunk → GraphRAG graph → extract/SQL → file.",
            model=settings.ollama_chat_model,
            system_prompt="You run the document pipeline. Prefer tool results over guessing.",
        ),
        Agent(
            slug="librarian",
            name="Librarian",
            role="specialist",
            status="live",
            summary="Answers questions with GraphRAG: similar chunks plus related entities from Neo4j.",
            model=settings.ollama_chat_model,
            system_prompt=(
                "You are Atrium's librarian. Answer using document excerpts AND the related entities "
                "listed with them (GraphRAG). If neighbors contradict the excerpts, prefer excerpts. "
                "Cite filenames. Be concise."
            ),
        ),
        Agent(
            slug="graphsmith",
            name="Graphsmith",
            role="specialist",
            status="live",
            summary="Turns chunks into a knowledge graph: entities, mentions, relations in Neo4j.",
            model=settings.ollama_chat_model,
            system_prompt="You build the knowledge graph. Prefer tool results. Do not invent entities.",
        ),
        Agent(
            slug="pathfinder",
            name="Pathfinder",
            role="specialist",
            status="live",
            summary="GraphRAG retrieve: who is connected to whom, which files mention an entity.",
            model=settings.ollama_chat_model,
            system_prompt="You search the entity graph. Report neighbors and files. Do not guess.",
        ),
        Agent(
            slug="courier",
            name="Courier",
            role="specialist",
            status="live",
            summary="Telegram channel: receive files into the inbox, notify when work finishes.",
            model=settings.ollama_chat_model,
            system_prompt="You are the Telegram agent. If the bot token is missing, say how to set TELEGRAM_BOT_TOKEN.",
        ),
        Agent(
            slug="reviewer",
            name="Reviewer",
            role="specialist",
            status="live",
            summary="Human gate: unclassified files, failed ingest, weak invoice rows.",
            model=settings.ollama_chat_model,
            system_prompt="You list exceptions that need a person. Do not auto-approve.",
        ),
        Agent(
            slug="architect",
            name="Architect",
            role="specialist",
            status="live",
            summary="Explains the live platform graph so humans and agents can see how work is routed.",
            model=settings.ollama_chat_model,
            system_prompt="You explain Atrium's architecture from the platform.explain tool. Be concrete.",
        ),
        Agent(
            slug="scribe",
            name="Scribe",
            role="specialist",
            status="live",
            summary="Keeps AGENTS.md and HOW_IT_WORKS roster in sync with the live Postgres catalog.",
            model=settings.ollama_chat_model,
            system_prompt="You refresh the north-star prompt from the catalog. Prefer the docs.sync tool. Do not invent agents.",
        ),
    ]

    for item in apps:
        _upsert_app(db, item)
    for item in tools:
        _upsert_tool(db, item)
    db.flush()
    for item in agents:
        _upsert_agent(db, item)
    db.flush()

    assignments = {
        "watchman": ["intake.list", "documents.list"],
        "mailroom": ["intake.poll_mail"],
        "parser": ["documents.parse"],
        "triage": ["documents.classify"],
        "chunker": ["documents.chunk"],
        "extractor": ["records.extract"],
        "recorder": ["records.list"],
        "clerk": ["documents.file"],
        "ingestor": ["knowledge.ingest", "documents.list"],
        "librarian": ["knowledge.search"],
        "graphsmith": ["knowledge.graph_build"],
        "pathfinder": ["knowledge.graph_search"],
        "courier": ["telegram.poll", "telegram.send"],
        "reviewer": ["review.list"],
        "orchestrator": ["models.list"],
        "architect": ["platform.explain"],
        "scribe": ["docs.sync"],
    }
    agents_by_slug = {row.slug: row for row in db.query(Agent).all()}
    tools_by_slug = {row.slug: row for row in db.query(Tool).all()}
    for agent_slug, tool_slugs in assignments.items():
        agent = agents_by_slug.get(agent_slug)
        if agent is None:
            continue
        for tool_slug in tool_slugs:
            tool = tools_by_slug[tool_slug]
            exists = (
                db.query(AgentTool)
                .filter(AgentTool.agent_id == agent.id, AgentTool.tool_id == tool.id)
                .first()
            )
            if not exists:
                db.add(AgentTool(agent_id=agent.id, tool_id=tool.id))
    _refresh_orchestrator_routes(db)
    db.commit()
    from app.services.scribe import try_sync_docs

    try_sync_docs(db)


def _tool(slug: str, name: str, summary: str, entrypoint: str) -> Tool:
    return Tool(
        slug=slug,
        name=name,
        kind="builtin",
        status="live",
        summary=summary,
        entrypoint=entrypoint,
        config_json="{}",
    )


def _refresh_orchestrator_routes(db: Session) -> None:
    row = db.query(Agent).filter(Agent.slug == "orchestrator").first()
    if row is None:
        return
    payload = json.loads(row.config_json or "{}")
    payload["routes"] = CANONICAL_ROUTES
    row.config_json = json.dumps(payload)


def _upsert_app(db: Session, incoming: App) -> None:
    row = db.query(App).filter(App.slug == incoming.slug).first()
    if row:
        row.name = incoming.name
        row.kind = incoming.kind
        row.base_url = incoming.base_url
        row.summary = incoming.summary
        if row.status == "planned":
            row.status = incoming.status
        return
    db.add(incoming)


def _upsert_tool(db: Session, incoming: Tool) -> None:
    row = db.query(Tool).filter(Tool.slug == incoming.slug).first()
    if row:
        row.name = incoming.name
        row.kind = incoming.kind
        row.summary = incoming.summary
        row.entrypoint = incoming.entrypoint
        return
    db.add(incoming)


def _upsert_agent(db: Session, incoming: Agent) -> None:
    row = db.query(Agent).filter(Agent.slug == incoming.slug).first()
    if row:
        row.summary = incoming.summary
        row.role = incoming.role
        if incoming.system_prompt:
            row.system_prompt = incoming.system_prompt
        if incoming.config_json and incoming.slug == "orchestrator":
            row.config_json = incoming.config_json
        return
    db.add(incoming)

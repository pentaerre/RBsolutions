from __future__ import annotations

import json

from sqlalchemy.orm import Session

from app.config import settings
from app.db.models import Agent, AgentTool, App, Tool
from app.services.llm_agents import assigned_model
from app.services.taxonomy import INSTANCES, instance_config, instance_status, is_taxonomist

CANONICAL_ROUTES = [
    {"match": ["telegram", "courier"], "agent": "courier"},
    {"match": ["teams worker", "aviso teams", "teams channel"], "agent": "teams"},
    {"match": ["post worker", "aviso por smtp", "outbound mail"], "agent": "post"},
    {"match": ["email", "imap", "mailbox", "attachment", "mailroom"], "agent": "mailroom"},
    {
        "match": [
            "sentinel",
            "shared inbox",
            "bandeja compartida",
            "churn",
            "opportunity radar",
            "riesgo legal",
            "operations brief",
            "señales de dirección",
        ],
        "agent": "sentinel",
    },
    {"match": ["watch", "drop folder", "inbox folder", "waiting for a file", "new arrivals"], "agent": "watchman"},
    {"match": ["ocr", "read the document", "first two pages", "scanned pdf", "reader"], "agent": "reader"},
    {
        "match": ["aircraft taxonom", "avion taxonom", "taxonomist-aircraft"],
        "agent": "taxonomist-aircraft",
    },
    {
        "match": ["car taxonom", "automotive taxonom", "taxonomist-car"],
        "agent": "taxonomist-car",
    },
    {
        "match": ["factory taxonom", "planta taxonom", "taxonomist-factory"],
        "agent": "taxonomist-factory",
    },
    {
        "match": ["bars taxonom", "horeca", "distribuidor", "taxonomist-bars"],
        "agent": "taxonomist-bars",
    },
    {
        "match": ["advice taxonom", "asesoria", "laboral fiscal", "taxonomist-advice"],
        "agent": "taxonomist-advice",
    },
    {
        "match": ["taxonomy", "taxonomist", "two-level", "library calendar", "filing tree", "e&p class"],
        "agent": "taxonomist",
    },
    {"match": ["promote to rag", "add to rag", "index selected"], "agent": "ingestor"},
    {"match": ["classify", "triage", "what type"], "agent": "triage"},
    {"match": ["chunk"], "agent": "chunker"},
    {"match": ["extract entities", "build the knowledge graph", "graphsmith"], "agent": "graphsmith"},
    {
        "match": [
            "graphrag",
            "who is connected",
            "related to",
            "which entities",
            "pathfinder",
            "party in the graph",
            "vecino en el grafo",
        ],
        "agent": "pathfinder",
    },
    {"match": ["extract", "structured", "to sql", "into sql"], "agent": "extractor"},
    {"match": ["records", "sql rows", "sql book", "libro sql"], "agent": "recorder"},
    {"match": ["exception", "review", "human gate", "approve", "hold the brief", "retener el brief"], "agent": "reviewer"},
    {"match": ["organize", "classified", "file them", "folder tree", "estructura de carpetas", "filing cabinet"], "agent": "clerk"},
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
            summary="Operator-facing portal: calendar of arrivals, taxonomy library, documents, and knowledge chat.",
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
        _tool("intake.register", "Register arrivals", "Register new inbox files (including subfolders) without sending them to RAG.", "builtin:intake.register"),
        _tool("intake.poll_mail", "Poll mailbox", "Download supported email attachments into the inbox folder.", "builtin:intake.poll_mail"),
        _tool(
            "intake.store_letters",
            "Store letters",
            "Mailroom saves a shared-inbox letter for Sentinel. The judge does not ingest mail.",
            "builtin:intake.store_letters",
        ),
        _tool(
            "signals.judge",
            "Judge a letter",
            "Classify a stored letter as legal, opportunity, or churn and write the brief with subject and sender. Local patterns. No 32b call.",
            "builtin:signals.judge",
        ),
        _tool(
            "signals.graph",
            "Cross the party",
            "Pathfinder looks the party up in Neo4j. The brief names a project only when that neighbor exists.",
            "builtin:signals.graph",
        ),
        _tool(
            "signals.book",
            "Read the SQL book",
            "Recorder reads SQL rows. A figure is written only when that value is already a row.",
            "builtin:signals.book",
        ),
        _tool(
            "signals.notify",
            "Notify the channel",
            "Send a high brief through the channel agent on the notify knob. An inactive agent does not count as delivered.",
            "builtin:signals.notify",
        ),
        _tool(
            "signals.scan",
            "Run the brief line",
            "Mailroom stores, Sentinel judges, Pathfinder crosses the graph, Recorder reads the book, Reviewer holds, then the channel notifies.",
            "builtin:signals.scan",
        ),
        _tool(
            "signals.list",
            "List direction briefs",
            "List open operational signals waiting for a human.",
            "builtin:signals.list",
        ),
        _tool("documents.parse", "Parse documents", "Extract text from PDF, XLSX, PPTX, PPT, DOCX, DOC, CSV, TXT.", "builtin:documents.parse"),
        _tool("documents.read", "Read first pages", "OCR/extract the first two pages, write a summary and keywords (Reader).", "builtin:documents.read"),
        _tool("documents.classify", "Classify documents", "Triage files into invoice, contract, policy, report, spreadsheet, presentation, form, other.", "builtin:documents.classify"),
        _tool("taxonomy.run", "Run taxonomy", "Two-level labels from path + filename + readable text. Clerk creates the folders and moves the files.", "builtin:taxonomy.run"),
        _tool("taxonomy.list", "List taxonomy", "List classified library documents with filters.", "builtin:taxonomy.list"),
        _tool("taxonomy.get", "Get document card", "Show summary, bytes, created date, absolute path, and keywords for one document.", "builtin:taxonomy.get"),
        _tool("documents.chunk", "Chunk for RAG", "Split parsed text and upsert chunks into Qdrant.", "builtin:documents.chunk"),
        _tool("documents.file", "File documents", "Clerk moves taxonomy-classified files into classified/{class}/{subclass}, then leftover IDP files by type.", "builtin:documents.file"),
        _tool("folders.ensure", "Ensure classified folders", "Create classified/{class}/{subclass} from the live Taxonomist tree. Does not move files.", "builtin:folders.ensure"),
        _tool("folders.list", "List classified folders", "Read the organized classified/ tree on disk.", "builtin:folders.list"),
        _tool("documents.list", "List documents", "List files and their pipeline status.", "builtin:documents.list"),
        _tool("knowledge.ingest", "Run pipeline", "Parse, classify, chunk, extract to SQL, index, and file every pending document.", "builtin:knowledge.ingest"),
        _tool("knowledge.promote", "Promote to GraphRAG", "Index only the documents an operator selected. The library path never dumps everything into RAG.", "builtin:knowledge.promote"),
        _tool("knowledge.search", "GraphRAG search", "Hybrid retrieve: Qdrant vectors plus Neo4j entity neighbors.", "builtin:knowledge.search"),
        _tool("knowledge.graph_build", "Build knowledge graph", "Extract entities and relations from documents into Neo4j (Graphsmith).", "builtin:knowledge.graph_build"),
        _tool("knowledge.graph_search", "Search entities", "Look up entities and 1-hop neighbors in Neo4j (Pathfinder).", "builtin:knowledge.graph_search"),
        _tool("telegram.poll", "Poll Telegram", "Download supported files the bot was sent, and list recent texts.", "builtin:telegram.poll"),
        _tool("telegram.send", "Send Telegram", "Send a status message to the configured Telegram chat.", "builtin:telegram.send"),
        _tool(
            "teams.send",
            "Send Teams",
            "Post a direction brief to a Teams channel. The webhook URL stays in TEAMS_WEBHOOK_URL.",
            "builtin:teams.send",
        ),
        _tool(
            "mail.send",
            "Send mail",
            "Send a direction brief by email. SMTP settings stay in the server environment.",
            "builtin:mail.send",
        ),
        _tool("review.list", "List exceptions", "Show files and extracts that need a human (Reviewer).", "builtin:review.list"),
        _tool(
            "review.hold",
            "Hold the brief",
            "Reviewer holds an open direction brief, including the sender. It stays open when the channel agent is off.",
            "builtin:review.hold",
        ),
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
            summary="Waits on the drop folder / inbox (including subfolders) and registers arrivals. Does not dump them into RAG.",
            model=settings.ollama_chat_model,
            system_prompt="You watch the documents inbox. Register new files; never send them to RAG yourself.",
            config_json=json.dumps({"watch_path": "inbox", "recursive": True}),
        ),
        Agent(
            slug="mailroom",
            name="Mailroom",
            role="specialist",
            status="live",
            summary="Polls IMAP, downloads attachments onto the server inbox, and stores the letter. Does not classify it.",
            model=settings.ollama_chat_model,
            system_prompt="You collect email attachments and store the letter. Sentinel classifies it. If IMAP is not configured, say exactly how to set it.",
            config_json=json.dumps({"imap_folder": settings.imap_folder or "INBOX", "poll_seconds": settings.imap_poll_seconds or 0}),
        ),
        Agent(
            slug="sentinel",
            name="Sentinel",
            role="specialist",
            status="live",
            summary=(
                "Classifies a shared-inbox letter as legal, opportunity, or churn and writes the brief with subject and sender (De: name and address). "
                "Local patterns only. Does not call the 32b model, does not cross Neo4j, does not read the SQL book, and does not notify."
            ),
            model="",
            system_prompt=(
                "You only classify the letter and write the brief with subject and sender. Use signals.judge and signals.list. "
                "Pathfinder crosses Neo4j, Recorder reads the SQL book, Reviewer holds the exception, and the channel agent notifies. "
                "Do not invent a project or a penalty. Do not draft a reply."
            ),
            config_json=json.dumps(
                {
                    "mailboxes": "INBOX",
                    "stale_hours": 24,
                    "signals": "legal,opportunity,churn",
                    "notify": "courier",
                    "poll_seconds": 0,
                    "roster": False,
                }
            ),
        ),
        Agent(
            slug="parser",
            name="Parser",
            role="specialist",
            status="live",
            summary="Reads PDF, Excel, PowerPoint, Word, and plain text into pages (Parser). Reader then OCRs and summarises.",
            model=settings.ollama_chat_model,
            system_prompt="You parse office files. Prefer tool output over guessing.",
        ),
        Agent(
            slug="reader",
            name="Reader",
            role="specialist",
            status="live",
            summary="OCR / best-effort extract of the first two pages: PDF, PPT/PPTX, DOC/DOCX, TXT and other readable files. Writes summary and keywords.",
            model=settings.ollama_chat_model,
            system_prompt="You read documents. OCR scanned PDFs when you can. Never index into RAG.",
            config_json=json.dumps({"read_pages": 2}),
        ),
        *[
            Agent(
                slug=item["slug"],
                name=item["name"],
                role="specialist",
                status=item.get("status") or instance_status(item["slug"]),
                summary=(
                    f"Two-level {instance_config(item['pack'])['taxonomy']['name']} taxonomy from path + filename + readable text. "
                    f"Scope {instance_config(item['pack'])['scope_path']}. Same oficio as other Taxonomists; different client tree. Does not send files to RAG."
                ),
                model=settings.ollama_chat_model,
                system_prompt="You file documents into a two-level taxonomy. Classify what the file is. Filename and Reader text beat the drop folder. An invoice under inbox/wells is still commercial/invoices.",
                config_json=json.dumps(instance_config(item["pack"])),
            )
            for item in INSTANCES
        ],
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
            summary="Reads the SQL table of extracted rows. On a brief, writes a figure only when that value is already a row.",
            model=settings.ollama_chat_model,
            system_prompt="You read SQL rows. On a brief, write a figure only when that value is already a row. Do not invent rows.",
        ),
        Agent(
            slug="clerk",
            name="Clerk",
            role="specialist",
            status="live",
            summary="Creates classified/{class}/{subclass} from the live Taxonomist tree and moves labeled files there. Also files the IDP line by type.",
            model="",
            system_prompt="You own the classified folder tree: create it, read it, and move labeled files into it. Do not classify.",
        ),
        Agent(
            slug="ingestor",
            name="Ingestor",
            role="specialist",
            status="live",
            summary="Runs the full IDP line when asked: parse → classify → chunk → GraphRAG graph → extract/SQL → file. Not used for every inbox arrival.",
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
            summary="GraphRAG retrieve: who is connected to whom. On a brief, names a project only when that neighbor exists.",
            model=settings.ollama_chat_model,
            system_prompt="You search the entity graph. Report neighbors and files. On a brief, name a project only when that neighbor exists. Do not guess.",
        ),
        Agent(
            slug="courier",
            name="Courier",
            role="specialist",
            status="live",
            summary="Telegram chatbot: receive files into the inbox, and deliver Sentinel briefs with subject and sender.",
            model=settings.ollama_chat_model,
            system_prompt="You are the Telegram agent. If the bot token is missing, say how to set TELEGRAM_BOT_TOKEN.",
        ),
        Agent(
            slug="teams",
            name="Teams",
            role="specialist",
            status="disabled",
            summary="Teams worker for the same Sentinel brief. Parked until enabled. Set TEAMS_WEBHOOK_URL; the secret stays off the graph.",
            model="",
            system_prompt="You post a direction brief to Teams. If the webhook is missing, say how to set TEAMS_WEBHOOK_URL.",
            config_json=json.dumps({"roster": False}),
        ),
        Agent(
            slug="post",
            name="Post",
            role="specialist",
            status="disabled",
            summary="Outbound mail worker for the same Sentinel brief. Parked until enabled. Set SMTP_HOST and SMTP_TO; the secret stays off the graph.",
            model="",
            system_prompt="You email a direction brief. If SMTP is missing, say how to set SMTP_HOST and SMTP_TO.",
            config_json=json.dumps({"roster": False}),
        ),
        Agent(
            slug="reviewer",
            name="Reviewer",
            role="specialist",
            status="live",
            summary="Human gate: unclassified files, failed ingest, weak invoice rows, and open direction briefs with the sender.",
            model=settings.ollama_chat_model,
            system_prompt="You hold exceptions that need a person, including an open brief and who sent it. Do not auto-approve. Do not mark a brief delivered.",
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
        "watchman": ["intake.register", "intake.list", "documents.list"],
        "mailroom": ["intake.poll_mail", "intake.store_letters"],
        "sentinel": ["signals.judge", "signals.list"],
        "parser": ["documents.parse"],
        "reader": ["documents.read"],
        **{item["slug"]: ["taxonomy.run", "taxonomy.list", "taxonomy.get"] for item in INSTANCES},
        "triage": ["documents.classify"],
        "chunker": ["documents.chunk"],
        "extractor": ["records.extract"],
        "recorder": ["records.list", "signals.book"],
        "clerk": ["documents.file", "folders.ensure", "folders.list"],
        "ingestor": ["knowledge.ingest", "knowledge.promote", "documents.list"],
        "librarian": ["knowledge.search"],
        "graphsmith": ["knowledge.graph_build"],
        "pathfinder": ["knowledge.graph_search", "signals.graph"],
        "courier": ["telegram.poll", "telegram.send"],
        "teams": ["teams.send"],
        "post": ["mail.send"],
        "reviewer": ["review.list", "review.hold"],
        "orchestrator": ["models.list", "signals.scan", "signals.notify"],
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
    _unbind_tool(db, "sentinel", "signals.scan")
    _refresh_orchestrator_routes(db)
    _enforce_one_live_taxonomist(db)
    db.commit()
    from app.services.scribe import try_sync_docs

    from app.services.knobs import ensure_taxonomist_scopes

    try_sync_docs(db)
    ensure_taxonomist_scopes(db)


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


def _unbind_tool(db: Session, agent_slug: str, tool_slug: str) -> None:
    agent = db.query(Agent).filter(Agent.slug == agent_slug).first()
    tool = db.query(Tool).filter(Tool.slug == tool_slug).first()
    if agent is None or tool is None:
        return
    db.query(AgentTool).filter(AgentTool.agent_id == agent.id, AgentTool.tool_id == tool.id).delete()


def _refresh_orchestrator_routes(db: Session) -> None:
    row = db.query(Agent).filter(Agent.slug == "orchestrator").first()
    if row is None:
        return
    payload = json.loads(row.config_json or "{}")
    payload["routes"] = CANONICAL_ROUTES
    row.config_json = json.dumps(payload)


def _enforce_one_live_taxonomist(db: Session) -> None:
    from app.services.taxonomy import exclusive_live, list_agents

    agents = list_agents(db)
    if not agents:
        return
    live = [row for row in agents if row.status == "live"]
    if len(live) == 1:
        return
    if not live:
        exclusive_live(db, "taxonomist")
        return
    preferred = next((row for row in live if row.slug == "taxonomist"), live[0])
    exclusive_live(db, preferred.slug)


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
        incoming_cfg = json.loads(incoming.config_json or "{}") if incoming.config_json else {}
        if is_taxonomist(incoming.slug, incoming_cfg):
            row.name = incoming.name
            stored = json.loads(row.config_json or "{}")
            stored.setdefault("specialist", "taxonomist")
            stored.setdefault("cadence", incoming_cfg.get("cadence") or "hour")
            stored.setdefault("scope_path", incoming_cfg.get("scope_path") or "inbox")
            if not stored.get("taxonomy") and incoming_cfg.get("taxonomy"):
                stored["taxonomy"] = incoming_cfg["taxonomy"]
            row.config_json = json.dumps(stored)
        if incoming.config_json and incoming.slug in {"watchman", "mailroom", "reader", "sentinel", "teams", "post"}:
            stored = json.loads(row.config_json or "{}")
            incoming_cfg = json.loads(incoming.config_json or "{}")
            for key, value in incoming_cfg.items():
                stored.setdefault(key, value)
            row.config_json = json.dumps(stored)
        row.model = assigned_model(row.slug, row.model)
        return
    incoming.model = assigned_model(incoming.slug, incoming.model)
    db.add(incoming)

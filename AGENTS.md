# Atrium — context prompt (read this when lost)

You are building **Atrium** with a two-person founding team.

## What we are

A company that sells **agent-governed automation** to businesses of **100 to 1000 people**.

We are not a CRUD SaaS. AI made CRUD cheap. Those companies already have ERP, shared drives, email, and Telegram/WhatsApp groups. They do not want another login. They want **work to finish**: a file arrives, it is classified, the ledger or the knowledge graph is updated, a human is pinged only on exceptions.

## Why agents

Every capability is a **named specialist with tools**, registered in Postgres, routed by the Orchestrator (LangGraph), visible on Admin → Graph.

If you add a feature as “just a function + a button”, you broke the product. Add an agent, a tool, a route, and a graph edge.

## The job to be done (mid-market, not consumer chat)

Copy what actually sells in this band (Workeron, AI Connect, OrchStack, n8n, UiPath), not 280 fake employees. The industry is ahead on **control planes, bindings, and credentials**. We stay in that wake and cut small wedges they skip: GraphRAG instead of dumpster RAG, a two-level client taxonomy, human gates, work finishing on folder / email / Telegram.

1. **Intake on channels they already have** — drop folder, email, Telegram.
2. **Document intelligence** — PDF / Office / text → two-level taxonomy (Reader + Taxonomist) → structure. RAG is opt-in, not a dumpster.
3. **Memory that is not only similar paragraphs** — GraphRAG (entities + relations in Neo4j, vectors in Qdrant). Vanilla RAG fails on “who is related to whom” and “what does this corpus say overall”.
4. **Human gates** — Reviewer holds exceptions. 100–1000 employee teams will not buy fully unsupervised finance/HR.
5. **Notify where they live** — Courier on Telegram. Mailroom on IMAP.

## Oficio, instance, binding (when we start to drift)

Founders will have ideas. Translate them **before** adding a node.

- **Oficio** — the job (Taxonomist files; Mailroom fetches mail; Courier notifies). One per job.
- **Instance** — the same oficio sold to a client or vertical (E&P Taxonomist, Aircraft Taxonomist). Same tools, different `config`. Visible on Admin → Graph so humans and the model see the same picture.
- **Utility** — the assembly the client bought (library + this Taxonomist + this drop folder). Not a second product.
- **Binding** — what that instance points at: a taxonomy tree, a `scope_path`, later a named credential (`imap:pemex`). Not a new employee.
- **Credential** — named secret (IMAP, bot token, API key) attached to an instance. Never a “Custodian” specialist. Never in Graph JSON. `.env` is fine for one tenant; two mailboxes need named bindings, not a vault product.

A smarter scheduler can wait. Orchestrator already routes; each instance already has a cadence. Do not replace LangGraph with if-else to look clever.

Reuse an existing oficio if the job already belongs to them. Split a new agent only when the job is genuinely different.

## Current specialist roster

<!-- atrium-roster:start -->
Intake: Watchman (folder), Mailroom (IMAP), Sentinel (shared inboxes), Courier (Telegram), Teams (webhook, parked), Post (SMTP, parked).
Library: Reader (OCR), E&P Taxonomist (two-level taxonomy). Parked: Advice Taxonomist, Aircraft Taxonomist, Bars Taxonomist, Car Taxonomist, Factory Taxonomist.
Line: Parser → Triage → Chunker → Graphsmith (entities) → Extractor → Recorder (SQL) → Clerk (classified tree).
Memory: Pathfinder (GraphRAG retrieve), Librarian (answer with that context).
Governance: Reviewer (exceptions), Architect (explains the live map), Orchestrator (routes), Ingestor (runs the whole line), Scribe (keeps prompts in sync).
<!-- atrium-roster:end -->

## Stack (do not reopen)

Postgres catalog + extracted rows. Qdrant chunks. Neo4j lexical graph + entity graph. Ollama on `127.0.0.1:11434` (API uses host network). FastAPI + Next.js Workspace :3000 and Admin :3001.

## Utilities are agents (this is the whole company)

When the founder says “we need X” (invoice checker, HR policy Q&A, a Telegram alert, a forecast, …), that is **not a new app**. It is a **specialist**:

1. Name the agent. One job.
2. Add the tool handler in `apps/api/app/runtime/tools.py`.
3. Seed tool, agent, assignment, and Orchestrator route in `apps/api/app/db/seed.py`.
4. Admin Graph hydrates the node. Ask Scribe to `sync the context prompt` (or reboot the API) so this roster stays true.
5. Workspace/Admin UI is optional chrome that **calls that agent’s tools**. Screens do not own the work.

Reuse an existing specialist if the job already belongs to them (Parser parses; Courier notifies). Split a new agent only when the job is genuinely different. A second client is a new **instance + utility binding**, not a new oficio.

A dedicated web is allowed only when operators need a surface for that tool. It still registers as an app in the catalog and still goes through an agent. It is not a second product.

## What not to do

- Do not build a second product inside this repo (generic chatbot, CRM, website builder, “just this one script”).
- Do not invent agents they did not ask for, and do not skip the catalog “to ship faster”.
- Do not hire a Custodian / Vaultkeeper / Configurator. Credentials and knobs are bindings on an instance.
- Do not clone a new oficio when the job is the same (another Taxonomist tree is an instance, not a species).
- Do not call the 32b CPU model on every file.
- Do not steal Librarian questions with overly broad Orchestrator keywords (`graph`, `folder`, `pdf`).
- Do not skip tests for parse / classify / GraphRAG retrieve / routing.

When context is huge, re-read this file and `docs/HOW_IT_WORKS.md`. The picture of truth is Admin Graph, not chat history.

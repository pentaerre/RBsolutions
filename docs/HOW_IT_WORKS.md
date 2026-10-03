# How Atrium works (read this tomorrow)

Atrium is a **multi-agent platform**. It is not “a chatbot with extras”.
The chatbot is one agent (Librarian). The admin website is another app.
**Every utility we add is a named specialist with tools**, then maybe a
small surface. Never the other way around. They all talk to the same API.

If you only remember three sentences:

1. **Postgres** remembers *what exists* (apps, tools, agents) and *extracted rows*.
2. **LangGraph** decides *who works* (router → specialist). Every feature is an agent.
3. **GraphRAG**: Qdrant finds similar chunks; Neo4j expands *who is connected to whom*. Vector RAG alone is not enough.

The north-star prompt (when an AI session gets lost) is **[AGENTS.md](../AGENTS.md)**.
Scribe keeps the roster below in sync with Postgres. Do not edit inside the markers by hand.

<!-- atrium-roster:start -->
Intake: Watchman (folder), Mailroom (IMAP), Sentinel (shared inboxes), Courier (Telegram), Teams (webhook, parked), Post (SMTP, parked).
Library: Reader (OCR), E&P Taxonomist (two-level taxonomy). Parked: Advice Taxonomist, Aircraft Taxonomist, Bars Taxonomist, Car Taxonomist, Factory Taxonomist.
Line: Parser → Triage → Chunker → Graphsmith (entities) → Extractor → Recorder (SQL) → Clerk (classified tree).
Memory: Pathfinder (GraphRAG retrieve), Librarian (answer with that context).
Governance: Reviewer (exceptions), Architect (explains the live map), Orchestrator (routes), Ingestor (runs the whole line), Scribe (keeps prompts in sync).
<!-- atrium-roster:end -->

---

## The two websites

| URL | App | For whom |
|---|---|---|
| http://localhost:3000 | Workspace | Day-to-day work: documents and chat |
| http://localhost:3001 | Admin | You: register apps, enable tools, assign agents, **see the graph** |

Admin → **Utilities** is where you change the knobs a client will actually
touch (Watchman’s folder, which Taxonomist instance / tree, cadence, Mailroom poll).
Those values live on the agent `config` in Postgres — the same JSON the Graph
already shows. Do not invent a second control plane.

**Oficio / instance / binding** (read this when a new idea shows up):

| Layer | Example | Not |
|---|---|---|
| Oficio (the job) | Taxonomist, Mailroom, Courier | One job per vertical |
| Instance | E&P Taxonomist, Aircraft Taxonomist | 280 employees |
| Utility | Biblioteca · Aircraft | A second SaaS |
| Binding | tree + `inbox/aircraft`; later `imap:pemex` | A Custodian agent; passwords on the graph |

Follow the industry (n8n credentials, UiPath assets, LangGraph assistants). Atrium’s
wedge is the line they skip: GraphRAG, two-level taxonomy, HITL, channels they already
have. A smarter scheduler can wait; Orchestrator + per-instance cadence is enough now.

Tomorrow, open Admin → **Graph**. **Map**, **live line**, and **corpus** —
that picture is the system. The live line is where a file sits right now:
Watchman → Reader → Taxonomist → Clerk (GraphRAG only after someone promotes).

Ask Workspace chat: `how does this platform work?`
That question is routed to the **Architect** agent, which reads the live catalog
instead of guessing.

---

## What happens when someone chats

```
You type a message in Workspace
        │
        ▼
Platform API  (/api/runtime/chat)
        │
        ▼
LangGraph router  (Orchestrator agent)
        │
        ├── folder / watch      → Watchman    → lists inbox
        ├── email / attachment  → Mailroom    → IMAP download + store the letter
        ├── shared inbox / churn / riesgo legal → Sentinel → brief for direction
        ├── parse               → Parser      → PDF / XLSX / PPTX
        ├── ocr / first two pages → Reader
        ├── taxonomy / filing tree  → Taxonomist  → labels class / subclass
        ├── organize / folder tree  → Clerk       → classified/{class}/{subclass}
        ├── classify            → Triage
        ├── chunk               → Chunker     → Qdrant + Neo4j
        ├── telegram            → Courier     → bot files / notify
        ├── extract entities    → Graphsmith  → Neo4j GraphRAG graph
        ├── who is connected    → Pathfinder  → entity neighbors
        ├── exception / review  → Reviewer    → human gate
        ├── extract / sql       → Extractor   → structured fields
        ├── records             → Recorder    → Postgres rows
        ├── ingest / pipeline   → Ingestor    → runs the whole line
        ├── how does            → Architect
        └── everything else     → Librarian   → GraphRAG answer
```

The router rules live in Admin → Agents → Orchestrator → config JSON.
You can change them without rewriting Python.

---

## Document pipeline (this is the company line)

This is how 100–1000 employee teams already process paper: inbox → classify →
knowledge base and/or the ledger. Atrium copies that split as agents.

```
Drop folder (Watchman)     Email IMAP (Mailroom)
            \                   /
             \                 /
              ▼               ▼
                 inbox/
                    │
                    ▼
                 Parser     PDF · XLSX · PPTX · DOCX · CSV
                    │
                    ▼
                 Triage     invoice | contract | policy | report |
                            spreadsheet | presentation | form | other
                   / \
                  /   \
           knowledge   structured
                │           │
             Chunker     Extractor
                │           │
           Qdrant vectors  Recorder → SQL
                │
            Graphsmith → Neo4j entities/relations
                │
            Pathfinder + Librarian  (GraphRAG, not vectors alone)
                │
            Reviewer (human) → Courier (Telegram)

Clerk files the original: library line into classified/{class}/{subclass}/;
IDP line into classified/{type}/.
```

Drop files in `data/documents/inbox` (subfolders allowed) or the documents folder root.
Mailroom writes email attachments there. Watchman **registers** arrivals. Reader extracts
the first two pages (OCR when a PDF has no text). **One Taxonomist is live.** That
instance labels documents in its two-level tree. **Clerk** creates
`classified/{class}/{subclass}` from that tree and moves the files. Taxonomist does
not shutil. The sold product is one client tree
(E&P today). The others (Aircraft, Car, Factory, Bars / HORECA distributors, Advice /
labor-tax) are the same oficio, parked until you enable that instance in Admin.
Drop under that agent’s `scope_path` (`inbox`, `inbox/bars`, `inbox/advice`, …).
Longer paths win when two live instances would overlap. That path **does not** write Qdrant.

Operators pick documents in Workspace → Library (the live tree, not a picker) and
promote only those into GraphRAG. The Ingestor IDP button still runs the finance line
(SQL extract + file by type).

Configure IMAP with `IMAP_HOST`, `IMAP_USER`, `IMAP_PASSWORD` when you want
Mailroom to pull attachments by itself. Cadence is `hour` / `day` / `week` on
the live Taxonomist instance (Admin → Utilities, or Workspace Library).

The same fetch stores the letter for **Sentinel** (Admin → Utilities → Operations brief).
Sentinel is the job for direction, not a personal inbox assistant. It reads shared
folders (`INBOX`, or `pedidos` / `soporte` once those names are on the mailbox knob),
flags legal risk, a commercial ask left longer than `stale_hours`, and churn or a
supplier slip, then looks the party up in Neo4j and in the SQL ledger. It does not
invent a penalty that those stores did not return. Reviewer keeps the brief open.
Courier sends it on the Telegram chatbot only when the signal is high and new. The text names the subject and the sender address. The notify knob can point the same brief at Teams or Post once that worker is enabled. Classification
is a local pattern pass, so a quiet mailbox does not call the 32b model. Set
Sentinel `poll_seconds` to 300 when it should scan every five minutes. Drop a
JSON letter in `documents/signals-drop/` when IMAP is not configured yet.

---

## Why Gemini’s libraries are here

Gemini listed a typical agent stack. Here is how each piece is used, in
human language:

| Library | Role in Atrium | What it is not |
|---|---|---|
| **LangGraph** | The actual agent workflow (router + specialists) | Not a website |
| **LangChain / langchain-ollama** | Talk to Ollama in a standard way | Not the catalog |
| **langchain-anthropic** | Optional later: set `LLM_PROVIDER=anthropic` + API key | Not required while Ollama is local |
| **Qdrant** | Vector database for PDF chunks (RAG) | Replaces Chroma |
| **Neo4j** | Graph of documents and entities | Not a dump of every PDF fragment |
| **Postgres** (`psycopg`) | Source of truth for apps / tools / agents | We use psycopg v3, which replaces `psycopg2-binary` |

Postgres was already in the platform. We did not add a second Postgres driver.

---

## The four data stores (easy to mix up)

1. **Postgres** — business objects you edit in Admin.
2. **Qdrant** — numbered pieces of PDF text + vectors, for “find similar meaning”.
3. **Neo4j** — documents and entities (`Document -MENTIONS-> Entity`). Chunks are plumbing in Qdrant + Neo4j; the Admin corpus view hides them so you can follow who is related to whom.
4. **Ollama** — chat default is `qwen2.5:7b`. `qwen2.5-coder:32b` is optional: this machine has no GPU, so 32b spends minutes on prompt eval before the first token.

---

## Folder map (only the parts that matter)

```
apps/api/app/db/           Postgres models + seed catalog
apps/api/app/runtime/      LangGraph + tool handlers + orchestrator
apps/api/app/services/     Qdrant, Neo4j, Ollama, PDF ingest
apps/api/app/routers/      HTTP: health, catalog, chat, graph
apps/web/                  Workspace UI
apps/admin/                Admin UI, including /graph
docs/HOW_IT_WORKS.md       this file
```

You do **not** need to read every file. Start with:

1. `docs/HOW_IT_WORKS.md` (here)
2. Admin Graph page (`http://localhost:3001/graph`)
3. `apps/api/app/runtime/graph.py` (the LangGraph)
4. `apps/api/app/db/seed.py` (default apps/tools/agents)

---

## What the files actually do

There are a few thousand lines. Almost none of them are “the product idea”.
They fall into six buckets:

### 1. The catalog (Postgres) — “what exists”

| File | Job |
|---|---|
| `apps/api/app/db/models.py` | Tables: App, Tool, Agent, plus intake_documents and extracted_records |
| `apps/api/app/db/seed.py` | Default 2 apps, 13 tools, 12 agents, and who uses which tool |
| `apps/api/app/db/session.py` | Connect to Postgres |
| `apps/admin/app/apps`, `tools`, `agents` | Forms so you can change the catalog without code |

If you add a future website, you register it here. You do not rewrite LangGraph.

### 2. The runtime (LangGraph) — “who works”

| File | Job |
|---|---|
| `apps/api/app/runtime/graph.py` | Chat graph + document pipeline picture |
| `apps/api/app/runtime/routing.py` | Keyword match against Orchestrator `config_json` |
| `apps/api/app/runtime/orchestrator.py` | Runs the graph, then asks Ollama to talk |
| `apps/api/app/runtime/tools.py` | Maps tool slugs to Python (`knowledge.search`, `platform.explain`, …) |
| `apps/api/app/routers/runtime.py` | SSE endpoint `/api/runtime/chat` |

### 3. Document ops — “files in, RAG and SQL out”

| File | Job |
|---|---|
| `apps/api/app/services/pipeline.py` | The line: parse → classify → chunk → extract → file |
| `apps/api/app/services/parsers.py` | PDF, XLSX, PPTX, DOCX, CSV → text |
| `apps/api/app/services/classify.py` | Triage (invoice, contract, policy, …) |
| `apps/api/app/services/extract.py` | Spreadsheet rows / invoice fields → JSON |
| `apps/api/app/services/mailroom.py` | IMAP attachment download |
| `apps/api/app/services/vectorstore.py` | Qdrant: vectors for “find similar meaning” |
| `apps/api/app/services/graphstore.py` | Neo4j: `Document -HAS_CHUNK-> Chunk` |
| `apps/api/app/services/rag.py` | Search Qdrant, build the librarian prompt |

### 4. The graphs you can see

Admin → Graph has three views an operator can follow:

1. **Map** — channels → specialists → GraphRAG / SQL ledger / human gate → stores. The product, not the client’s knowledge.
2. **Live line** — where each file sits: Watchman → Reader → Taxonomist → Clerk (GraphRAG only after someone promotes).
3. **Corpus** — how GraphRAG retrieve works, then documents and entities in Neo4j. Chunks stay in Qdrant; this picture is who is mentioned with whom.

The old “every agent + every chunk” dump is not a view. Architect still reads the full catalog text.

| File | Job |
|---|---|
| `apps/api/app/services/platform_map.py` | Builds architecture, detail, RAG, runtime, pipeline, platform graphs |
| `apps/admin/app/graph/page.tsx` | Admin → Graph (map, live line, corpus) |

Same data the Architect agent reads. Humans look at the picture; the model looks at the text.

### 5. The two websites

| App | Port | Files |
|---|---|---|
| Workspace | 3000 | `apps/web` — documents + chat |
| Admin | 3001 | `apps/admin` — catalog + graph |

Both proxy `/api/*` to the platform API on port 8000.

### 6. Glue

| File | Job |
|---|---|
| `docker-compose.yml` | Postgres, Qdrant, Neo4j, API, web, admin |
| `apps/api/app/main.py` | FastAPI app, boots catalog, watches the PDF folder |
| `apps/api/app/services/llm.py` | Ollama today, Anthropic if `LLM_PROVIDER=anthropic` |
| `apps/api/app/config.py` | Env vars |

Ollama itself is **not** in Docker. It already runs on this machine at `127.0.0.1:11434`. That is why the API uses `network_mode: host`.

---

## How a future complex tool plugs in

1. Build a new website (another Next.js app, or anything).
2. In Admin → Apps, register it (slug, URL, kind=`tool`).
3. In Admin → Tools, register an HTTP tool pointing at that site’s API.
4. In Admin → Agents, attach that tool to an agent (or make a new agent).
5. Optionally add a router keyword so the Orchestrator sends matching questions there.

No rewrite of the platform is required for that step.

---

## Commands

```bash
docker compose up --build     # start everything
# Workspace  http://localhost:3000
# Admin      http://localhost:3001
# Neo4j UI   http://localhost:7474   (neo4j / atriumpass)
# Qdrant     http://localhost:6333
```

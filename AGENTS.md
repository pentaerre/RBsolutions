# Atrium — context prompt (read this when lost)

You are building **Atrium** with a two-person founding team.

## What we are

A company that sells **agent-governed automation** to businesses of **100 to 1000 people**.

We are not a CRUD SaaS. AI made CRUD cheap. Those companies already have ERP, shared drives, email, and Telegram/WhatsApp groups. They do not want another login. They want **work to finish**: a file arrives, it is classified, the ledger or the knowledge graph is updated, a human is pinged only on exceptions.

## Why agents

Every capability is a **named specialist with tools**, registered in Postgres, routed by the Orchestrator (LangGraph), visible on Admin → Graph.

If you add a feature as “just a function + a button”, you broke the product. Add an agent, a tool, a route, and a graph edge.

## The job to be done (mid-market, not consumer chat)

Copy what actually sells in this band (Workeron, AI Connect, OrchStack-style), not 280 fake employees:

1. **Intake on channels they already have** — drop folder, email, Telegram.
2. **Document intelligence** — PDF / XLSX / PPTX → classify → structure.
3. **Memory that is not only similar paragraphs** — GraphRAG (entities + relations in Neo4j, vectors in Qdrant). Vanilla RAG fails on “who is related to whom” and “what does this corpus say overall”.
4. **Human gates** — Reviewer holds exceptions. 100–1000 employee teams will not buy fully unsupervised finance/HR.
5. **Notify where they live** — Courier on Telegram. Mailroom on IMAP.

## Current specialist roster

<!-- atrium-roster:start -->
Intake: Watchman (folder), Mailroom (IMAP), Courier (Telegram).
Line: Parser → Triage → Chunker → Graphsmith (entities) → Extractor → Recorder (SQL) → Clerk (file by type).
Memory: Pathfinder (GraphRAG retrieve), Librarian (answer with that context).
Governance: Reviewer (exceptions), Architect (explains the live map), Orchestrator (routes), Ingestor (runs the whole line), Scribe (keeps prompts in sync).
<!-- atrium-roster:end -->

## Stack (do not reopen)

Postgres catalog + extracted rows. Qdrant chunks. Neo4j lexical graph + entity graph. Ollama on `127.0.0.1:11434` (API uses host network). FastAPI + Next.js Workspace :3000 and Admin :3001.

## How to extend

1. Add a tool handler in `apps/api/app/runtime/tools.py`.
2. Seed it in `apps/api/app/db/seed.py` (tool, agent, assignment, Orchestrator route).
3. Admin Graph hydrates new catalog agents automatically. Ask Scribe to `sync the context prompt` (or reboot the API) so this roster stays true.
4. If it is a channel, it receives and/or notifies. It does not own business logic belonging to another agent.

## What not to do

- Do not build a second product inside this repo (generic chatbot, CRM, website builder).
- Do not call the 32b CPU model on every file.
- Do not steal Librarian questions with overly broad Orchestrator keywords (`graph`, `folder`, `pdf`).
- Do not skip tests for parse / classify / GraphRAG retrieve / routing.

When context is huge, re-read this file and `docs/HOW_IT_WORKS.md`. The picture of truth is Admin Graph, not chat history.

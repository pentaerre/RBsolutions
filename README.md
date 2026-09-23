# Atrium

Two-person agent company: automate work for businesses of 100–1000 people.
Not CRUD SaaS. Agents own every capability.

**Read [AGENTS.md](AGENTS.md) first** (north star / context prompt). Then
**[docs/HOW_IT_WORKS.md](docs/HOW_IT_WORKS.md)**.

## Surfaces

- Workspace: http://localhost:3000
- Admin (tools, agents, **graph**): http://localhost:3001
- API: http://localhost:8000/api/health
- Neo4j browser: http://localhost:7474 (`neo4j` / `atriumpass`)

```bash
cp .env.example .env
docker compose up --build
```

Ask chat `how does this platform work?` or open Admin → Graph. GraphRAG lives
with Graphsmith + Pathfinder + Librarian. Telegram is the Courier agent
(`TELEGRAM_BOT_TOKEN`).

## Surfaces

- Workspace: http://localhost:3000
- Admin (tools, agents, **graph**): http://localhost:3001
- API: http://localhost:8000/api/health
- Neo4j browser: http://localhost:7474 (`neo4j` / `atriumpass`)

```bash
cp .env.example .env
docker compose up --build
```

Ask chat `how does this platform work?` or open Admin → Graph.

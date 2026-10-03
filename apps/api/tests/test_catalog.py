def test_disable_and_update_tool(client) -> None:
    listed = client.get("/api/tools").json()["tools"]
    tool = next(item for item in listed if item["slug"] == "documents.list")
    updated = client.patch(f"/api/tools/{tool['id']}", json={"status": "disabled"})
    assert updated.status_code == 200
    assert updated.json()["status"] == "disabled"
    restored = client.patch(f"/api/tools/{tool['id']}", json={"status": "live"})
    assert restored.json()["status"] == "live"


def test_document_ops_agents_are_seeded(client) -> None:
    slugs = {item["slug"] for item in client.get("/api/agents").json()["agents"]}
    assert {
        "watchman",
        "mailroom",
        "parser",
        "triage",
        "chunker",
        "extractor",
        "recorder",
        "clerk",
        "ingestor",
        "librarian",
        "graphsmith",
        "pathfinder",
        "courier",
        "sentinel",
        "reviewer",
        "architect",
        "scribe",
        "reader",
        "taxonomist",
        "taxonomist-aircraft",
        "taxonomist-car",
        "taxonomist-factory",
        "taxonomist-bars",
        "taxonomist-advice",
        "orchestrator",
    }.issubset(slugs)


def test_register_future_app(client) -> None:
    slug = f"forecast-{__import__('uuid').uuid4().hex[:8]}"
    created = client.post(
        "/api/apps",
        json={
            "slug": slug,
            "name": "Forecast",
            "kind": "tool",
            "base_url": "http://localhost:3100",
            "status": "planned",
            "summary": "Future specialized web for forecasting.",
        },
    )
    assert created.status_code == 201
    apps = client.get("/api/apps").json()["apps"]
    assert any(item["slug"] == slug for item in apps)


def test_assign_agent_tools(client) -> None:
    agent = next(item for item in client.get("/api/agents").json()["agents"] if item["slug"] == "librarian")
    updated = client.patch(f"/api/agents/{agent['id']}", json={"tools": ["knowledge.search", "models.list"]})
    assert updated.status_code == 200
    assert set(updated.json()["tools"]) == {"knowledge.search", "models.list"}
    client.patch(f"/api/agents/{agent['id']}", json={"tools": ["knowledge.search"]})


def test_patch_agent_model(client) -> None:
    agent = next(item for item in client.get("/api/agents").json()["agents"] if item["slug"] == "librarian")
    updated = client.patch(f"/api/agents/{agent['id']}", json={"model": "qwen2.5:7b"})
    assert updated.status_code == 200
    assert updated.json()["model"] == "qwen2.5:7b"


def test_only_llm_agents_carry_a_model(client) -> None:
    agents = client.get("/api/agents").json()["agents"]
    llm = {item["slug"] for item in agents if item["uses_llm"]}
    assert "librarian" in llm
    assert "reader" in llm
    assert "extractor" in llm
    assert "triage" in llm
    assert "graphsmith" in llm
    assert "taxonomist" in llm
    assert any(item.startswith("taxonomist") for item in llm)
    assert "architect" not in llm
    assert "watchman" not in llm
    assert "chunker" not in llm
    assert "pathfinder" not in llm
    librarian = next(item for item in agents if item["slug"] == "librarian")
    assert librarian["model"]
    assert "32b" not in librarian["model"]
    watchman = next(item for item in agents if item["slug"] == "watchman")
    assert watchman["model"] == ""
    architect = next(item for item in agents if item["slug"] == "architect")
    assert architect["uses_llm"] is False
    assert architect["model"] == ""

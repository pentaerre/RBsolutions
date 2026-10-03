from fastapi.testclient import TestClient

from app.runtime.graph import RUNTIME_GRAPH, get_compiled_graph
from app.runtime.routing import choose_agent_slug


def test_langgraph_compiles() -> None:
    graph = get_compiled_graph()
    assert graph is not None
    assert len(RUNTIME_GRAPH["nodes"]) >= 4


def test_architect_route() -> None:
    routes = [
        {"match": ["ingest", "index"], "agent": "ingestor"},
        {"match": ["architecture", "how does", "platform", "graph"], "agent": "architect"},
        {"match": ["*"], "agent": "librarian"},
    ]
    available = {"orchestrator", "librarian", "ingestor", "architect"}
    assert choose_agent_slug("how does this platform work?", routes, available) == "architect"
    assert choose_agent_slug("ingest now", routes, available) == "ingestor"


def test_graph_endpoint(client: TestClient) -> None:
    response = client.get("/api/graph")
    assert response.status_code == 200
    body = response.json()
    assert "runtime" in body
    assert "pipeline" in body
    assert "platform" in body
    assert "architecture" in body
    assert "detail" in body
    assert "rag" in body
    assert any(node["id"] == "router" for node in body["runtime"]["nodes"])
    assert any(node["id"] == "mailroom" for node in body["pipeline"]["nodes"])
    assert any(node["id"] == "graphsmith" for node in body["pipeline"]["nodes"])
    assert any(node["id"] == "courier" for node in body["runtime"]["nodes"])
    assert any(node["id"] == "scribe" for node in body["runtime"]["nodes"])
    assert any(node["id"] == "scribe" for node in body["detail"]["nodes"])
    assert any(node["id"] == "memory" for node in body["architecture"]["nodes"])
    assert any(node["id"] == "graphsmith" for node in body["detail"]["nodes"])
    reader = next(node for node in body["detail"]["nodes"] if node["id"] == "reader")
    assert reader.get("model")
    watchman = next(node for node in body["detail"]["nodes"] if node["id"] == "watchman")
    assert not watchman.get("model")
    hop_reader = next(hop for hop in body["flow"]["hops"] if hop["id"] == "reader")
    assert hop_reader.get("model")
    hop_watchman = next(hop for hop in body["flow"]["hops"] if hop["id"] == "watchman")
    assert not hop_watchman.get("model")
    assert any(node["id"] == "hybrid" for node in body["rag"]["method"]["nodes"])
    assert "knowledge" in body["rag"]
    assert "flow" in body
    assert body["flow"]["hops"]
    assert {hop["id"] for hop in body["flow"]["hops"]} >= {"watchman", "reader", "taxonomist", "clerk"}
    knowledge = body["rag"]["knowledge"]
    assert all(node.get("kind") != "chunk" for node in knowledge["nodes"])
    assert any(node["id"] == "people" for node in body["architecture"]["nodes"])
    assert any(node["id"] == "watchman" for node in body["flow"]["line"]["nodes"])
    assert len(body["flow"]["line"]["nodes"]) <= 8


def test_architect_chat(client: TestClient) -> None:
    with client.stream("POST", "/api/runtime/chat", json={"message": "how does this platform work?"}) as response:
        assert response.status_code == 200
        text = "".join(response.iter_text())
    assert "architect" in text
    assert "Atrium" in text

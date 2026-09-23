from app.runtime.routing import choose_agent_slug


def test_ingest_keywords_route_to_ingestor() -> None:
    routes = [
        {"match": ["ingest", "index", "reindex", "folder"], "agent": "ingestor"},
        {"match": ["*"], "agent": "librarian"},
    ]
    available = {"orchestrator", "librarian", "ingestor"}
    assert choose_agent_slug("please ingest the folder", routes, available) == "ingestor"
    assert choose_agent_slug("What does Atrium do with PDFs?", routes, available) == "librarian"


def test_missing_agent_falls_back() -> None:
    routes = [{"match": ["*"], "agent": "missing"}]
    assert choose_agent_slug("hello", routes, {"librarian"}) == "librarian"

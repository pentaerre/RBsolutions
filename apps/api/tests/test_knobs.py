from pathlib import Path

from app.config import settings
from app.services.knobs import _safe_under_documents, get_value, set_value


def test_utilities_list_library_agents(client) -> None:
    payload = client.get("/api/utilities").json()
    slugs = {item["slug"] for item in payload["utilities"]}
    assert {"library", "library-aircraft", "library-car", "library-factory", "library-bars", "library-advice", "idp-line", "graphrag"} <= slugs
    library = next(item for item in payload["utilities"] if item["slug"] == "library")
    agents = {agent["slug"] for agent in library["agents"]}
    assert {"watchman", "mailroom", "reader", "taxonomist", "clerk"} <= agents
    watchman = next(agent for agent in library["agents"] if agent["slug"] == "watchman")
    keys = {field["key"] for field in watchman["knobs"]}
    assert "watch_path" in keys
    assert "recursive" in keys


def test_patch_utility_writes_agent_config(client) -> None:
    saved = client.patch(
        "/api/utilities/library",
        json={"values": {"watchman": {"watch_path": "inbox"}, "taxonomist": {"cadence": "week"}}},
    ).json()
    taxonomist = next(agent for agent in saved["agents"] if agent["slug"] == "taxonomist")
    assert taxonomist["config"]["cadence"] == "week"
    watchman = next(agent for agent in saved["agents"] if agent["slug"] == "watchman")
    assert watchman["config"]["watch_path"] == "inbox"
    listed = client.get("/api/agents").json()["agents"]
    again = next(item for item in listed if item["slug"] == "taxonomist")
    assert again["config"]["cadence"] == "week"
    assert any(field["key"] == "cadence" for field in again["knobs"])


def test_watch_path_cannot_escape_documents(tmp_path: Path) -> None:
    previous = settings.documents_dir
    settings.documents_dir = str(tmp_path)
    try:
        safe = _safe_under_documents("inbox/client-a")
        assert safe == (tmp_path / "inbox" / "client-a").resolve()
        escaped = _safe_under_documents("../etc")
        assert escaped == (tmp_path / "inbox").resolve()
    finally:
        settings.documents_dir = previous


def test_nested_knob_helpers() -> None:
    payload: dict = {}
    set_value(payload, "taxonomy.name", "HR")
    assert payload["taxonomy"]["name"] == "HR"
    assert get_value(payload, "taxonomy.name") == "HR"

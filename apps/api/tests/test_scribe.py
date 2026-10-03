from pathlib import Path

from app.db.seed import CANONICAL_ROUTES
from app.db.session import SessionLocal
from app.runtime.routing import choose_agent_slug
from app.services.scribe import render_roster, sync_docs


def test_scribe_roster_includes_live_agents(client) -> None:
    db = SessionLocal()
    try:
        text = render_roster(db)
    finally:
        db.close()
    assert "Courier" in text
    assert "Graphsmith" in text
    assert "Scribe" in text
    assert "Parked:" in text
    assert "E&P Taxonomist" in text
    assert "Bars Taxonomist" in text
    assert "Advice Taxonomist" in text


def test_scribe_patches_markers(tmp_path, client) -> None:
    md = tmp_path / "AGENTS.md"
    md.write_text(
        "intro\n<!-- atrium-roster:start -->\nold roster\n<!-- atrium-roster:end -->\noutro\n",
        encoding="utf-8",
    )
    how = tmp_path / "docs"
    how.mkdir()
    (how / "HOW_IT_WORKS.md").write_text(
        "x\n<!-- atrium-roster:start -->\nstale\n<!-- atrium-roster:end -->\ny\n",
        encoding="utf-8",
    )
    db = SessionLocal()
    try:
        result = sync_docs(db, root=Path(tmp_path))
    finally:
        db.close()
    assert result["ok"] is True
    assert "AGENTS.md" in result["written"]
    body = md.read_text(encoding="utf-8")
    assert "Scribe" in body
    assert "old roster" not in body
    assert body.startswith("intro")
    assert "outro" in body


def test_scribe_route() -> None:
    available = {rule["agent"] for rule in CANONICAL_ROUTES}
    available.add("orchestrator")
    assert choose_agent_slug("sync the context prompt", CANONICAL_ROUTES, available) == "scribe"
    assert choose_agent_slug("how does this platform work?", CANONICAL_ROUTES, available) == "architect"

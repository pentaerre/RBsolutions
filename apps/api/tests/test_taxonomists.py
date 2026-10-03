from pathlib import Path

from app.db.session import SessionLocal
from app.runtime.routing import choose_agent_slug
from app.db.seed import CANONICAL_ROUTES
from app.services import library
from app.services.taxonomy import ADVICE_TAXONOMY, AIRCRAFT_TAXONOMY, BARS_TAXONOMY, classify_document, owner_slug


def test_aircraft_tree_from_path() -> None:
    placed = classify_document(
        "inbox/aircraft/engines/ehm-report.txt",
        "ehm-report.txt",
        "Engine health monitoring EHM vibration on the left engine.",
        {"taxonomy": AIRCRAFT_TAXONOMY},
    )
    assert placed["l1"] == "engineering"
    assert placed["l2"] == "engines"


def test_longest_scope_wins() -> None:
    owners = [
        ("taxonomist", "inbox"),
        ("taxonomist-aircraft", "inbox/aircraft"),
        ("taxonomist-car", "inbox/car"),
    ]
    assert owner_slug("inbox/wells/drilling/mud.txt", owners) == "taxonomist"
    assert owner_slug("inbox/aircraft/engines/ehm.txt", owners) == "taxonomist-aircraft"
    assert owner_slug("inbox/car/warranty/claim.txt", owners) == "taxonomist-car"


def test_aircraft_cycle_does_not_use_ep_tree(tmp_path: Path) -> None:
    from app.config import settings

    previous = settings.documents_dir
    settings.documents_dir = str(tmp_path)
    try:
        folder = tmp_path / "inbox" / "aircraft" / "engines"
        folder.mkdir(parents=True)
        (folder / "ehm-report.txt").write_text("Engine EHM vibration report for the left engine and APU.\n" * 3)
        ep = tmp_path / "inbox" / "wells" / "drilling"
        ep.mkdir(parents=True)
        (ep / "mud-report.txt").write_text("Daily drilling mud report. BHA trip and standpipe pressure.\n" * 3)
        db = SessionLocal()
        try:
            library.run_cycle(db, "taxonomist-aircraft")
            library.run_cycle(db, "taxonomist")
            docs = {item["filename"]: item for item in library.list_documents(db)}
            assert docs["ehm-report.txt"]["taxonomy_l1"] == "engineering"
            assert docs["ehm-report.txt"]["taxonomist_slug"] == "taxonomist-aircraft"
            assert docs["mud-report.txt"]["taxonomy_l1"] == "wells"
            assert docs["mud-report.txt"]["taxonomist_slug"] == "taxonomist"
            aircraft_only = library.list_documents(db, taxonomist="taxonomist-aircraft")
            assert [item["filename"] for item in aircraft_only] == ["ehm-report.txt"]
            assert docs["ehm-report.txt"]["rel_path"].startswith("classified/engineering/")
            assert docs["mud-report.txt"]["rel_path"].startswith("classified/wells/")
        finally:
            db.close()
    finally:
        settings.documents_dir = previous


def test_routes_pick_named_taxonomist() -> None:
    available = {rule["agent"] for rule in CANONICAL_ROUTES}
    available.update({"orchestrator", "librarian"})
    assert choose_agent_slug("run the aircraft taxonomy", CANONICAL_ROUTES, available) == "taxonomist-aircraft"
    assert choose_agent_slug("run the two-level taxonomy", CANONICAL_ROUTES, available) == "taxonomist"
    assert choose_agent_slug("run the horeca taxonomy", CANONICAL_ROUTES, available) == "taxonomist-bars"
    assert choose_agent_slug("run the asesoria laboral fiscal", CANONICAL_ROUTES, available) == "taxonomist-advice"


def test_library_aircraft_utility(client) -> None:
    item = client.get("/api/utilities/library-aircraft").json()
    slugs = {agent["slug"] for agent in item["agents"]}
    assert "taxonomist-aircraft" in slugs
    taxonomist = next(agent for agent in item["agents"] if agent["slug"] == "taxonomist-aircraft")
    keys = {field["key"] for field in taxonomist["knobs"]}
    assert "scope_path" in keys
    assert "cadence" in keys
    saved = client.patch(
        "/api/utilities/library-aircraft",
        json={"values": {"taxonomist-aircraft": {"cadence": "day"}}},
    ).json()
    again = next(agent for agent in saved["agents"] if agent["slug"] == "taxonomist-aircraft")
    assert again["config"]["cadence"] == "day"


def test_bars_tree_from_path() -> None:
    placed = classify_document(
        "inbox/bars/catalog/cerveza-sku.txt",
        "cerveza-sku.txt",
        "Catalogo de cerveza IPA lager en barril. SKU 441 para on trade.",
        {"taxonomy": BARS_TAXONOMY},
    )
    assert placed["l1"] == "catalog"
    assert placed["l2"] == "beer"


def test_advice_tree_from_path() -> None:
    placed = classify_document(
        "inbox/advice/labor/nomina-marzo.txt",
        "nomina-marzo.txt",
        "Nomina de marzo con IRPF y cotizacion a la seguridad social.",
        {"taxonomy": ADVICE_TAXONOMY},
    )
    assert placed["l1"] == "labor"
    assert placed["l2"] == "payroll"


def test_only_ep_taxonomist_is_live(client) -> None:
    agents = {item["slug"]: item for item in client.get("/api/agents").json()["agents"]}
    assert agents["taxonomist"]["status"] == "live"
    for slug in (
        "taxonomist-aircraft",
        "taxonomist-car",
        "taxonomist-factory",
        "taxonomist-bars",
        "taxonomist-advice",
    ):
        assert agents[slug]["status"] == "disabled"


def test_enabling_one_taxonomist_parks_the_rest(client) -> None:
    agents = {item["slug"]: item for item in client.get("/api/agents").json()["agents"]}
    bars = agents["taxonomist-bars"]
    ep = agents["taxonomist"]
    updated = client.patch(f"/api/agents/{bars['id']}", json={"status": "live"})
    assert updated.status_code == 200
    assert updated.json()["status"] == "live"
    again = {item["slug"]: item for item in client.get("/api/agents").json()["agents"]}
    assert again["taxonomist-bars"]["status"] == "live"
    assert again["taxonomist"]["status"] == "disabled"
    assert again["taxonomist-aircraft"]["status"] == "disabled"
    restored = client.patch(f"/api/agents/{ep['id']}", json={"status": "live"})
    assert restored.json()["status"] == "live"
    final = {item["slug"]: item for item in client.get("/api/agents").json()["agents"]}
    assert final["taxonomist"]["status"] == "live"
    assert final["taxonomist-bars"]["status"] == "disabled"


def test_default_cycle_uses_live_tree_only(tmp_path: Path) -> None:
    from app.config import settings

    previous = settings.documents_dir
    settings.documents_dir = str(tmp_path)
    try:
        folder = tmp_path / "inbox" / "aircraft" / "engines"
        folder.mkdir(parents=True)
        (folder / "ehm-report.txt").write_text("Engine EHM vibration report for the left engine and APU.\n" * 3)
        db = SessionLocal()
        try:
            library.run_cycle(db)
            docs = {item["filename"]: item for item in library.list_documents(db)}
            assert docs["ehm-report.txt"]["taxonomist_slug"] == "taxonomist"
            assert docs["ehm-report.txt"]["taxonomy_l1"] != "engineering"
        finally:
            db.close()
    finally:
        settings.documents_dir = previous


def test_library_bars_utility(client) -> None:
    item = client.get("/api/utilities/library-bars").json()
    slugs = {agent["slug"] for agent in item["agents"]}
    assert "taxonomist-bars" in slugs
    taxonomist = next(agent for agent in item["agents"] if agent["slug"] == "taxonomist-bars")
    assert (taxonomist["config"] or {}).get("scope_path") == "inbox/bars"


def test_seed_repairs_multiple_live_taxonomists(client) -> None:
    from app.db.models import Agent
    from app.db.seed import seed_catalog

    db = SessionLocal()
    try:
        bars = db.query(Agent).filter(Agent.slug == "taxonomist-bars").first()
        bars.status = "live"
        db.commit()
        seed_catalog(db)
        db.expire_all()
        ep = db.query(Agent).filter(Agent.slug == "taxonomist").first()
        bars = db.query(Agent).filter(Agent.slug == "taxonomist-bars").first()
        assert ep.status == "live"
        assert bars.status == "disabled"
    finally:
        db.close()


def test_library_advice_utility(client) -> None:
    item = client.get("/api/utilities/library-advice").json()
    slugs = {agent["slug"] for agent in item["agents"]}
    assert "taxonomist-advice" in slugs
    taxonomist = next(agent for agent in item["agents"] if agent["slug"] == "taxonomist-advice")
    assert (taxonomist["config"] or {}).get("scope_path") == "inbox/advice"

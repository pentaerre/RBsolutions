import json
from datetime import datetime, timedelta

from app.db.models import Agent, ExtractedRecord, IntakeDocument, MailboxLetter, OperationalSignal
from app.db.seed import CANONICAL_ROUTES
from app.db.session import SessionLocal
from app.runtime.routing import choose_agent_slug
from app.runtime.tools import invoke_tool
from app.services.reviewer import list_exceptions
from app.services.sentinel import classify_letter, scan, signals_drop


def _clear(db) -> None:
    db.query(OperationalSignal).delete()
    db.query(MailboxLetter).delete()
    db.commit()


def _letter(**overrides):
    base = {
        "message_id": "msg-1",
        "mailbox": "INBOX",
        "sender": "Acme <ops@acme.test>",
        "subject": "Entrega",
        "body": "Sin novedad.",
        "received_at": datetime.utcnow().isoformat(),
    }
    base.update(overrides)
    return base


def test_classify_three_sellable_signals() -> None:
    legal = classify_letter("Legal <l@firm.test>", "Borrador", "Incluye responsabilidad ilimitada.")
    assert legal is not None
    assert legal["kind"] == "legal"
    assert legal["severity"] == "high"

    ask = classify_letter("Cliente <c@buyer.test>", "Servicios", "¿Vosotros también hacéis auditorías ISO?")
    assert ask is not None
    assert ask["kind"] == "opportunity"

    slip = classify_letter("Acme <ops@acme.test>", "Plazo", "El plazo de entrega se va a retrasar dos semanas.")
    assert slip is not None
    assert slip["kind"] == "churn"
    assert slip["severity"] == "high"
    assert slip["party"] == "Acme"

    assert classify_letter("News <n@news.test>", "Boletín", "La newsletter semanal ya está publicada.") is None


def test_scan_crosses_graph_and_ledger_without_inventing(monkeypatch) -> None:
    class FakeGraph:
        def entity_search(self, query: str) -> dict:
            assert "Acme" in query
            return {
                "ok": True,
                "enabled": True,
                "entities": [
                    {"name": "Acme", "kind": "org", "neighbors": ["Proyecto X"], "files": ["contrato.pdf"]}
                ],
            }

    monkeypatch.setattr("app.services.graphstore.get_graphstore", lambda: FakeGraph())
    db = SessionLocal()
    try:
        _clear(db)
        doc = IntakeDocument(filename="acme-contract.pdf", rel_path=f"acme-contract-{datetime.utcnow().timestamp()}.pdf")
        db.add(doc)
        db.flush()
        db.add(
            ExtractedRecord(
                document_id=doc.id,
                kind="contract",
                payload_json=json.dumps({"vendor": "Acme", "penalty": "10000"}),
            )
        )
        db.commit()
        result = scan(
            db,
            [
                _letter(
                    message_id="delay-451",
                    subject="Correo 451",
                    body="El plazo de entrega se va a retrasar dos semanas.",
                )
            ],
        )
        assert result["created"] == 1
        brief = result["signals"][0]["brief"]
        assert "Proyecto X" in brief
        assert "penalty=10000" in brief
        assert "10000" not in brief.replace("penalty=10000", "")
        again = scan(db, [_letter(message_id="delay-451", body="El plazo de entrega se va a retrasar dos semanas.")])
        assert again["created"] == 0
        queued = list_exceptions(db)
        assert any(item["reason"] == "signal_churn" for item in queued["items"])
    finally:
        db.close()


def test_stale_opportunity_is_high_and_other_mailbox_is_ignored() -> None:
    db = SessionLocal()
    try:
        _clear(db)
        old = (datetime.utcnow() - timedelta(hours=30)).isoformat()
        result = scan(
            db,
            [
                _letter(
                    message_id="iso-ask",
                    sender="Norte <buyer@norte.test>",
                    subject="ISO",
                    body="¿Vosotros también hacéis auditorías ISO?",
                    received_at=old,
                ),
                _letter(
                    message_id="other-box",
                    mailbox="personal",
                    subject="ISO personal",
                    body="¿Vosotros también hacéis auditorías ISO?",
                ),
            ],
        )
        assert result["created"] == 1
        signal = result["signals"][0]
        assert signal["kind"] == "opportunity"
        assert signal["severity"] == "high"
        assert "sin atención" in signal["brief"]
    finally:
        db.close()


def test_disabled_signal_kind_is_a_knob() -> None:
    db = SessionLocal()
    try:
        _clear(db)
        agent = db.query(Agent).filter(Agent.slug == "sentinel").one()
        cfg = json.loads(agent.config_json or "{}")
        cfg["signals"] = "legal"
        agent.config_json = json.dumps(cfg)
        db.commit()
        result = scan(db, [_letter(message_id="only-legal-off", body="El plazo de entrega se va a retrasar dos semanas.")])
        assert result["created"] == 0
        agent = db.query(Agent).filter(Agent.slug == "sentinel").one()
        cfg = json.loads(agent.config_json or "{}")
        cfg["signals"] = "legal,opportunity,churn"
        agent.config_json = json.dumps(cfg)
        db.commit()
    finally:
        db.close()


def test_drop_folder_and_tool(client) -> None:
    db = SessionLocal()
    try:
        _clear(db)
    finally:
        db.close()
    path = signals_drop() / "demo-letter.json"
    path.write_text(
        json.dumps(
            {
                "message_id": "drop-legal-1",
                "sender": "Contratos <legal@vendor.test>",
                "subject": "Borrador de contrato",
                "body": "Este anexo fija responsabilidad ilimitada.",
            }
        ),
        encoding="utf-8",
    )
    listed = client.get("/api/utilities").json()["utilities"]
    operations = next(item for item in listed if item["slug"] == "operations")
    sentinel = next(agent for agent in operations["agents"] if agent["slug"] == "sentinel")
    assert {field["key"] for field in sentinel["knobs"]} >= {"mailboxes", "signals", "stale_hours", "poll_seconds"}
    db = SessionLocal()
    try:
        result = invoke_tool(db, "signals.scan", {})
    finally:
        db.close()
    assert result["tool"] == "signals.scan"
    assert result["created"] == 1
    assert result["signals"][0]["kind"] == "legal"
    assert not path.exists()


def test_telegram_alarm_names_subject_and_sender_and_other_workers_stay_parked(monkeypatch) -> None:
    sent: dict[str, str] = {}

    def fake(text: str, chat_id: str | None = None) -> dict:
        sent["text"] = text
        return {"ok": True, "configured": True}

    monkeypatch.setattr("app.services.telegram.send_message", fake)
    db = SessionLocal()
    try:
        _clear(db)
        agent = db.query(Agent).filter(Agent.slug == "sentinel").one()
        cfg = json.loads(agent.config_json or "{}")
        cfg["notify"] = "courier"
        agent.config_json = json.dumps(cfg)
        db.commit()
        result = scan(
            db,
            [
                _letter(
                    message_id="alarm-451",
                    sender="Acme <ops@acme.test>",
                    subject="Correo 451",
                    body="El plazo de entrega se va a retrasar dos semanas.",
                )
            ],
        )
        assert result["channel"] == "courier"
        assert result["notified"] == 1
        assert "Asunto: Correo 451" in sent["text"]
        assert "De: Acme <ops@acme.test>" in sent["text"]
        assert db.query(Agent).filter(Agent.slug == "teams").one().status == "disabled"
        assert db.query(Agent).filter(Agent.slug == "post").one().status == "disabled"
        _clear(db)
        agent = db.query(Agent).filter(Agent.slug == "sentinel").one()
        cfg = json.loads(agent.config_json or "{}")
        cfg["notify"] = "teams"
        agent.config_json = json.dumps(cfg)
        db.commit()
        parked = scan(
            db,
            [_letter(message_id="alarm-teams", body="El plazo de entrega se va a retrasar dos semanas.")],
        )
        assert parked["notified"] == 0
        assert parked["channel"] == "teams"
        assert "parked" in parked["delivery"].lower()
        agent = db.query(Agent).filter(Agent.slug == "sentinel").one()
        cfg = json.loads(agent.config_json or "{}")
        cfg["notify"] = "courier"
        agent.config_json = json.dumps(cfg)
        db.commit()
    finally:
        db.close()


def test_sentinel_route_does_not_steal_mailroom() -> None:
    available = {rule["agent"] for rule in CANONICAL_ROUTES}
    available.add("orchestrator")
    assert choose_agent_slug("scan the shared inbox", CANONICAL_ROUTES, available) == "sentinel"
    assert choose_agent_slug("riesgo legal en la bandeja compartida", CANONICAL_ROUTES, available) == "sentinel"
    assert choose_agent_slug("check the mailbox for attachments", CANONICAL_ROUTES, available) == "mailroom"

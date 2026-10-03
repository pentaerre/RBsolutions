from app.services.flow import STATUS_HOP, live_flow


def test_flow_endpoint_lists_hops(client) -> None:
    payload = client.get("/api/flow").json()
    ids = [hop["id"] for hop in payload["hops"]]
    assert ids == ["watchman", "reader", "taxonomist", "clerk", "chunker", "reviewer"]
    assert "total" in payload
    assert "line" in payload
    assert any(node["id"] == "watchman" for node in payload["line"]["nodes"])


def test_status_maps_to_library_agents() -> None:
    assert STATUS_HOP["received"] == "watchman"
    assert STATUS_HOP["read"] == "reader"
    assert STATUS_HOP["classified"] == "taxonomist"
    assert STATUS_HOP["filed"] == "clerk"
    assert STATUS_HOP["indexed"] == "chunker"


def test_live_flow_counts_received(client) -> None:
    from app.db.session import SessionLocal
    from app.services import library

    db = SessionLocal()
    try:
        library.register_arrivals(db)
        payload = live_flow(db)
        assert payload["total"] >= 0
        assert sum(hop["count"] for hop in payload["hops"]) == payload["total"]
    finally:
        db.close()

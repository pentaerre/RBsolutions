def test_health_endpoint(client) -> None:
    response = client.get("/api/health")
    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert "ollama" in body
    assert body["platform"]["tools"] >= 1
    assert body["platform"]["agents"] >= 1


def test_tools_endpoint(client) -> None:
    response = client.get("/api/tools")
    assert response.status_code == 200
    tools = response.json()["tools"]
    assert any(item["slug"] == "knowledge.search" for item in tools)

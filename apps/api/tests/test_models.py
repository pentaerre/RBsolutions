from unittest.mock import AsyncMock, patch

from app.services.ollama_client import normalize_models, pick_default_model


def test_normalize_models_keeps_every_installed_name() -> None:
    catalog = normalize_models(
        [
            {"name": "qwen2.5-coder:32b", "details": {"parameter_size": "32.8B"}},
            {"model": "llama3.1:8b", "details": {"family": "llama", "parameter_size": "8.0B"}},
            {"name": "qwen2.5-coder:32b"},
            {"name": ""},
        ]
    )
    assert [item["name"] for item in catalog] == ["qwen2.5-coder:32b", "llama3.1:8b"]


def test_pick_default_falls_back_to_first_installed() -> None:
    assert pick_default_model(["llama3.1:8b", "qwen2.5-coder:32b"], "missing") == "llama3.1:8b"
    assert pick_default_model(["llama3.1:8b", "qwen2.5-coder:32b"], "qwen2.5-coder:32b") == "qwen2.5-coder:32b"


def test_models_endpoint_lists_all_installed(client) -> None:
    fake = [
        {"name": "qwen2.5-coder:32b", "size": 1, "details": {"parameter_size": "32.8B"}},
        {"name": "llama3.1:8b", "size": 2, "details": {"parameter_size": "8.0B"}},
    ]
    with patch("app.services.ollama_client.OllamaClient.list_models", new=AsyncMock(return_value=fake)):
        response = client.get("/api/models")
    assert response.status_code == 200
    body = response.json()
    assert [item["name"] for item in body["models"]] == ["qwen2.5-coder:32b", "llama3.1:8b"]
    assert body["default"] in {item["name"] for item in body["models"]}

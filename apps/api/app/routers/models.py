from fastapi import APIRouter

from app.config import settings
from app.services.ollama_client import OllamaClient

router = APIRouter()


@router.get("/models")
async def list_models() -> dict:
    client = OllamaClient(settings)
    return await client.catalog()

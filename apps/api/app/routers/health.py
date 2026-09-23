from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.config import settings
from app.db.models import Agent, App, Tool
from app.db.session import get_db
from app.deps import get_vectorstore
from app.services.graphstore import get_graphstore
from app.services.ollama_client import OllamaClient
from app.services.vectorstore import VectorStore

router = APIRouter()


@router.get("/health")
async def health(
    store: VectorStore = Depends(get_vectorstore),
    db: Session = Depends(get_db),
) -> dict:
    ollama = OllamaClient(settings)
    ollama_status = await ollama.health()
    return {
        "service": settings.app_name.lower(),
        "ok": True,
        "ollama": ollama_status,
        "documents_dir": settings.documents_dir,
        "index": {"chunks": store.count()},
        "embed_backend": settings.embedding_backend or "hash",
        "vector": store.health(),
        "graph": get_graphstore().health(),
        "runtime": "langgraph",
        "platform": {
            "database": "ok",
            "apps": db.query(App).count(),
            "tools": db.query(Tool).count(),
            "agents": db.query(Agent).count(),
        },
    }

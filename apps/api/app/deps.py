from app.config import settings
from app.services.vectorstore import VectorStore

_store: VectorStore | None = None


def get_vectorstore() -> VectorStore:
    global _store
    if _store is None:
        _store = VectorStore(settings)
    return _store


def reset_vectorstore() -> None:
    global _store
    _store = None

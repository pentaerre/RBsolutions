import logging
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.db.seed import seed_catalog
from app.db.session import SessionLocal, init_db
from app.deps import get_vectorstore, reset_vectorstore
from app.routers import agents, apps, chat, documents, graph, health, library, models, runtime, utilities
from app.routers import catalog_tools
from app.watchers.folder import start_folder_watcher, stop_folder_watcher
from app.watchers.scheduler import start_scheduler, stop_scheduler

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("atrium")


def _boot_database() -> None:
    last_error: Exception | None = None
    for attempt in range(1, 31):
        try:
            init_db()
            db = SessionLocal()
            try:
                seed_catalog(db)
            finally:
                db.close()
            logger.info("Catalog ready")
            return
        except Exception as exc:  # pragma: no cover - retry around postgres boot
            last_error = exc
            logger.warning("Database not ready (%s/30): %s", attempt, exc)
            time.sleep(1)
    raise RuntimeError(f"Could not initialize database: {last_error}")


@asynccontextmanager
async def lifespan(_: FastAPI):
    _boot_database()
    store = None
    last_error: Exception | None = None
    for attempt in range(1, 21):
        try:
            store = get_vectorstore()
            if store.health().get("ok"):
                break
        except Exception as exc:
            last_error = exc
            logger.warning("Qdrant not ready (%s/20): %s", attempt, exc)
            reset_vectorstore()
            time.sleep(1)
    if store is None:
        raise RuntimeError(f"Could not reach Qdrant: {last_error}")
    if settings.watch_documents:
        start_folder_watcher(settings)
        start_scheduler()
        if not store.count():
            logger.info("Empty index; waiting for operators to promote documents into GraphRAG")
    try:
        yield
    finally:
        stop_scheduler()
        stop_folder_watcher()


app = FastAPI(title=f"{settings.app_name} Platform", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, prefix=settings.api_prefix, tags=["system"])
app.include_router(models.router, prefix=settings.api_prefix, tags=["models"])
app.include_router(documents.router, prefix=settings.api_prefix, tags=["documents"])
app.include_router(library.router, prefix=settings.api_prefix, tags=["library"])
app.include_router(chat.router, prefix=settings.api_prefix, tags=["runtime"])
app.include_router(runtime.router, prefix=settings.api_prefix, tags=["runtime"])
app.include_router(apps.router, prefix=settings.api_prefix, tags=["catalog"])
app.include_router(catalog_tools.router, prefix=settings.api_prefix, tags=["catalog"])
app.include_router(agents.router, prefix=settings.api_prefix, tags=["catalog"])
app.include_router(utilities.router, prefix=settings.api_prefix, tags=["catalog"])
app.include_router(graph.router, prefix=settings.api_prefix, tags=["graph"])

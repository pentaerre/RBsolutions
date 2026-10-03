import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

os.environ["WATCH_DOCUMENTS"] = "false"
os.environ["EMBEDDING_BACKEND"] = "hash"
os.environ["FILE_LLM"] = "false"
os.environ["EXTRACT_WITH_LLM"] = "false"
os.environ["DOCUMENTS_DIR"] = "/tmp/atrium-docs-test"
os.environ["DATABASE_URL"] = "sqlite:////tmp/atrium-test.db"
os.environ["QDRANT_URL"] = "memory"
os.environ["NEO4J_URI"] = ""
os.environ["TELEGRAM_BOT_TOKEN"] = ""
os.environ["SYNC_DOCS"] = "false"

Path("/tmp/atrium-test.db").unlink(missing_ok=True)

from app.db.seed import seed_catalog
from app.db.session import SessionLocal, init_db
from app.main import app


@pytest.fixture(autouse=True, scope="session")
def _platform_db() -> None:
    init_db()
    db = SessionLocal()
    try:
        seed_catalog(db)
    finally:
        db.close()


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client

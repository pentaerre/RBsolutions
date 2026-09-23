from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.config import settings
from app.db.session import get_db
from app.deps import get_vectorstore
from app.services import pipeline
from app.services.ingest import IngestService
from app.services.mailroom import poll_mailbox
from app.services.vectorstore import VectorStore

router = APIRouter()


@router.get("/documents")
def list_documents(store: VectorStore = Depends(get_vectorstore)) -> dict:
    ingest = IngestService(settings, store)
    return {"documents_dir": settings.documents_dir, "inbox": str(pipeline.inbox_dir()), "files": ingest.list_files()}


@router.post("/documents/ingest")
def ingest_documents(store: VectorStore = Depends(get_vectorstore), db: Session = Depends(get_db)) -> dict:
    return pipeline.process_all(store, db)


@router.post("/documents/mail")
def poll_mail() -> dict:
    return poll_mailbox(pipeline.inbox_dir())


@router.get("/records")
def list_records(db: Session = Depends(get_db)) -> dict:
    return {"records": pipeline.list_records(db)}

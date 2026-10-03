from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services import library

router = APIRouter()


class PromoteBody(BaseModel):
    ids: list[str] = []
    filenames: list[str] = []


class CadenceBody(BaseModel):
    cadence: str = "hour"
    taxonomist: str = "taxonomist"


@router.get("/library")
def list_library(
    day: str | None = None,
    l1: str | None = None,
    l2: str | None = None,
    q: str | None = None,
    rag: str | None = None,
    source: str | None = None,
    taxonomist: str | None = None,
    db: Session = Depends(get_db),
) -> dict:
    from app.services.taxonomy import resolve_slug

    live = resolve_slug(db, taxonomist)
    meta = library.meta(db, live)
    documents = library.list_documents(
        db, day=day, l1=l1, l2=l2, q=q, rag=rag, source=source, taxonomist=live
    )
    return {"documents": documents, **meta}


@router.get("/library/meta")
def library_meta(taxonomist: str | None = None, db: Session = Depends(get_db)) -> dict:
    from app.services.taxonomy import resolve_slug

    return library.meta(db, resolve_slug(db, taxonomist))


@router.get("/library/documents/{document_id}")
def library_document(document_id: str, db: Session = Depends(get_db)) -> dict:
    item = library.get_document(db, document_id)
    if item is None:
        raise HTTPException(status_code=404, detail="document not found")
    return item


@router.post("/library/run")
def library_run(taxonomist: str | None = None, db: Session = Depends(get_db)) -> dict:
    from app.services.taxonomy import resolve_slug

    return library.run_cycle(db, resolve_slug(db, taxonomist))


@router.post("/library/promote")
def library_promote(body: PromoteBody, db: Session = Depends(get_db)) -> dict:
    return library.promote(db, ids=body.ids, filenames=body.filenames)


@router.patch("/library/cadence")
def library_cadence(body: CadenceBody, db: Session = Depends(get_db)) -> dict:
    return library.set_cadence(db, body.cadence, body.taxonomist)

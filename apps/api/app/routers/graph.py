from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services.flow import live_flow
from app.services.platform_map import full_graph

router = APIRouter()


@router.get("/graph")
def get_graph(db: Session = Depends(get_db)) -> dict:
    return full_graph(db)


@router.get("/flow")
def get_flow(taxonomist: str | None = None, db: Session = Depends(get_db)) -> dict:
    return live_flow(db, taxonomist)

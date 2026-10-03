from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from fastapi import APIRouter, Depends, HTTPException

from app.db.session import get_db
from app.services import knobs

router = APIRouter()


class UtilityUpdate(BaseModel):
    values: dict[str, dict] = Field(default_factory=dict)


@router.get("/utilities")
def list_utilities(db: Session = Depends(get_db)) -> dict:
    return {"utilities": knobs.list_utilities(db)}


@router.get("/utilities/{slug}")
def get_utility(slug: str, db: Session = Depends(get_db)) -> dict:
    item = knobs.get_utility(db, slug)
    if item is None:
        raise HTTPException(status_code=404, detail="utility not found")
    return item


@router.patch("/utilities/{slug}")
def update_utility(slug: str, payload: UtilityUpdate, db: Session = Depends(get_db)) -> dict:
    try:
        return knobs.save_utility(db, slug, payload.values)
    except KeyError:
        raise HTTPException(status_code=404, detail="utility not found")

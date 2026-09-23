from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from fastapi import APIRouter, Depends, HTTPException

from app.db.models import App
from app.db.serialize import app_to_dict
from app.db.session import get_db

router = APIRouter()


class AppCreate(BaseModel):
    slug: str = Field(min_length=2, max_length=80)
    name: str = Field(min_length=2, max_length=160)
    kind: str = Field(default="tool", pattern="^(experience|admin|tool)$")
    base_url: str = ""
    status: str = Field(default="planned", pattern="^(live|planned|disabled)$")
    summary: str = ""


class AppUpdate(BaseModel):
    name: str | None = None
    kind: str | None = None
    base_url: str | None = None
    status: str | None = None
    summary: str | None = None


@router.get("/apps")
def list_apps(db: Session = Depends(get_db)) -> dict:
    rows = db.query(App).order_by(App.kind, App.name).all()
    return {"apps": [app_to_dict(row) for row in rows]}


@router.post("/apps", status_code=201)
def create_app(payload: AppCreate, db: Session = Depends(get_db)) -> dict:
    if db.query(App).filter(App.slug == payload.slug).first():
        raise HTTPException(status_code=409, detail="slug already exists")
    row = App(**payload.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    return app_to_dict(row)


@router.patch("/apps/{app_id}")
def update_app(app_id: str, payload: AppUpdate, db: Session = Depends(get_db)) -> dict:
    row = db.query(App).filter(App.id == app_id).first()
    if row is None:
        raise HTTPException(status_code=404, detail="app not found")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(row, key, value)
    db.commit()
    db.refresh(row)
    return app_to_dict(row)

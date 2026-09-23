import json

from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from fastapi import APIRouter, Depends, HTTPException

from app.db.models import Tool
from app.db.serialize import tool_to_dict
from app.db.session import get_db
from app.runtime.tools import ToolError, invoke_tool

router = APIRouter()


class ToolUpdate(BaseModel):
    name: str | None = None
    status: str | None = Field(default=None, pattern="^(live|planned|disabled)$")
    summary: str | None = None
    kind: str | None = None
    entrypoint: str | None = None
    config: dict | None = None


class ToolCreate(BaseModel):
    slug: str = Field(min_length=2, max_length=80)
    name: str = Field(min_length=2, max_length=160)
    kind: str = Field(default="http", pattern="^(builtin|http)$")
    status: str = Field(default="planned", pattern="^(live|planned|disabled)$")
    summary: str = ""
    entrypoint: str = ""
    config: dict = Field(default_factory=dict)


class InvokeRequest(BaseModel):
    payload: dict = Field(default_factory=dict)


@router.get("/tools")
def list_tools(db: Session = Depends(get_db)) -> dict:
    rows = db.query(Tool).order_by(Tool.name).all()
    return {"tools": [tool_to_dict(row) for row in rows]}


@router.post("/tools", status_code=201)
def create_tool(payload: ToolCreate, db: Session = Depends(get_db)) -> dict:
    if db.query(Tool).filter(Tool.slug == payload.slug).first():
        raise HTTPException(status_code=409, detail="slug already exists")
    data = payload.model_dump()
    config = data.pop("config") or {}
    row = Tool(**data, config_json=json.dumps(config))
    db.add(row)
    db.commit()
    db.refresh(row)
    return tool_to_dict(row)


@router.patch("/tools/{tool_id}")
def update_tool(tool_id: str, payload: ToolUpdate, db: Session = Depends(get_db)) -> dict:
    row = db.query(Tool).filter(Tool.id == tool_id).first()
    if row is None:
        raise HTTPException(status_code=404, detail="tool not found")
    data = payload.model_dump(exclude_unset=True)
    config = data.pop("config", None)
    for key, value in data.items():
        setattr(row, key, value)
    if config is not None:
        row.config_json = json.dumps(config)
    db.commit()
    db.refresh(row)
    return tool_to_dict(row)


@router.post("/tools/{slug}/invoke")
def run_tool(slug: str, payload: InvokeRequest, db: Session = Depends(get_db)) -> dict:
    try:
        return invoke_tool(db, slug, payload.payload)
    except ToolError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

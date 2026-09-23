import json

from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from fastapi import APIRouter, Depends, HTTPException

from app.db.models import Agent, AgentTool, Tool
from app.db.serialize import agent_to_dict
from app.db.session import get_db

router = APIRouter()


class AgentUpdate(BaseModel):
    name: str | None = None
    status: str | None = Field(default=None, pattern="^(live|planned|disabled)$")
    summary: str | None = None
    model: str | None = None
    system_prompt: str | None = None
    config: dict | None = None
    tools: list[str] | None = None


@router.get("/agents")
def list_agents(db: Session = Depends(get_db)) -> dict:
    rows = db.query(Agent).order_by(Agent.role, Agent.name).all()
    return {"agents": [agent_to_dict(row) for row in rows]}


@router.get("/agents/{agent_id}")
def get_agent(agent_id: str, db: Session = Depends(get_db)) -> dict:
    row = db.query(Agent).filter(Agent.id == agent_id).first()
    if row is None:
        raise HTTPException(status_code=404, detail="agent not found")
    return agent_to_dict(row)


@router.patch("/agents/{agent_id}")
def update_agent(agent_id: str, payload: AgentUpdate, db: Session = Depends(get_db)) -> dict:
    row = db.query(Agent).filter(Agent.id == agent_id).first()
    if row is None:
        raise HTTPException(status_code=404, detail="agent not found")
    data = payload.model_dump(exclude_unset=True)
    tool_slugs = data.pop("tools", None)
    config = data.pop("config", None)
    for key, value in data.items():
        setattr(row, key, value)
    if config is not None:
        row.config_json = json.dumps(config)
    if tool_slugs is not None:
        db.query(AgentTool).filter(AgentTool.agent_id == row.id).delete()
        for slug in tool_slugs:
            tool = db.query(Tool).filter(Tool.slug == slug).first()
            if tool is None:
                raise HTTPException(status_code=400, detail=f"unknown tool: {slug}")
            db.add(AgentTool(agent_id=row.id, tool_id=tool.id))
    db.commit()
    db.refresh(row)
    from app.services.scribe import try_sync_docs

    try_sync_docs(db)
    return agent_to_dict(row)

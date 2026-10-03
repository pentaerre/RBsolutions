from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


def _uuid() -> str:
    return str(uuid.uuid4())


class App(Base):
    __tablename__ = "apps"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    slug: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(160))
    kind: Mapped[str] = mapped_column(String(40))  # experience | admin | tool
    base_url: Mapped[str] = mapped_column(String(300), default="")
    status: Mapped[str] = mapped_column(String(20), default="planned")
    summary: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Tool(Base):
    __tablename__ = "tools"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    slug: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(160))
    kind: Mapped[str] = mapped_column(String(40), default="builtin")  # builtin | http
    status: Mapped[str] = mapped_column(String(20), default="live")
    summary: Mapped[str] = mapped_column(Text, default="")
    entrypoint: Mapped[str] = mapped_column(String(200), default="")
    config_json: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    agent_links: Mapped[list[AgentTool]] = relationship(back_populates="tool", cascade="all, delete-orphan")


class Agent(Base):
    __tablename__ = "agents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    slug: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(160))
    role: Mapped[str] = mapped_column(String(40), default="specialist")  # router | specialist
    status: Mapped[str] = mapped_column(String(20), default="live")
    summary: Mapped[str] = mapped_column(Text, default="")
    model: Mapped[str] = mapped_column(String(120), default="")
    system_prompt: Mapped[str] = mapped_column(Text, default="")
    config_json: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    tool_links: Mapped[list[AgentTool]] = relationship(back_populates="agent", cascade="all, delete-orphan")


class AgentTool(Base):
    __tablename__ = "agent_tools"
    __table_args__ = (UniqueConstraint("agent_id", "tool_id"),)

    agent_id: Mapped[str] = mapped_column(ForeignKey("agents.id"), primary_key=True)
    tool_id: Mapped[str] = mapped_column(ForeignKey("tools.id"), primary_key=True)
    agent: Mapped[Agent] = relationship(back_populates="tool_links")
    tool: Mapped[Tool] = relationship(back_populates="agent_links")


class IntakeDocument(Base):
    __tablename__ = "intake_documents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    filename: Mapped[str] = mapped_column(String(260), index=True)
    rel_path: Mapped[str] = mapped_column(String(512), unique=True, index=True, default="")
    abs_path: Mapped[str] = mapped_column(String(800), default="")
    source: Mapped[str] = mapped_column(String(40), default="folder")  # folder | email | telegram
    source_ref: Mapped[str] = mapped_column(String(300), default="")
    suffix: Mapped[str] = mapped_column(String(20), default="")
    doc_type: Mapped[str] = mapped_column(String(40), default="unknown")
    taxonomy_l1: Mapped[str] = mapped_column(String(80), default="")
    taxonomy_l2: Mapped[str] = mapped_column(String(80), default="")
    taxonomist_slug: Mapped[str] = mapped_column(String(80), default="")
    status: Mapped[str] = mapped_column(String(20), default="received")
    pages: Mapped[int] = mapped_column(Integer, default=0)
    read_pages: Mapped[int] = mapped_column(Integer, default=0)
    chunks: Mapped[int] = mapped_column(Integer, default=0)
    records: Mapped[int] = mapped_column(Integer, default=0)
    size_bytes: Mapped[int] = mapped_column(Integer, default=0)
    ocr_used: Mapped[int] = mapped_column(Integer, default=0)
    rag_selected: Mapped[int] = mapped_column(Integer, default=0)
    summary: Mapped[str] = mapped_column(Text, default="")
    keywords: Mapped[str] = mapped_column(Text, default="[]")
    text_preview: Mapped[str] = mapped_column(Text, default="")
    classified_path: Mapped[str] = mapped_column(String(400), default="")
    classify_method: Mapped[str] = mapped_column(String(20), default="")
    classify_note: Mapped[str] = mapped_column(String(160), default="")
    error: Mapped[str] = mapped_column(Text, default="")
    file_created_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    extractions: Mapped[list[ExtractedRecord]] = relationship(back_populates="document", cascade="all, delete-orphan")


class ExtractedRecord(Base):
    __tablename__ = "extracted_records"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    document_id: Mapped[str] = mapped_column(ForeignKey("intake_documents.id"), index=True)
    kind: Mapped[str] = mapped_column(String(40), default="document")
    payload_json: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    document: Mapped[IntakeDocument] = relationship(back_populates="extractions")


class MailboxLetter(Base):
    """One shared-inbox letter. Mailroom stores it; Sentinel judges it."""

    __tablename__ = "mailbox_letters"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    message_key: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    mailbox: Mapped[str] = mapped_column(String(120), default="INBOX")
    sender: Mapped[str] = mapped_column(String(300), default="")
    subject: Mapped[str] = mapped_column(String(400), default="")
    body: Mapped[str] = mapped_column(Text, default="")
    received_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    scanned: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    signals: Mapped[list["OperationalSignal"]] = relationship(back_populates="letter", cascade="all, delete-orphan")


class OperationalSignal(Base):
    """A brief for direction: legal risk, opportunity, or churn. Not a personal reply."""

    __tablename__ = "operational_signals"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    letter_id: Mapped[str] = mapped_column(ForeignKey("mailbox_letters.id"), index=True)
    kind: Mapped[str] = mapped_column(String(40), default="")  # legal | opportunity | churn
    severity: Mapped[str] = mapped_column(String(20), default="medium")
    party: Mapped[str] = mapped_column(String(160), default="")
    evidence: Mapped[str] = mapped_column(String(200), default="")
    brief: Mapped[str] = mapped_column(Text, default="")
    graph_json: Mapped[str] = mapped_column(Text, default="{}")
    ledger_json: Mapped[str] = mapped_column(Text, default="[]")
    status: Mapped[str] = mapped_column(String(20), default="open")
    notified: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    letter: Mapped[MailboxLetter] = relationship(back_populates="signals")

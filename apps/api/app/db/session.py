from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import settings


class Base(DeclarativeBase):
    pass


connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
engine = create_engine(settings.database_url, future=True, pool_pre_ping=True, connect_args=connect_args)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    from app.db import models  # noqa: F401

    Base.metadata.create_all(bind=engine)
    migrate_schema()


def migrate_schema() -> None:
    from sqlalchemy import inspect, text

    inspector = inspect(engine)
    if "intake_documents" not in inspector.get_table_names():
        return
    existing = {col["name"] for col in inspector.get_columns("intake_documents")}
    dialect = engine.dialect.name
    datetime_type = "TIMESTAMP" if dialect == "postgresql" else "DATETIME"
    columns = [
        ("rel_path", "VARCHAR(512)"),
        ("abs_path", "VARCHAR(800)"),
        ("taxonomy_l1", "VARCHAR(80)"),
        ("taxonomy_l2", "VARCHAR(80)"),
        ("taxonomist_slug", "VARCHAR(80)"),
        ("read_pages", "INTEGER"),
        ("size_bytes", "INTEGER"),
        ("ocr_used", "INTEGER"),
        ("rag_selected", "INTEGER"),
        ("summary", "TEXT"),
        ("keywords", "TEXT"),
        ("classified_path", "VARCHAR(400)"),
        ("classify_method", "VARCHAR(20)"),
        ("classify_note", "VARCHAR(160)"),
        ("file_created_at", datetime_type),
    ]
    with engine.begin() as conn:
        for name, col_type in columns:
            if name not in existing:
                conn.execute(text(f"ALTER TABLE intake_documents ADD COLUMN {name} {col_type}"))
        conn.execute(
            text("UPDATE intake_documents SET rel_path = filename WHERE rel_path IS NULL OR rel_path = ''")
        )
        if dialect == "postgresql":
            conn.execute(text("ALTER TABLE intake_documents DROP CONSTRAINT IF EXISTS intake_documents_filename_key"))
            conn.execute(text("DROP INDEX IF EXISTS ix_intake_documents_filename"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS ix_intake_documents_filename ON intake_documents (filename)"))
            conn.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS uq_intake_rel_path ON intake_documents (rel_path)"))

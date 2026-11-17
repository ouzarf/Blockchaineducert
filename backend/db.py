from __future__ import annotations

import os
from pathlib import Path
from sqlalchemy import create_engine, DateTime, Integer, String, Text, func, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

BASE_DIR = Path(__file__).resolve().parent.parent
DATABASE_URL = os.getenv("DATABASE_URL", "").strip()
if not DATABASE_URL.startswith("postgresql+psycopg://"):
    raise RuntimeError("DATABASE_URL PostgreSQL obligatoire: utilisez postgresql+psycopg://...")
connect_args = {}
engine = create_engine(DATABASE_URL, future=True, pool_pre_ping=True, connect_args=connect_args)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

class Base(DeclarativeBase):
    pass

class Certificate(Base):
    __tablename__ = "certificates"
    __table_args__ = (UniqueConstraint("certificate_id", "version", name="uq_certificate_version"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    certificate_id: Mapped[str] = mapped_column(String(180), nullable=False, index=True)
    university_id: Mapped[str] = mapped_column(String(180), nullable=False)
    faculty_id: Mapped[str | None] = mapped_column(String(180))
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    document_hash: Mapped[str] = mapped_column(String(66), nullable=False)
    issuer: Mapped[str] = mapped_column(String(42), nullable=False)
    tx_hash: Mapped[str | None] = mapped_column(String(100))
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="ACTIVE")
    created_at: Mapped[object] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    revoked_at: Mapped[object | None] = mapped_column(DateTime)

class AuditEvent(Base):
    __tablename__ = "audit_events"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    event_type: Mapped[str] = mapped_column(String(60), nullable=False)
    certificate_id: Mapped[str | None] = mapped_column(String(180), index=True)
    version: Mapped[int | None] = mapped_column(Integer)
    actor: Mapped[str | None] = mapped_column(String(180))
    tx_hash: Mapped[str | None] = mapped_column(String(100))
    details: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[object] = mapped_column(DateTime, server_default=func.now(), nullable=False)

def init_db() -> None:
    Base.metadata.create_all(bind=engine)

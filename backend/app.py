from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from .db import AuditEvent, Certificate, SessionLocal, init_db

app = FastAPI(title="EduCert Maroc off-chain API", version="1.1.0")
origins = [x.strip() for x in os.getenv("EDUCERT_CORS_ORIGINS", "*").split(",") if x.strip()]
app.add_middleware(CORSMiddleware, allow_origins=origins, allow_credentials=False, allow_methods=["GET", "POST", "PATCH"], allow_headers=["*"])

@app.on_event("startup")
def startup() -> None:
    init_db()

class CertificateIn(BaseModel):
    certificate_id: str = Field(min_length=1, max_length=180)
    university_id: str = Field(min_length=1, max_length=180)
    faculty_id: str | None = Field(default=None, max_length=180)
    version: int = Field(ge=1)
    document_hash: str = Field(pattern=r"^0x[0-9a-fA-F]{64}$")
    issuer: str = Field(min_length=42, max_length=42)
    tx_hash: str | None = None
    status: str = Field(default="ACTIVE", pattern=r"^(ACTIVE|REVOKED|SUPERSEDED)$")

class StatusIn(BaseModel):
    status: str = Field(pattern=r"^(ACTIVE|REVOKED|SUPERSEDED)$")
    tx_hash: str | None = None
    actor: str | None = Field(default=None, min_length=42, max_length=42)

def as_json(row: Any) -> dict[str, Any]:
    data = {column.name: getattr(row, column.name) for column in row.__table__.columns}
    for key, value in data.items():
        if isinstance(value, datetime):
            data[key] = value.isoformat()
    return data

@app.get("/api/health")
def health() -> dict[str, Any]:
    return {"ok": True, "database": "postgresql", "service": "educert-offchain"}

@app.post("/api/certificates", status_code=201)
def save_certificate(item: CertificateIn) -> dict[str, Any]:
    with SessionLocal() as session:
        payload = item.model_dump()
        payload["document_hash"] = item.document_hash.lower()
        certificate = Certificate(**payload)
        session.add(certificate)
        session.add(AuditEvent(event_type="CERTIFICATE_ISSUED", certificate_id=item.certificate_id, version=item.version, actor=item.issuer, tx_hash=item.tx_hash, details=item.status))
        try:
            session.commit()
        except IntegrityError as exc:
            session.rollback()
            raise HTTPException(409, "Ce certificat/version existe déjà") from exc
        session.refresh(certificate)
        return {"id": certificate.id, "saved": True}

@app.get("/api/certificates/{certificate_id}")
def list_certificate(certificate_id: str):
    with SessionLocal() as session:
        rows = session.scalars(select(Certificate).where(Certificate.certificate_id == certificate_id).order_by(Certificate.version)).all()
        return [as_json(row) for row in rows]

@app.get("/api/certificates/{certificate_id}/{version}")
def get_certificate(certificate_id: str, version: int):
    with SessionLocal() as session:
        row = session.scalar(select(Certificate).where(Certificate.certificate_id == certificate_id, Certificate.version == version))
        if row is None:
            raise HTTPException(404, "Certificat absent")
        return as_json(row)

@app.patch("/api/certificates/{certificate_id}/{version}/status")
def update_status(certificate_id: str, version: int, item: StatusIn):
    with SessionLocal() as session:
        row = session.scalar(select(Certificate).where(Certificate.certificate_id == certificate_id, Certificate.version == version))
        if row is None:
            raise HTTPException(404, "Certificat absent")
        row.status = item.status
        if item.tx_hash:
            row.tx_hash = item.tx_hash
        if item.status == "REVOKED":
            row.revoked_at = datetime.now(timezone.utc)
        session.add(AuditEvent(event_type="CERTIFICATE_STATUS_CHANGED", certificate_id=certificate_id, version=version, actor=item.actor, tx_hash=item.tx_hash, details=item.status))
        session.commit()
        return {"updated": True}

@app.get("/api/audit/{certificate_id}")
def list_audit(certificate_id: str):
    with SessionLocal() as session:
        rows = session.scalars(select(AuditEvent).where(AuditEvent.certificate_id == certificate_id).order_by(AuditEvent.id)).all()
        return [as_json(row) for row in rows]

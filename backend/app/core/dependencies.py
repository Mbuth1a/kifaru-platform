from uuid import UUID

from fastapi import Header

from app.core.database import SessionLocal


def get_db():
    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()


def get_tenant_id(x_tenant_id: UUID = Header(...)) -> UUID:
    return x_tenant_id
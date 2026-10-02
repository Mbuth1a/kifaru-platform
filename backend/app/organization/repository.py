from sqlalchemy.orm import Session

from .models import LegalEntity


class LegalEntityRepository:

    def create(self, db: Session, entity: LegalEntity):
        db.add(entity)
        db.flush()
        return entity

    def get(self, db: Session, entity_id):
        return (
            db.query(LegalEntity)
            .filter(LegalEntity.id == entity_id)
            .first()
        )

    def list_by_tenant(self, db: Session, tenant_id):
        return (
            db.query(LegalEntity)
            .filter(LegalEntity.tenant_id == tenant_id)
            .all()
        )

    def exists_by_name(self, db: Session, tenant_id, name):
        return (
            db.query(LegalEntity)
            .filter(
                LegalEntity.tenant_id == tenant_id,
                LegalEntity.legal_name == name,
            )
            .first()
            is not None
        )
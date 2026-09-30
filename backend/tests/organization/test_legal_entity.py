import pytest
from sqlalchemy.exc import IntegrityError

from app.organization.models import (
    Tenant,
    LegalEntity,
)


def test_create_legal_entity(db):

    tenant = Tenant(
        legal_name="Kifaru Group",
        country_code="KE",
        currency_code="KES",
        timezone="Africa/Nairobi",
    )

    db.add(tenant)
    db.commit()
    db.refresh(tenant)

    entity = LegalEntity(
        tenant_id=tenant.id,
        legal_name="Kifaru Kenya Ltd",
        country_code="KE",
        currency_code="KES",
        timezone="Africa/Nairobi",
    )

    db.add(entity)
    db.commit()
    db.refresh(entity)

    assert entity.id is not None
    assert entity.tenant_id == tenant.id



def test_duplicate_legal_name_same_tenant(db):

    tenant = Tenant(
        legal_name="Group",
        country_code="KE",
        currency_code="KES",
        timezone="Africa/Nairobi",
    )

    db.add(tenant)
    db.commit()
    db.refresh(tenant)

    first = LegalEntity(
        tenant_id=tenant.id,
        legal_name="Kifaru Kenya Ltd",
        country_code="KE",
        currency_code="KES",
        timezone="Africa/Nairobi",
    )

    second = LegalEntity(
        tenant_id=tenant.id,
        legal_name="Kifaru Kenya Ltd",
        country_code="KE",
        currency_code="KES",
        timezone="Africa/Nairobi",
    )

    db.add(first)
    db.commit()

    db.add(second)

    with pytest.raises(IntegrityError):
        db.commit()
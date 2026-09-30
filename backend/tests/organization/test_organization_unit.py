from datetime import datetime, timezone

from app.organization.enums import OrganizationUnitType
from app.organization.models import (
    LegalEntity,
    OrganizationUnit,
    Tenant,
)


def test_create_organization_unit(db):
    tenant = Tenant(
        legal_name="Kifaru Group",
        country_code="KE",
        currency_code="KES",
        timezone="Africa/Nairobi",
    )

    db.add(tenant)
    db.commit()
    db.refresh(tenant)

    legal_entity = LegalEntity(
        tenant_id=tenant.id,
        legal_name="Kifaru Kenya Ltd",
        country_code="KE",
        currency_code="KES",
        timezone="Africa/Nairobi",
    )

    db.add(legal_entity)
    db.commit()
    db.refresh(legal_entity)

    unit = OrganizationUnit(
        tenant_id=tenant.id,
        legal_entity_id=legal_entity.id,
        code="TECH",
        name="Technology",
        unit_type=OrganizationUnitType.DIVISION,
        effective_from=datetime.now(timezone.utc),
    )

    db.add(unit)
    db.commit()
    db.refresh(unit)

    assert unit.id is not None
    assert unit.tenant_id == tenant.id
    assert unit.legal_entity_id == legal_entity.id
    assert unit.parent_id is None


    
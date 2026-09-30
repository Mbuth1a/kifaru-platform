import pytest
from datetime import datetime, timezone

from app.organization.enums import OrganizationUnitType
from app.organization.models import (
    LegalEntity,
    OrganizationUnit,
    Tenant,
)

from sqlalchemy.exc import IntegrityError
def test_parent_must_belong_to_same_tenant(db):
    tenant_a = Tenant(
        legal_name="Tenant A",
        country_code="KE",
        currency_code="KES",
        timezone="Africa/Nairobi",
    )

    tenant_b = Tenant(
        legal_name="Tenant B",
        country_code="KE",
        currency_code="KES",
        timezone="Africa/Nairobi",
    )

    db.add_all([tenant_a, tenant_b])
    db.commit()
    db.refresh(tenant_a)
    db.refresh(tenant_b)

    parent = OrganizationUnit(
        tenant_id=tenant_a.id,
        code="TECH",
        name="Technology",
        unit_type=OrganizationUnitType.DIVISION,
        effective_from=datetime.now(timezone.utc),
    )

    db.add(parent)
    db.commit()
    db.refresh(parent)

    malicious_child = OrganizationUnit(
        tenant_id=tenant_b.id,
        parent_id=parent.id,
        code="INFRA",
        name="Infrastructure",
        unit_type=OrganizationUnitType.DEPARTMENT,
        effective_from=datetime.now(timezone.utc),
    )

    db.add(malicious_child)

    with pytest.raises(IntegrityError):
        db.commit()

    db.rollback()
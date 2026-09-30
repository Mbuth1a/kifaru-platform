from datetime import datetime, timezone
from uuid import uuid4

import pytest

from app.organization.models import (
    OrganizationUnitType,
    Tenant,
)
from app.organization.service import OrganizationUnitService


def create_test_tenant(db):
    tenant = Tenant(
        legal_name="Service Test Tenant",
        trading_name="Service Test",
        country_code="KE",
        timezone="Africa/Nairobi",
        currency_code="KES",
    )

    db.add(tenant)
    db.flush()

    return tenant


def test_create_organization_unit_service(db):
    tenant = create_test_tenant(db)

    service = OrganizationUnitService(db)

    unit = service.create(
        tenant_id=tenant.id,
        code="TECH",
        name="Technology",
        unit_type=OrganizationUnitType.DIVISION,
        effective_from=datetime.now(timezone.utc),
    )

    assert unit.id is not None
    assert unit.tenant_id == tenant.id
    assert unit.code == "TECH"
    assert unit.name == "Technology"


def test_cannot_create_unit_with_invalid_parent(db):
    tenant = create_test_tenant(db)

    service = OrganizationUnitService(db)

    with pytest.raises(
        ValueError,
        match="Parent organization unit not found",
    ):
        service.create(
            tenant_id=tenant.id,
            code="INFRA",
            name="Infrastructure",
            unit_type=OrganizationUnitType.DEPARTMENT,
            effective_from=datetime.now(timezone.utc),
            parent_id=uuid4(),
        )


def test_cannot_make_unit_its_own_parent(db):
    tenant = create_test_tenant(db)

    service = OrganizationUnitService(db)

    unit = service.create(
        tenant_id=tenant.id,
        code="TECH",
        name="Technology",
        unit_type=OrganizationUnitType.DIVISION,
        effective_from=datetime.now(timezone.utc),
    )

    with pytest.raises(
        ValueError,
        match="cannot be its own parent",
    ):
        service.change_parent(
            tenant_id=tenant.id,
            unit_id=unit.id,
            new_parent_id=unit.id,
        )


def test_cannot_create_cycle(db):
    tenant = create_test_tenant(db)

    service = OrganizationUnitService(db)

    technology = service.create(
        tenant_id=tenant.id,
        code="TECH",
        name="Technology",
        unit_type=OrganizationUnitType.DIVISION,
        effective_from=datetime.now(timezone.utc),
    )

    infrastructure = service.create(
        tenant_id=tenant.id,
        code="INFRA",
        name="Infrastructure",
        unit_type=OrganizationUnitType.DEPARTMENT,
        parent_id=technology.id,
        effective_from=datetime.now(timezone.utc),
    )

    cloud = service.create(
        tenant_id=tenant.id,
        code="CLOUD",
        name="Cloud",
        unit_type=OrganizationUnitType.TEAM,
        parent_id=infrastructure.id,
        effective_from=datetime.now(timezone.utc),
    )

    with pytest.raises(
        ValueError,
        match="hierarchy cycle",
    ):
        service.change_parent(
            tenant_id=tenant.id,
            unit_id=technology.id,
            new_parent_id=cloud.id,
        )


def test_get_children(db):
    tenant = create_test_tenant(db)

    service = OrganizationUnitService(db)

    technology = service.create(
        tenant_id=tenant.id,
        code="TECH",
        name="Technology",
        unit_type=OrganizationUnitType.DIVISION,
        effective_from=datetime.now(timezone.utc),
    )

    service.create(
        tenant_id=tenant.id,
        code="INFRA",
        name="Infrastructure",
        unit_type=OrganizationUnitType.DEPARTMENT,
        parent_id=technology.id,
        effective_from=datetime.now(timezone.utc),
    )

    service.create(
        tenant_id=tenant.id,
        code="APPS",
        name="Applications",
        unit_type=OrganizationUnitType.DEPARTMENT,
        parent_id=technology.id,
        effective_from=datetime.now(timezone.utc),
    )

    children = service.get_children(
        tenant_id=tenant.id,
        unit_id=technology.id,
    )

    assert len(children) == 2
    assert [child.code for child in children] == [
        "APPS",
        "INFRA",
    ]


def test_get_descendants(db):
    tenant = create_test_tenant(db)

    service = OrganizationUnitService(db)

    technology = service.create(
        tenant_id=tenant.id,
        code="TECH",
        name="Technology",
        unit_type=OrganizationUnitType.DIVISION,
        effective_from=datetime.now(timezone.utc),
    )

    infrastructure = service.create(
        tenant_id=tenant.id,
        code="INFRA",
        name="Infrastructure",
        unit_type=OrganizationUnitType.DEPARTMENT,
        parent_id=technology.id,
        effective_from=datetime.now(timezone.utc),
    )

    service.create(
        tenant_id=tenant.id,
        code="CLOUD",
        name="Cloud",
        unit_type=OrganizationUnitType.TEAM,
        parent_id=infrastructure.id,
        effective_from=datetime.now(timezone.utc),
    )

    service.create(
        tenant_id=tenant.id,
        code="NETWORK",
        name="Network",
        unit_type=OrganizationUnitType.TEAM,
        parent_id=infrastructure.id,
        effective_from=datetime.now(timezone.utc),
    )

    descendants = service.get_descendants(
        tenant_id=tenant.id,
        unit_id=technology.id,
    )

    assert len(descendants) == 3
    assert {unit.code for unit in descendants} == {
        "INFRA",
        "CLOUD",
        "NETWORK",
    }


def test_get_ancestors(db):
    tenant = create_test_tenant(db)

    service = OrganizationUnitService(db)

    technology = service.create(
        tenant_id=tenant.id,
        code="TECH",
        name="Technology",
        unit_type=OrganizationUnitType.DIVISION,
        effective_from=datetime.now(timezone.utc),
    )

    infrastructure = service.create(
        tenant_id=tenant.id,
        code="INFRA",
        name="Infrastructure",
        unit_type=OrganizationUnitType.DEPARTMENT,
        parent_id=technology.id,
        effective_from=datetime.now(timezone.utc),
    )

    cloud = service.create(
        tenant_id=tenant.id,
        code="CLOUD",
        name="Cloud",
        unit_type=OrganizationUnitType.TEAM,
        parent_id=infrastructure.id,
        effective_from=datetime.now(timezone.utc),
    )

    ancestors = service.get_ancestors(
        tenant_id=tenant.id,
        unit_id=cloud.id,
    )

    assert [unit.code for unit in ancestors] == [
        "INFRA",
        "TECH",
    ]

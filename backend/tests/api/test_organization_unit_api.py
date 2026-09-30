from datetime import datetime, timezone
from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import app
from app.organization.models import Tenant


client = TestClient(app)


def create_test_tenant(db):
    tenant = Tenant(
        legal_name="API Test Tenant",
        trading_name="API Test",
        country_code="KE",
        timezone="Africa/Nairobi",
        currency_code="KES",
    )

    db.add(tenant)
    db.flush()

    return tenant


def test_create_organization_unit_api(db):
    tenant = create_test_tenant(db)

    response = client.post(
        "/organization/units",
        headers={
            "X-Tenant-ID": str(tenant.id),
        },
        json={
            "code": "TECH",
            "name": "Technology",
            "unit_type": "DIVISION",
            "effective_from": datetime.now(
                timezone.utc
            ).isoformat(),
        },
    )

    assert response.status_code == 201

    data = response.json()

    assert data["tenant_id"] == str(tenant.id)
    assert data["code"] == "TECH"
    assert data["name"] == "Technology"
    assert data["unit_type"] == "DIVISION"


def test_get_organization_unit_api(db):
    tenant = create_test_tenant(db)

    create_response = client.post(
        "/organization/units",
        headers={
            "X-Tenant-ID": str(tenant.id),
        },
        json={
            "code": "TECH",
            "name": "Technology",
            "unit_type": "DIVISION",
            "effective_from": datetime.now(
                timezone.utc
            ).isoformat(),
        },
    )

    assert create_response.status_code == 201

    unit_id = create_response.json()["id"]

    response = client.get(
        f"/organization/units/{unit_id}",
        headers={
            "X-Tenant-ID": str(tenant.id),
        },
    )

    assert response.status_code == 200
    assert response.json()["id"] == unit_id


def test_get_organization_unit_cannot_cross_tenant(db):
    tenant_a = create_test_tenant(db)
    tenant_b = create_test_tenant(db)

    create_response = client.post(
        "/organization/units",
        headers={
            "X-Tenant-ID": str(tenant_a.id),
        },
        json={
            "code": "TECH",
            "name": "Technology",
            "unit_type": "DIVISION",
            "effective_from": datetime.now(
                timezone.utc
            ).isoformat(),
        },
    )

    assert create_response.status_code == 201

    unit_id = create_response.json()["id"]

    response = client.get(
        f"/organization/units/{unit_id}",
        headers={
            "X-Tenant-ID": str(tenant_b.id),
        },
    )

    assert response.status_code == 404


def test_get_nonexistent_organization_unit_api(db):
    tenant = create_test_tenant(db)

    response = client.get(
        f"/organization/units/{uuid4()}",
        headers={
            "X-Tenant-ID": str(tenant.id),
        },
    )

    assert response.status_code == 404
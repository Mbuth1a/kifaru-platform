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




def test_change_organization_unit_parent_api(db):
    tenant = create_test_tenant(db)

    parent_response = client.post(
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

    assert parent_response.status_code == 201

    parent_id = parent_response.json()["id"]

    child_response = client.post(
        "/organization/units",
        headers={
            "X-Tenant-ID": str(tenant.id),
        },
        json={
            "code": "SEC",
            "name": "Security",
            "unit_type": "DEPARTMENT",
            "effective_from": datetime.now(
                timezone.utc
            ).isoformat(),
        },
    )

    assert child_response.status_code == 201

    child_id = child_response.json()["id"]

    response = client.patch(
        f"/organization/units/{child_id}/parent",
        headers={
            "X-Tenant-ID": str(tenant.id),
        },
        json={
            "parent_id": parent_id,
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["id"] == child_id
    assert data["parent_id"] == parent_id


def test_change_organization_unit_cannot_be_its_own_parent_api(db):
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

    response = client.patch(
        f"/organization/units/{unit_id}/parent",
        headers={
            "X-Tenant-ID": str(tenant.id),
        },
        json={
            "parent_id": unit_id,
        },
    )

    assert response.status_code == 400
    assert "own parent" in response.json()["detail"].lower()



def test_change_organization_unit_invalid_parent_api(db):
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

    response = client.patch(
        f"/organization/units/{unit_id}/parent",
        headers={
            "X-Tenant-ID": str(tenant.id),
        },
        json={
            "parent_id": str(uuid4()),
        },
    )

    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()




def test_get_organization_unit_children_api(db):
    tenant = create_test_tenant(db)

    parent_response = client.post(
        "/organization/units",
        headers={"X-Tenant-ID": str(tenant.id)},
        json={
            "code": "TECH",
            "name": "Technology Division",
            "unit_type": "DIVISION",
            "effective_from": "2026-01-01T00:00:00Z",
        },
    )

    assert parent_response.status_code == 201
    parent_id = parent_response.json()["id"]

    child_response = client.post(
        "/organization/units",
        headers={"X-Tenant-ID": str(tenant.id)},
        json={
            "code": "SEC",
            "name": "Security Department",
            "unit_type": "DEPARTMENT",
            "parent_id": parent_id,
            "effective_from": "2026-01-01T00:00:00Z",
        },
    )

    assert child_response.status_code == 201
    child_id = child_response.json()["id"]

    response = client.get(
        f"/organization/units/{parent_id}/children",
        headers={"X-Tenant-ID": str(tenant.id)},
    )

    assert response.status_code == 200

    data = response.json()

    assert len(data) == 1
    assert data[0]["id"] == child_id
    assert data[0]["parent_id"] == parent_id
    assert data[0]["code"] == "SEC"


def test_get_organization_unit_descendants_api(db):
    tenant = create_test_tenant(db)

    root_response = client.post(
        "/organization/units",
        headers={"X-Tenant-ID": str(tenant.id)},
        json={
            "code": "TECH",
            "name": "Technology Division",
            "unit_type": "DIVISION",
            "effective_from": "2026-01-01T00:00:00Z",
        },
    )

    assert root_response.status_code == 201
    root_id = root_response.json()["id"]

    child_response = client.post(
        "/organization/units",
        headers={"X-Tenant-ID": str(tenant.id)},
        json={
            "code": "SEC",
            "name": "Security Department",
            "unit_type": "DEPARTMENT",
            "parent_id": root_id,
            "effective_from": "2026-01-01T00:00:00Z",
        },
    )

    assert child_response.status_code == 201
    child_id = child_response.json()["id"]

    grandchild_response = client.post(
        "/organization/units",
        headers={"X-Tenant-ID": str(tenant.id)},
        json={
            "code": "SOC",
            "name": "Security Operations Team",
            "unit_type": "TEAM",
            "parent_id": child_id,
            "effective_from": "2026-01-01T00:00:00Z",
        },
    )

    assert grandchild_response.status_code == 201
    grandchild_id = grandchild_response.json()["id"]

    response = client.get(
        f"/organization/units/{root_id}/descendants",
        headers={"X-Tenant-ID": str(tenant.id)},
    )

    assert response.status_code == 200

    data = response.json()
    returned_ids = {item["id"] for item in data}

    assert len(data) == 2
    assert child_id in returned_ids
    assert grandchild_id in returned_ids




def test_get_organization_unit_ancestors_api(db):
    tenant = create_test_tenant(db)

    root_response = client.post(
        "/organization/units",
        headers={"X-Tenant-ID": str(tenant.id)},
        json={
            "code": "TECH",
            "name": "Technology Division",
            "unit_type": "DIVISION",
            "effective_from": "2026-01-01T00:00:00Z",
        },
    )

    assert root_response.status_code == 201
    root_id = root_response.json()["id"]

    child_response = client.post(
        "/organization/units",
        headers={"X-Tenant-ID": str(tenant.id)},
        json={
            "code": "SEC",
            "name": "Security Department",
            "unit_type": "DEPARTMENT",
            "parent_id": root_id,
            "effective_from": "2026-01-01T00:00:00Z",
        },
    )

    assert child_response.status_code == 201
    child_id = child_response.json()["id"]

    grandchild_response = client.post(
        "/organization/units",
        headers={"X-Tenant-ID": str(tenant.id)},
        json={
            "code": "SOC",
            "name": "Security Operations Team",
            "unit_type": "TEAM",
            "parent_id": child_id,
            "effective_from": "2026-01-01T00:00:00Z",
        },
    )

    assert grandchild_response.status_code == 201
    grandchild_id = grandchild_response.json()["id"]

    response = client.get(
        f"/organization/units/{grandchild_id}/ancestors",
        headers={"X-Tenant-ID": str(tenant.id)},
    )

    assert response.status_code == 200

    data = response.json()

    assert len(data) == 2
    assert data[0]["id"] == child_id
    assert data[1]["id"] == root_id



def test_get_organization_unit_children_cannot_cross_tenant(db):
    tenant_a = create_test_tenant(db)
    tenant_b = create_test_tenant(db)

    response = client.post(
        "/organization/units",
        headers={"X-Tenant-ID": str(tenant_b.id)},
        json={
            "code": "TECH",
            "name": "Technology Division",
            "unit_type": "DIVISION",
            "effective_from": "2026-01-01T00:00:00Z",
        },
    )

    assert response.status_code == 201
    unit_id = response.json()["id"]

    response = client.get(
        f"/organization/units/{unit_id}/children",
        headers={"X-Tenant-ID": str(tenant_a.id)},
    )

    assert response.status_code == 404


def test_get_organization_unit_descendants_cannot_cross_tenant(db):
    tenant_a = create_test_tenant(db)
    tenant_b = create_test_tenant(db)

    response = client.post(
        "/organization/units",
        headers={"X-Tenant-ID": str(tenant_b.id)},
        json={
            "code": "TECH",
            "name": "Technology Division",
            "unit_type": "DIVISION",
            "effective_from": "2026-01-01T00:00:00Z",
        },
    )

    assert response.status_code == 201
    unit_id = response.json()["id"]

    response = client.get(
        f"/organization/units/{unit_id}/descendants",
        headers={"X-Tenant-ID": str(tenant_a.id)},
    )

    assert response.status_code == 404





def test_get_organization_unit_ancestors_cannot_cross_tenant(db):
    tenant_a = create_test_tenant(db)
    tenant_b = create_test_tenant(db)

    response = client.post(
        "/organization/units",
        headers={"X-Tenant-ID": str(tenant_b.id)},
        json={
            "code": "TECH",
            "name": "Technology Division",
            "unit_type": "DIVISION",
            "effective_from": "2026-01-01T00:00:00Z",
        },
    )

    assert response.status_code == 201
    unit_id = response.json()["id"]

    response = client.get(
        f"/organization/units/{unit_id}/ancestors",
        headers={"X-Tenant-ID": str(tenant_a.id)},
    )

    assert response.status_code == 404


def test_change_organization_unit_parent_cannot_cross_tenant(db):
    tenant_a = create_test_tenant(db)
    tenant_b = create_test_tenant(db)

    child_response = client.post(
        "/organization/units",
        headers={"X-Tenant-ID": str(tenant_a.id)},
        json={
            "code": "SEC",
            "name": "Security Department",
            "unit_type": "DEPARTMENT",
            "effective_from": "2026-01-01T00:00:00Z",
        },
    )

    assert child_response.status_code == 201
    child_id = child_response.json()["id"]

    parent_response = client.post(
        "/organization/units",
        headers={"X-Tenant-ID": str(tenant_b.id)},
        json={
            "code": "TECH",
            "name": "Technology Division",
            "unit_type": "DIVISION",
            "effective_from": "2026-01-01T00:00:00Z",
        },
    )

    assert parent_response.status_code == 201
    parent_id = parent_response.json()["id"]

    response = client.patch(
        f"/organization/units/{child_id}/parent",
        headers={"X-Tenant-ID": str(tenant_a.id)},
        json={
            "parent_id": parent_id,
        },
    )

    assert response.status_code == 404


def test_create_organization_unit_cannot_reference_cross_tenant_legal_entity(db):
    tenant_a = create_test_tenant(db)
    tenant_b = create_test_tenant(db)

    legal_entity_response = client.post(
        "/organization/legal-entities",
        headers={"X-Tenant-ID": str(tenant_b.id)},
        json={
            "tenant_id": str(tenant_b.id),
            "legal_name": "Tenant B Holdings Ltd",
            "registration_number": "REG-B-001",
            "tax_identifier": "TAX-B-001",
            "country_code": "KEN",
            "currency_code": "KES",
            "timezone": "Africa/Nairobi",
        },
    )

    assert legal_entity_response.status_code == 201
    legal_entity_id = legal_entity_response.json()["id"]

    response = client.post(
        "/organization/units",
        headers={"X-Tenant-ID": str(tenant_a.id)},
        json={
            "legal_entity_id": legal_entity_id,
            "code": "TECH",
            "name": "Technology Division",
            "unit_type": "DIVISION",
            "effective_from": "2026-01-01T00:00:00Z",
        },
    )

    assert response.status_code == 400
from datetime import date, datetime, timezone
from uuid import uuid4

from fastapi.testclient import TestClient

from app.core.database import Base
from app.main import app
from app.organization.enums import OrganizationUnitStatus, OrganizationUnitType
from app.organization.models import OrganizationUnit, Tenant

from tests.conftest import TestingSession


client = TestClient(app)


def create_tenant(db, legal_name="HR API Test Tenant"):
    tenant = Tenant(
        legal_name=legal_name,
        country_code="KE",
        timezone="Africa/Nairobi",
        currency_code="KES",
    )
    db.add(tenant)
    db.flush()
    return tenant


def create_organization_unit(db, tenant_id):
    unit = OrganizationUnit(
        tenant_id=tenant_id,
        code=f"HR-{uuid4().hex[:8]}",
        name="Technology",
        unit_type=OrganizationUnitType.DEPARTMENT,
        status=OrganizationUnitStatus.ACTIVE,
        effective_from=datetime(
            2026,
            1,
            1,
            tzinfo=timezone.utc,
        ),
    )
    db.add(unit)
    db.flush()
    return unit


def test_create_and_get_person(db):
    tenant = create_tenant(db)

    response = client.post(
        "/hr/persons",
        headers={"X-Tenant-ID": str(tenant.id)},
        json={
            "person_number": "P-1001",
            "first_name": "Peter",
            "last_name": "Mbuthia",
            "date_of_birth": "1995-01-15",
            "gender": "MALE",
            "nationality_code": "KE",
        },
    )

    assert response.status_code == 201

    data = response.json()

    assert data["tenant_id"] == str(tenant.id)
    assert data["person_number"] == "P-1001"
    assert data["first_name"] == "Peter"
    assert data["last_name"] == "Mbuthia"

    person_id = data["id"]

    response = client.get(
        f"/hr/persons/{person_id}",
        headers={"X-Tenant-ID": str(tenant.id)},
    )

    assert response.status_code == 200
    assert response.json()["id"] == person_id


def test_person_is_tenant_isolated(db):
    tenant_a = create_tenant(db, "Tenant A")
    tenant_b = create_tenant(db, "Tenant B")

    response = client.post(
        "/hr/persons",
        headers={"X-Tenant-ID": str(tenant_a.id)},
        json={
            "person_number": "P-2001",
            "first_name": "John",
            "last_name": "Doe",
        },
    )

    assert response.status_code == 201

    person_id = response.json()["id"]

    response = client.get(
        f"/hr/persons/{person_id}",
        headers={"X-Tenant-ID": str(tenant_b.id)},
    )

    assert response.status_code == 404


def test_create_employee(db):
    tenant = create_tenant(db)

    person_response = client.post(
        "/hr/persons",
        headers={"X-Tenant-ID": str(tenant.id)},
        json={
            "person_number": "P-3001",
            "first_name": "Jane",
            "last_name": "Doe",
        },
    )

    assert person_response.status_code == 201
    person_id = person_response.json()["id"]

    response = client.post(
        "/hr/employees",
        headers={"X-Tenant-ID": str(tenant.id)},
        json={
            "person_id": person_id,
            "employee_number": "EMP-3001",
            "employment_status": "ACTIVE",
            "employment_type": "PERMANENT",
            "hire_date": "2026-01-01",
        },
    )

    assert response.status_code == 201

    data = response.json()

    assert data["tenant_id"] == str(tenant.id)
    assert data["person_id"] == person_id
    assert data["employee_number"] == "EMP-3001"
    assert data["employment_status"] == "ACTIVE"


def test_create_employee_rejects_cross_tenant_person(db):
    tenant_a = create_tenant(db, "Tenant A")
    tenant_b = create_tenant(db, "Tenant B")

    person_response = client.post(
        "/hr/persons",
        headers={"X-Tenant-ID": str(tenant_a.id)},
        json={
            "person_number": "P-4001",
            "first_name": "Cross",
            "last_name": "Tenant",
        },
    )

    assert person_response.status_code == 201

    person_id = person_response.json()["id"]

    response = client.post(
        "/hr/employees",
        headers={"X-Tenant-ID": str(tenant_b.id)},
        json={
            "person_id": person_id,
            "employee_number": "EMP-4001",
            "employment_status": "ACTIVE",
            "employment_type": "PERMANENT",
            "hire_date": "2026-01-01",
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Person not found for this tenant."


def test_create_assignment_and_get_current(db):
    tenant = create_tenant(db)
    unit = create_organization_unit(db, tenant.id)

    person_response = client.post(
        "/hr/persons",
        headers={"X-Tenant-ID": str(tenant.id)},
        json={
            "person_number": "P-5001",
            "first_name": "Alice",
            "last_name": "Kamau",
        },
    )

    assert person_response.status_code == 201

    employee_response = client.post(
        "/hr/employees",
        headers={"X-Tenant-ID": str(tenant.id)},
        json={
            "person_id": person_response.json()["id"],
            "employee_number": "EMP-5001",
            "employment_status": "ACTIVE",
            "employment_type": "PERMANENT",
            "hire_date": "2026-01-01",
        },
    )

    assert employee_response.status_code == 201

    employee_id = employee_response.json()["id"]

    response = client.post(
        "/hr/employment-assignments",
        headers={"X-Tenant-ID": str(tenant.id)},
        json={
            "employee_id": employee_id,
            "organization_unit_id": str(unit.id),
            "job_title": "Software Engineer",
            "effective_from": "2026-01-01T00:00:00Z",
        },
    )

    assert response.status_code == 201

    assignment = response.json()

    assert assignment["employee_id"] == employee_id
    assert assignment["organization_unit_id"] == str(unit.id)
    assert assignment["job_title"] == "Software Engineer"

    response = client.get(
        f"/hr/employees/{employee_id}/assignment/current",
        headers={"X-Tenant-ID": str(tenant.id)},
    )

    assert response.status_code == 200

    current = response.json()

    assert current["id"] == assignment["id"]
    assert current["job_title"] == "Software Engineer"


def test_assignment_history_returns_effective_dated_history(db):
    tenant = create_tenant(db)
    unit = create_organization_unit(db, tenant.id)

    person_response = client.post(
        "/hr/persons",
        headers={"X-Tenant-ID": str(tenant.id)},
        json={
            "person_number": "P-6001",
            "first_name": "David",
            "last_name": "Otieno",
        },
    )

    employee_response = client.post(
        "/hr/employees",
        headers={"X-Tenant-ID": str(tenant.id)},
        json={
            "person_id": person_response.json()["id"],
            "employee_number": "EMP-6001",
            "employment_status": "ACTIVE",
            "employment_type": "PERMANENT",
            "hire_date": "2026-01-01",
        },
    )

    employee_id = employee_response.json()["id"]

    first = client.post(
        "/hr/employment-assignments",
        headers={"X-Tenant-ID": str(tenant.id)},
        json={
            "employee_id": employee_id,
            "organization_unit_id": str(unit.id),
            "job_title": "Junior Engineer",
            "effective_from": "2026-01-01T00:00:00Z",
            "effective_to": "2026-06-01T00:00:00Z",
        },
    )

    second = client.post(
        "/hr/employment-assignments",
        headers={"X-Tenant-ID": str(tenant.id)},
        json={
            "employee_id": employee_id,
            "organization_unit_id": str(unit.id),
            "job_title": "Senior Engineer",
            "effective_from": "2026-06-01T00:00:00Z",
        },
    )

    assert first.status_code == 201
    assert second.status_code == 201

    response = client.get(
        f"/hr/employees/{employee_id}/assignment/history",
        headers={"X-Tenant-ID": str(tenant.id)},
    )

    assert response.status_code == 200

    history = response.json()

    assert len(history) == 2
    assert history[0]["job_title"] == "Senior Engineer"
    assert history[1]["job_title"] == "Junior Engineer"


def test_missing_employee_returns_404(db):
    tenant = create_tenant(db)

    response = client.get(
        f"/hr/employees/{uuid4()}",
        headers={"X-Tenant-ID": str(tenant.id)},
    )

    assert response.status_code == 404


def test_invalid_employment_dates_return_400(db):
    tenant = create_tenant(db)

    person_response = client.post(
        "/hr/persons",
        headers={"X-Tenant-ID": str(tenant.id)},
        json={
            "person_number": "P-8001",
            "first_name": "Invalid",
            "last_name": "Dates",
        },
    )

    person_id = person_response.json()["id"]

    response = client.post(
        "/hr/employees",
        headers={"X-Tenant-ID": str(tenant.id)},
        json={
            "person_id": person_id,
            "employee_number": "EMP-8001",
            "employment_status": "TERMINATED",
            "employment_type": "PERMANENT",
            "hire_date": "2026-06-01",
            "termination_date": "2026-05-01",
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == (
      "termination_date must be on or after hire_date."
    )
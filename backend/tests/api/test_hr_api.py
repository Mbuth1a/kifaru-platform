from datetime import date, datetime, timezone
from uuid import uuid4
from sqlalchemy import text
from fastapi.testclient import TestClient
from tests.conftest import engine
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



def test_create_and_get_employment_term(db):
    tenant = create_tenant(db)

    person_response = client.post(
        "/hr/persons",
        headers={"X-Tenant-ID": str(tenant.id)},
        json={
            "person_number": "P-9001",
            "first_name": "Peter",
            "last_name": "Term",
        },
    )

    assert person_response.status_code == 201
    person_id = person_response.json()["id"]

    employee_response = client.post(
        "/hr/employees",
        headers={"X-Tenant-ID": str(tenant.id)},
        json={
            "person_id": person_id,
            "employee_number": "EMP-9001",
            "employment_status": "ACTIVE",
            "employment_type": "PERMANENT",
            "hire_date": "2026-01-01",
        },
    )

    assert employee_response.status_code == 201
    employee_id = employee_response.json()["id"]

    response = client.post(
        "/hr/employment-terms",
        headers={"X-Tenant-ID": str(tenant.id)},
        json={
            "employee_id": employee_id,
            "effective_from": "2026-01-01T00:00:00Z",
            "pay_frequency": "MONTHLY",
            "compensation_basis": "SALARY",
            "currency_code": "KES",
            "amount": "150000.00",
        },
    )

    assert response.status_code == 201

    data = response.json()

    assert data["tenant_id"] == str(tenant.id)
    assert data["employee_id"] == employee_id
    assert data["pay_frequency"] == "MONTHLY"
    assert data["compensation_basis"] == "SALARY"
    assert data["currency_code"] == "KES"
    assert data["amount"] == "150000.00"

    term_id = data["id"]

    response = client.get(
        f"/hr/employment-terms/{term_id}",
        headers={"X-Tenant-ID": str(tenant.id)},
    )

    assert response.status_code == 200

    retrieved = response.json()

    assert retrieved["id"] == term_id
    assert retrieved["employee_id"] == employee_id
    assert retrieved["amount"] == "150000.00"



def test_employment_term_current_and_history(db):
    tenant = create_tenant(db)

    person_response = client.post(
        "/hr/persons",
        headers={"X-Tenant-ID": str(tenant.id)},
        json={
            "person_number": "P-9101",
            "first_name": "Grace",
            "last_name": "Wanjiku",
        },
    )

    assert person_response.status_code == 201

    employee_response = client.post(
        "/hr/employees",
        headers={"X-Tenant-ID": str(tenant.id)},
        json={
            "person_id": person_response.json()["id"],
            "employee_number": "EMP-9101",
            "employment_status": "ACTIVE",
            "employment_type": "PERMANENT",
            "hire_date": "2026-01-01",
        },
    )

    assert employee_response.status_code == 201
    employee_id = employee_response.json()["id"]

    first = client.post(
        "/hr/employment-terms",
        headers={"X-Tenant-ID": str(tenant.id)},
        json={
            "employee_id": employee_id,
            "effective_from": "2026-01-01T00:00:00Z",
            "effective_to": "2026-07-01T00:00:00Z",
            "pay_frequency": "MONTHLY",
            "compensation_basis": "SALARY",
            "currency_code": "KES",
            "amount": "120000.00",
        },
    )

    second = client.post(
        "/hr/employment-terms",
        headers={"X-Tenant-ID": str(tenant.id)},
        json={
            "employee_id": employee_id,
            "effective_from": "2026-07-01T00:00:00Z",
            "pay_frequency": "MONTHLY",
            "compensation_basis": "SALARY",
            "currency_code": "KES",
            "amount": "150000.00",
        },
    )

    assert first.status_code == 201
    assert second.status_code == 201

    response = client.get(
        f"/hr/employees/{employee_id}/term/current",
        headers={"X-Tenant-ID": str(tenant.id)},
    )

    assert response.status_code == 200

    current = response.json()

    assert current["id"] == second.json()["id"]
    assert current["amount"] == "150000.00"

    response = client.get(
        f"/hr/employees/{employee_id}/term/history",
        headers={"X-Tenant-ID": str(tenant.id)},
    )

    assert response.status_code == 200

    history = response.json()

    assert len(history) == 2
    assert history[0]["amount"] == "150000.00"
    assert history[1]["amount"] == "120000.00"



def test_employment_term_is_tenant_isolated(db):
    tenant_a = create_tenant(db, "Tenant A")
    tenant_b = create_tenant(db, "Tenant B")

    person_response = client.post(
        "/hr/persons",
        headers={"X-Tenant-ID": str(tenant_a.id)},
        json={
            "person_number": "P-9201",
            "first_name": "Tenant",
            "last_name": "Employee",
        },
    )

    assert person_response.status_code == 201

    employee_response = client.post(
        "/hr/employees",
        headers={"X-Tenant-ID": str(tenant_a.id)},
        json={
            "person_id": person_response.json()["id"],
            "employee_number": "EMP-9201",
            "employment_status": "ACTIVE",
            "employment_type": "PERMANENT",
            "hire_date": "2026-01-01",
        },
    )

    assert employee_response.status_code == 201
    employee_id = employee_response.json()["id"]

    term_response = client.post(
        "/hr/employment-terms",
        headers={"X-Tenant-ID": str(tenant_a.id)},
        json={
            "employee_id": employee_id,
            "effective_from": "2026-01-01T00:00:00Z",
            "pay_frequency": "MONTHLY",
            "compensation_basis": "SALARY",
            "currency_code": "KES",
            "amount": "100000.00",
        },
    )

    assert term_response.status_code == 201
    term_id = term_response.json()["id"]

    response = client.get(
        f"/hr/employment-terms/{term_id}",
        headers={"X-Tenant-ID": str(tenant_b.id)},
    )

    assert response.status_code == 404

    response = client.get(
        f"/hr/employees/{employee_id}/term/current",
        headers={"X-Tenant-ID": str(tenant_b.id)},
    )

    assert response.status_code == 404

    response = client.get(
        f"/hr/employees/{employee_id}/term/history",
        headers={"X-Tenant-ID": str(tenant_b.id)},
    )

    assert response.status_code == 404


def test_invalid_employment_term_dates_return_400(db):
    tenant = create_tenant(db)

    person_response = client.post(
        "/hr/persons",
        headers={"X-Tenant-ID": str(tenant.id)},
        json={
            "person_number": "P-9301",
            "first_name": "Invalid",
            "last_name": "Term",
        },
    )

    assert person_response.status_code == 201

    employee_response = client.post(
        "/hr/employees",
        headers={"X-Tenant-ID": str(tenant.id)},
        json={
            "person_id": person_response.json()["id"],
            "employee_number": "EMP-9301",
            "employment_status": "ACTIVE",
            "employment_type": "PERMANENT",
            "hire_date": "2026-01-01",
        },
    )

    assert employee_response.status_code == 201
    employee_id = employee_response.json()["id"]

    response = client.post(
        "/hr/employment-terms",
        headers={"X-Tenant-ID": str(tenant.id)},
        json={
            "employee_id": employee_id,
            "effective_from": "2026-07-01T00:00:00Z",
            "effective_to": "2026-06-01T00:00:00Z",
            "pay_frequency": "MONTHLY",
            "compensation_basis": "SALARY",
            "currency_code": "KES",
            "amount": "150000.00",
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == (
        "effective_to must be later than effective_from."
    )




def test_employee_initial_status_history_is_created(db):
    tenant = create_tenant(db)

    person_response = client.post(
        "/hr/persons",
        headers={"X-Tenant-ID": str(tenant.id)},
        json={
            "person_number": "P-9401",
            "first_name": "Initial",
            "last_name": "Status",
        },
    )

    assert person_response.status_code == 201

    employee_response = client.post(
        "/hr/employees",
        headers={"X-Tenant-ID": str(tenant.id)},
        json={
            "person_id": person_response.json()["id"],
            "employee_number": "EMP-9401",
            "employment_status": "ACTIVE",
            "employment_type": "PERMANENT",
            "hire_date": "2026-01-01",
        },
    )

    assert employee_response.status_code == 201
    employee_id = employee_response.json()["id"]

    response = client.get(
        f"/hr/employees/{employee_id}/status/history",
        headers={"X-Tenant-ID": str(tenant.id)},
    )

    assert response.status_code == 200

    history = response.json()

    assert len(history) == 1
    assert history[0]["employee_id"] == employee_id
    assert history[0]["status"] == "ACTIVE"
    assert history[0]["effective_from"] == "2026-01-01T00:00:00Z"
    assert history[0]["effective_to"] is None
    assert history[0]["reason"] == "Initial employment status"


def test_employee_status_transition_succeeds(db):
    tenant = create_tenant(db)

    person_response = client.post(
        "/hr/persons",
        headers={"X-Tenant-ID": str(tenant.id)},
        json={
            "person_number": "P-9501",
            "first_name": "Status",
            "last_name": "Transition",
        },
    )

    assert person_response.status_code == 201

    employee_response = client.post(
        "/hr/employees",
        headers={"X-Tenant-ID": str(tenant.id)},
        json={
            "person_id": person_response.json()["id"],
            "employee_number": "EMP-9501",
            "employment_status": "ACTIVE",
            "employment_type": "PERMANENT",
            "hire_date": "2026-01-01",
        },
    )

    assert employee_response.status_code == 201

    employee_id = employee_response.json()["id"]

    response = client.post(
        f"/hr/employees/{employee_id}/status",
        headers={"X-Tenant-ID": str(tenant.id)},
        json={
            "status": "ON_LEAVE",
            "effective_from": "2026-06-01T00:00:00Z",
            "reason": "Approved leave",
        },
    )

    assert response.status_code == 201

    data = response.json()

    assert data["tenant_id"] == str(tenant.id)
    assert data["employee_id"] == employee_id
    assert data["status"] == "ON_LEAVE"
    assert data["effective_from"] == "2026-06-01T00:00:00Z"
    assert data["effective_to"] is None
    assert data["reason"] == "Approved leave"

    employee_response = client.get(
        f"/hr/employees/{employee_id}",
        headers={"X-Tenant-ID": str(tenant.id)},
    )

    assert employee_response.status_code == 200
    assert employee_response.json()["employment_status"] == "ON_LEAVE"


def test_employee_current_status_returns_current_period(db):
    tenant = create_tenant(db)

    person_response = client.post(
        "/hr/persons",
        headers={"X-Tenant-ID": str(tenant.id)},
        json={
            "person_number": "P-9601",
            "first_name": "Current",
            "last_name": "Status",
        },
    )

    employee_response = client.post(
        "/hr/employees",
        headers={"X-Tenant-ID": str(tenant.id)},
        json={
            "person_id": person_response.json()["id"],
            "employee_number": "EMP-9601",
            "employment_status": "ACTIVE",
            "employment_type": "PERMANENT",
            "hire_date": "2026-01-01",
        },
    )

    assert employee_response.status_code == 201

    employee_id = employee_response.json()["id"]

    transition_response = client.post(
        f"/hr/employees/{employee_id}/status",
        headers={"X-Tenant-ID": str(tenant.id)},
        json={
            "status": "ON_LEAVE",
            "effective_from": "2026-06-01T00:00:00Z",
            "reason": "Annual leave",
        },
    )

    assert transition_response.status_code == 201

    response = client.get(
        f"/hr/employees/{employee_id}/status/current",
        headers={"X-Tenant-ID": str(tenant.id)},
    )

    assert response.status_code == 200

    current = response.json()

    assert current["employee_id"] == employee_id
    assert current["status"] == "ON_LEAVE"
    assert current["effective_from"] == "2026-06-01T00:00:00Z"
    assert current["effective_to"] is None


def test_employee_status_history_returns_effective_dated_history(db):
    tenant = create_tenant(db)

    person_response = client.post(
        "/hr/persons",
        headers={"X-Tenant-ID": str(tenant.id)},
        json={
            "person_number": "P-9701",
            "first_name": "Status",
            "last_name": "History",
        },
    )

    employee_response = client.post(
        "/hr/employees",
        headers={"X-Tenant-ID": str(tenant.id)},
        json={
            "person_id": person_response.json()["id"],
            "employee_number": "EMP-9701",
            "employment_status": "ACTIVE",
            "employment_type": "PERMANENT",
            "hire_date": "2026-01-01",
        },
    )

    assert employee_response.status_code == 201

    employee_id = employee_response.json()["id"]

    first_transition = client.post(
        f"/hr/employees/{employee_id}/status",
        headers={"X-Tenant-ID": str(tenant.id)},
        json={
            "status": "ON_LEAVE",
            "effective_from": "2026-04-01T00:00:00Z",
            "reason": "Leave",
        },
    )

    second_transition = client.post(
        f"/hr/employees/{employee_id}/status",
        headers={"X-Tenant-ID": str(tenant.id)},
        json={
            "status": "SUSPENDED",
            "effective_from": "2026-07-01T00:00:00Z",
            "reason": "Administrative suspension",
        },
    )

    assert first_transition.status_code == 201
    assert second_transition.status_code == 201

    response = client.get(
        f"/hr/employees/{employee_id}/status/history",
        headers={"X-Tenant-ID": str(tenant.id)},
    )

    assert response.status_code == 200

    history = response.json()

    assert len(history) == 3

    assert history[0]["status"] == "SUSPENDED"
    assert history[0]["effective_from"] == "2026-07-01T00:00:00Z"
    assert history[0]["effective_to"] is None

    assert history[1]["status"] == "ON_LEAVE"
    assert history[1]["effective_from"] == "2026-04-01T00:00:00Z"
    assert history[1]["effective_to"] == "2026-07-01T00:00:00Z"

    assert history[2]["status"] == "ACTIVE"
    assert history[2]["effective_from"] == "2026-01-01T00:00:00Z"
    assert history[2]["effective_to"] == "2026-04-01T00:00:00Z"


def test_employee_status_transition_rejects_future_effective_date(db):
    tenant = create_tenant(db)

    person_response = client.post(
        "/hr/persons",
        headers={"X-Tenant-ID": str(tenant.id)},
        json={
            "person_number": "P-9801",
            "first_name": "Future",
            "last_name": "Status",
        },
    )

    employee_response = client.post(
        "/hr/employees",
        headers={"X-Tenant-ID": str(tenant.id)},
        json={
            "person_id": person_response.json()["id"],
            "employee_number": "EMP-9801",
            "employment_status": "ACTIVE",
            "employment_type": "PERMANENT",
            "hire_date": "2026-01-01",
        },
    )

    assert employee_response.status_code == 201

    employee_id = employee_response.json()["id"]

    response = client.post(
        f"/hr/employees/{employee_id}/status",
        headers={"X-Tenant-ID": str(tenant.id)},
        json={
            "status": "ON_LEAVE",
            "effective_from": "2030-01-01T00:00:00Z",
            "reason": "Future leave",
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == (
        "effective_from cannot be in the future."
    )


def test_employee_status_transition_rejects_same_status(db):
    tenant = create_tenant(db)

    person_response = client.post(
        "/hr/persons",
        headers={"X-Tenant-ID": str(tenant.id)},
        json={
            "person_number": "P-9901",
            "first_name": "Same",
            "last_name": "Status",
        },
    )

    employee_response = client.post(
        "/hr/employees",
        headers={"X-Tenant-ID": str(tenant.id)},
        json={
            "person_id": person_response.json()["id"],
            "employee_number": "EMP-9901",
            "employment_status": "ACTIVE",
            "employment_type": "PERMANENT",
            "hire_date": "2026-01-01",
        },
    )

    assert employee_response.status_code == 201

    employee_id = employee_response.json()["id"]

    response = client.post(
        f"/hr/employees/{employee_id}/status",
        headers={"X-Tenant-ID": str(tenant.id)},
        json={
            "status": "ACTIVE",
            "effective_from": "2026-06-01T00:00:00Z",
            "reason": "Duplicate status",
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == (
        "Employee already has this employment status."
    )


def test_employee_status_endpoints_are_tenant_isolated(db):
    tenant_a = create_tenant(db, "Status Tenant A")
    tenant_b = create_tenant(db, "Status Tenant B")

    person_response = client.post(
        "/hr/persons",
        headers={"X-Tenant-ID": str(tenant_a.id)},
        json={
            "person_number": "P-9910",
            "first_name": "Tenant",
            "last_name": "Status",
        },
    )

    assert person_response.status_code == 201

    employee_response = client.post(
        "/hr/employees",
        headers={"X-Tenant-ID": str(tenant_a.id)},
        json={
            "person_id": person_response.json()["id"],
            "employee_number": "EMP-9910",
            "employment_status": "ACTIVE",
            "employment_type": "PERMANENT",
            "hire_date": "2026-01-01",
        },
    )

    assert employee_response.status_code == 201

    employee_id = employee_response.json()["id"]

    response = client.post(
        f"/hr/employees/{employee_id}/status",
        headers={"X-Tenant-ID": str(tenant_b.id)},
        json={
            "status": "ON_LEAVE",
            "effective_from": "2026-06-01T00:00:00Z",
            "reason": "Cross-tenant attempt",
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == (
        "Employee not found for this tenant."
    )

    response = client.get(
        f"/hr/employees/{employee_id}/status/current",
        headers={"X-Tenant-ID": str(tenant_b.id)},
    )

    assert response.status_code == 404

    response = client.get(
        f"/hr/employees/{employee_id}/status/history",
        headers={"X-Tenant-ID": str(tenant_b.id)},
    )

    assert response.status_code == 404




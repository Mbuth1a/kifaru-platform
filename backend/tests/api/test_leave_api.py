from fastapi.testclient import TestClient

from app.main import app
from datetime import date
from uuid import uuid4

from app.hr.enums import EmploymentStatus, EmploymentType
from app.hr.models import Employee, Person
from app.leave.models import LeaveType
from app.organization.models import Tenant

client = TestClient(app)


def test_create_leave_type(db):
    from app.organization.models import Tenant

    tenant = Tenant(
        legal_name="Leave API Test Tenant",
        country_code="KE",
        timezone="Africa/Nairobi",
        currency_code="KES",
    )

    db.add(tenant)
    db.flush()

    response = client.post(
        "/leave/types",
        headers={"X-Tenant-ID": str(tenant.id)},
        json={
            "code": "ANNUAL",
            "name": "Annual Leave",
            "description": "Annual employee leave",
            "active": True,
        },
    )

    assert response.status_code == 201

    data = response.json()

    assert data["tenant_id"] == str(tenant.id)
    assert data["code"] == "ANNUAL"
    assert data["name"] == "Annual Leave"
    assert data["description"] == "Annual employee leave"
    assert data["active"] is True



def test_create_leave_request(db):
    tenant = Tenant(
        legal_name="Leave Request API Test Tenant",
        country_code="KE",
        timezone="Africa/Nairobi",
        currency_code="KES",
    )
    db.add(tenant)
    db.flush()

    person = Person(
        tenant_id=tenant.id,
        person_number=f"P-{uuid4().hex[:8]}",
        first_name="API",
        last_name="Employee",
    )
    db.add(person)
    db.flush()

    employee = Employee(
        tenant_id=tenant.id,
        person_id=person.id,
        employee_number=f"E-{uuid4().hex[:8]}",
        employment_status=EmploymentStatus.ACTIVE,
        employment_type=EmploymentType.PERMANENT,
        hire_date=date(2025, 1, 1),
    )
    db.add(employee)
    db.flush()

    leave_type = LeaveType(
        tenant_id=tenant.id,
        code="ANNUAL",
        name="Annual Leave",
        active=True,
    )
    db.add(leave_type)
    db.flush()

    response = client.post(
        "/leave/requests",
        headers={"X-Tenant-ID": str(tenant.id)},
        json={
            "employee_id": str(employee.id),
            "leave_type_id": str(leave_type.id),
            "start_date": "2026-10-12",
            "end_date": "2026-10-14",
            "reason": "Annual leave",
        },
    )

    assert response.status_code == 201

    data = response.json()

    assert data["tenant_id"] == str(tenant.id)
    assert data["employee_id"] == str(employee.id)
    assert data["leave_type_id"] == str(leave_type.id)
    assert data["start_date"] == "2026-10-12"
    assert data["end_date"] == "2026-10-14"
    assert data["requested_days"] == 3
    assert data["reason"] == "Annual leave"
    assert data["status"] == "PENDING"




def test_approve_leave_request(db):
    tenant = Tenant(
        legal_name="Leave Approval API Test Tenant",
        country_code="KE",
        timezone="Africa/Nairobi",
        currency_code="KES",
    )
    db.add(tenant)
    db.flush()

    person = Person(
        tenant_id=tenant.id,
        person_number=f"P-{uuid4().hex[:8]}",
        first_name="Approval",
        last_name="Employee",
    )
    db.add(person)
    db.flush()

    employee = Employee(
        tenant_id=tenant.id,
        person_id=person.id,
        employee_number=f"E-{uuid4().hex[:8]}",
        employment_status=EmploymentStatus.ACTIVE,
        employment_type=EmploymentType.PERMANENT,
        hire_date=date(2025, 1, 1),
    )
    db.add(employee)
    db.flush()

    leave_type = LeaveType(
        tenant_id=tenant.id,
        code="ANNUAL",
        name="Annual Leave",
        active=True,
    )
    db.add(leave_type)
    db.flush()

    create_response = client.post(
        "/leave/requests",
        headers={"X-Tenant-ID": str(tenant.id)},
        json={
            "employee_id": str(employee.id),
            "leave_type_id": str(leave_type.id),
            "start_date": "2026-11-02",
            "end_date": "2026-11-04",
            "reason": "Annual leave",
        },
    )

    assert create_response.status_code == 201

    leave_request_id = create_response.json()["id"]

    response = client.post(
        f"/leave/requests/{leave_request_id}/status",
        headers={"X-Tenant-ID": str(tenant.id)},
        json={
            "status": "APPROVED",
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["id"] == leave_request_id
    assert data["status"] == "APPROVED"


def test_get_leave_type_is_tenant_scoped(db):
    tenant_a = Tenant(
        legal_name="Leave Type Tenant A",
        country_code="KE",
        timezone="Africa/Nairobi",
        currency_code="KES",
    )
    tenant_b = Tenant(
        legal_name="Leave Type Tenant B",
        country_code="KE",
        timezone="Africa/Nairobi",
        currency_code="KES",
    )

    db.add_all([tenant_a, tenant_b])
    db.flush()

    leave_type = LeaveType(
        tenant_id=tenant_a.id,
        code="ANNUAL",
        name="Annual Leave",
        active=True,
    )
    db.add(leave_type)
    db.flush()

    response = client.get(
        f"/leave/types/{leave_type.id}",
        headers={"X-Tenant-ID": str(tenant_a.id)},
    )

    assert response.status_code == 200
    assert response.json()["id"] == str(leave_type.id)
    assert response.json()["tenant_id"] == str(tenant_a.id)

    cross_tenant_response = client.get(
        f"/leave/types/{leave_type.id}",
        headers={"X-Tenant-ID": str(tenant_b.id)},
    )

    assert cross_tenant_response.status_code == 404



def test_get_leave_request_is_tenant_scoped(db):
    tenant_a = Tenant(
        legal_name="Leave Request Tenant A",
        country_code="KE",
        timezone="Africa/Nairobi",
        currency_code="KES",
    )
    tenant_b = Tenant(
        legal_name="Leave Request Tenant B",
        country_code="KE",
        timezone="Africa/Nairobi",
        currency_code="KES",
    )
    db.add_all([tenant_a, tenant_b])
    db.flush()

    person = Person(
        tenant_id=tenant_a.id,
        person_number=f"P-{uuid4().hex[:8]}",
        first_name="Request",
        last_name="Employee",
    )
    db.add(person)
    db.flush()

    employee = Employee(
        tenant_id=tenant_a.id,
        person_id=person.id,
        employee_number=f"E-{uuid4().hex[:8]}",
        employment_status=EmploymentStatus.ACTIVE,
        employment_type=EmploymentType.PERMANENT,
        hire_date=date(2025, 1, 1),
    )
    db.add(employee)
    db.flush()

    leave_type = LeaveType(
        tenant_id=tenant_a.id,
        code="ANNUAL",
        name="Annual Leave",
        active=True,
    )
    db.add(leave_type)
    db.flush()

    create_response = client.post(
        "/leave/requests",
        headers={"X-Tenant-ID": str(tenant_a.id)},
        json={
            "employee_id": str(employee.id),
            "leave_type_id": str(leave_type.id),
            "start_date": "2026-12-01",
            "end_date": "2026-12-03",
            "reason": "Annual leave",
        },
    )

    assert create_response.status_code == 201

    leave_request_id = create_response.json()["id"]

    response = client.get(
        f"/leave/requests/{leave_request_id}",
        headers={"X-Tenant-ID": str(tenant_a.id)},
    )

    assert response.status_code == 200

    data = response.json()

    assert data["id"] == leave_request_id
    assert data["tenant_id"] == str(tenant_a.id)
    assert data["employee_id"] == str(employee.id)
    assert data["status"] == "PENDING"

    cross_tenant_response = client.get(
        f"/leave/requests/{leave_request_id}",
        headers={"X-Tenant-ID": str(tenant_b.id)},
    )

    assert cross_tenant_response.status_code == 404


def test_create_leave_request_rejects_invalid_date_range(db):
    tenant = Tenant(
        legal_name="Invalid Date API Test Tenant",
        country_code="KE",
        timezone="Africa/Nairobi",
        currency_code="KES",
    )
    db.add(tenant)
    db.flush()

    person = Person(
        tenant_id=tenant.id,
        person_number=f"P-{uuid4().hex[:8]}",
        first_name="Invalid",
        last_name="Date",
    )
    db.add(person)
    db.flush()

    employee = Employee(
        tenant_id=tenant.id,
        person_id=person.id,
        employee_number=f"E-{uuid4().hex[:8]}",
        employment_status=EmploymentStatus.ACTIVE,
        employment_type=EmploymentType.PERMANENT,
        hire_date=date(2025, 1, 1),
    )
    db.add(employee)
    db.flush()

    leave_type = LeaveType(
        tenant_id=tenant.id,
        code="ANNUAL",
        name="Annual Leave",
        active=True,
    )
    db.add(leave_type)
    db.flush()

    response = client.post(
        "/leave/requests",
        headers={"X-Tenant-ID": str(tenant.id)},
        json={
            "employee_id": str(employee.id),
            "leave_type_id": str(leave_type.id),
            "start_date": "2026-12-10",
            "end_date": "2026-12-05",
            "reason": "Invalid date range",
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == (
        "end_date must be on or after start_date."
    )




def test_create_leave_request_rejects_terminated_employee(db):
    tenant = Tenant(
        legal_name="Terminated Employee API Test Tenant",
        country_code="KE",
        timezone="Africa/Nairobi",
        currency_code="KES",
    )
    db.add(tenant)
    db.flush()

    person = Person(
        tenant_id=tenant.id,
        person_number=f"P-{uuid4().hex[:8]}",
        first_name="Terminated",
        last_name="Employee",
    )
    db.add(person)
    db.flush()

    employee = Employee(
        tenant_id=tenant.id,
        person_id=person.id,
        employee_number=f"E-{uuid4().hex[:8]}",
        employment_status=EmploymentStatus.TERMINATED,
        employment_type=EmploymentType.PERMANENT,
        hire_date=date(2025, 1, 1),
        termination_date=date(2026, 9, 30),
        termination_reason="Employment ended",
    )
    db.add(employee)
    db.flush()

    leave_type = LeaveType(
        tenant_id=tenant.id,
        code="ANNUAL",
        name="Annual Leave",
        active=True,
    )
    db.add(leave_type)
    db.flush()

    response = client.post(
        "/leave/requests",
        headers={"X-Tenant-ID": str(tenant.id)},
        json={
            "employee_id": str(employee.id),
            "leave_type_id": str(leave_type.id),
            "start_date": "2026-10-12",
            "end_date": "2026-10-14",
            "reason": "Annual leave",
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == (
        "Terminated employees cannot create new leave requests."
    )


def test_create_leave_request_rejects_overlapping_pending_request(db):
    tenant = Tenant(
        legal_name="Overlap API Test Tenant",
        country_code="KE",
        timezone="Africa/Nairobi",
        currency_code="KES",
    )
    db.add(tenant)
    db.flush()

    person = Person(
        tenant_id=tenant.id,
        person_number=f"P-{uuid4().hex[:8]}",
        first_name="Overlap",
        last_name="Employee",
    )
    db.add(person)
    db.flush()

    employee = Employee(
        tenant_id=tenant.id,
        person_id=person.id,
        employee_number=f"E-{uuid4().hex[:8]}",
        employment_status=EmploymentStatus.ACTIVE,
        employment_type=EmploymentType.PERMANENT,
        hire_date=date(2025, 1, 1),
    )
    db.add(employee)
    db.flush()

    leave_type = LeaveType(
        tenant_id=tenant.id,
        code="ANNUAL",
        name="Annual Leave",
        active=True,
    )
    db.add(leave_type)
    db.flush()

    first_response = client.post(
        "/leave/requests",
        headers={"X-Tenant-ID": str(tenant.id)},
        json={
            "employee_id": str(employee.id),
            "leave_type_id": str(leave_type.id),
            "start_date": "2026-12-10",
            "end_date": "2026-12-12",
            "reason": "First leave request",
        },
    )

    assert first_response.status_code == 201

    second_response = client.post(
        "/leave/requests",
        headers={"X-Tenant-ID": str(tenant.id)},
        json={
            "employee_id": str(employee.id),
            "leave_type_id": str(leave_type.id),
            "start_date": "2026-12-12",
            "end_date": "2026-12-15",
            "reason": "Overlapping leave request",
        },
    )

    assert second_response.status_code == 400
    assert second_response.json()["detail"] == (
        "Leave request overlaps an existing pending or approved leave request."
    )


def test_create_leave_request_rejects_overlapping_approved_request(db):
    tenant = Tenant(
        legal_name="Approved Overlap API Test Tenant",
        country_code="KE",
        timezone="Africa/Nairobi",
        currency_code="KES",
    )
    db.add(tenant)
    db.flush()

    person = Person(
        tenant_id=tenant.id,
        person_number=f"P-{uuid4().hex[:8]}",
        first_name="Approved",
        last_name="Overlap",
    )
    db.add(person)
    db.flush()

    employee = Employee(
        tenant_id=tenant.id,
        person_id=person.id,
        employee_number=f"E-{uuid4().hex[:8]}",
        employment_status=EmploymentStatus.ACTIVE,
        employment_type=EmploymentType.PERMANENT,
        hire_date=date(2025, 1, 1),
    )
    db.add(employee)
    db.flush()

    leave_type = LeaveType(
        tenant_id=tenant.id,
        code="ANNUAL",
        name="Annual Leave",
        active=True,
    )
    db.add(leave_type)
    db.flush()

    first_response = client.post(
        "/leave/requests",
        headers={"X-Tenant-ID": str(tenant.id)},
        json={
            "employee_id": str(employee.id),
            "leave_type_id": str(leave_type.id),
            "start_date": "2027-01-10",
            "end_date": "2027-01-12",
            "reason": "Approved leave",
        },
    )

    assert first_response.status_code == 201

    leave_request_id = first_response.json()["id"]

    approval_response = client.post(
        f"/leave/requests/{leave_request_id}/status",
        headers={"X-Tenant-ID": str(tenant.id)},
        json={"status": "APPROVED"},
    )

    assert approval_response.status_code == 200
    assert approval_response.json()["status"] == "APPROVED"

    second_response = client.post(
        "/leave/requests",
        headers={"X-Tenant-ID": str(tenant.id)},
        json={
            "employee_id": str(employee.id),
            "leave_type_id": str(leave_type.id),
            "start_date": "2027-01-12",
            "end_date": "2027-01-15",
            "reason": "Overlapping approved leave",
        },
    )

    assert second_response.status_code == 400
    assert second_response.json()["detail"] == (
        "Leave request overlaps an existing pending or approved leave request."
    )


def test_create_leave_request_allows_overlap_with_rejected_request(db):
    tenant = Tenant(
        legal_name="Rejected Overlap API Test Tenant",
        country_code="KE",
        timezone="Africa/Nairobi",
        currency_code="KES",
    )
    db.add(tenant)
    db.flush()

    person = Person(
        tenant_id=tenant.id,
        person_number=f"P-{uuid4().hex[:8]}",
        first_name="Rejected",
        last_name="Overlap",
    )
    db.add(person)
    db.flush()

    employee = Employee(
        tenant_id=tenant.id,
        person_id=person.id,
        employee_number=f"E-{uuid4().hex[:8]}",
        employment_status=EmploymentStatus.ACTIVE,
        employment_type=EmploymentType.PERMANENT,
        hire_date=date(2025, 1, 1),
    )
    db.add(employee)
    db.flush()

    leave_type = LeaveType(
        tenant_id=tenant.id,
        code="ANNUAL",
        name="Annual Leave",
        active=True,
    )
    db.add(leave_type)
    db.flush()

    first_response = client.post(
        "/leave/requests",
        headers={"X-Tenant-ID": str(tenant.id)},
        json={
            "employee_id": str(employee.id),
            "leave_type_id": str(leave_type.id),
            "start_date": "2027-02-10",
            "end_date": "2027-02-12",
            "reason": "Rejected leave",
        },
    )

    assert first_response.status_code == 201

    leave_request_id = first_response.json()["id"]

    rejection_response = client.post(
        f"/leave/requests/{leave_request_id}/status",
        headers={"X-Tenant-ID": str(tenant.id)},
        json={"status": "REJECTED"},
    )

    assert rejection_response.status_code == 200
    assert rejection_response.json()["status"] == "REJECTED"

    second_response = client.post(
        "/leave/requests",
        headers={"X-Tenant-ID": str(tenant.id)},
        json={
            "employee_id": str(employee.id),
            "leave_type_id": str(leave_type.id),
            "start_date": "2027-02-12",
            "end_date": "2027-02-15",
            "reason": "New leave after rejection",
        },
    )

    assert second_response.status_code == 201
    assert second_response.json()["status"] == "PENDING"



def test_create_leave_request_allows_overlap_with_cancelled_request(db):
    tenant = Tenant(
        legal_name="Cancelled Overlap API Test Tenant",
        country_code="KE",
        timezone="Africa/Nairobi",
        currency_code="KES",
    )
    db.add(tenant)
    db.flush()

    person = Person(
        tenant_id=tenant.id,
        person_number=f"P-{uuid4().hex[:8]}",
        first_name="Cancelled",
        last_name="Overlap",
    )
    db.add(person)
    db.flush()

    employee = Employee(
        tenant_id=tenant.id,
        person_id=person.id,
        employee_number=f"E-{uuid4().hex[:8]}",
        employment_status=EmploymentStatus.ACTIVE,
        employment_type=EmploymentType.PERMANENT,
        hire_date=date(2025, 1, 1),
    )
    db.add(employee)
    db.flush()

    leave_type = LeaveType(
        tenant_id=tenant.id,
        code="ANNUAL",
        name="Annual Leave",
        active=True,
    )
    db.add(leave_type)
    db.flush()

    first_response = client.post(
        "/leave/requests",
        headers={"X-Tenant-ID": str(tenant.id)},
        json={
            "employee_id": str(employee.id),
            "leave_type_id": str(leave_type.id),
            "start_date": "2027-03-10",
            "end_date": "2027-03-12",
            "reason": "Cancelled leave",
        },
    )

    assert first_response.status_code == 201

    leave_request_id = first_response.json()["id"]

    cancellation_response = client.post(
        f"/leave/requests/{leave_request_id}/status",
        headers={"X-Tenant-ID": str(tenant.id)},
        json={"status": "CANCELLED"},
    )

    assert cancellation_response.status_code == 200
    assert cancellation_response.json()["status"] == "CANCELLED"

    second_response = client.post(
        "/leave/requests",
        headers={"X-Tenant-ID": str(tenant.id)},
        json={
            "employee_id": str(employee.id),
            "leave_type_id": str(leave_type.id),
            "start_date": "2027-03-12",
            "end_date": "2027-03-15",
            "reason": "New leave after cancellation",
        },
    )

    assert second_response.status_code == 201
    assert second_response.json()["status"] == "PENDING"


def test_rejected_leave_request_cannot_be_approved(db):
    tenant = Tenant(
        legal_name="Invalid Transition API Test Tenant",
        country_code="KE",
        timezone="Africa/Nairobi",
        currency_code="KES",
    )
    db.add(tenant)
    db.flush()

    person = Person(
        tenant_id=tenant.id,
        person_number=f"P-{uuid4().hex[:8]}",
        first_name="Invalid",
        last_name="Transition",
    )
    db.add(person)
    db.flush()

    employee = Employee(
        tenant_id=tenant.id,
        person_id=person.id,
        employee_number=f"E-{uuid4().hex[:8]}",
        employment_status=EmploymentStatus.ACTIVE,
        employment_type=EmploymentType.PERMANENT,
        hire_date=date(2025, 1, 1),
    )
    db.add(employee)
    db.flush()

    leave_type = LeaveType(
        tenant_id=tenant.id,
        code="ANNUAL",
        name="Annual Leave",
        active=True,
    )
    db.add(leave_type)
    db.flush()

    create_response = client.post(
        "/leave/requests",
        headers={"X-Tenant-ID": str(tenant.id)},
        json={
            "employee_id": str(employee.id),
            "leave_type_id": str(leave_type.id),
            "start_date": "2027-04-10",
            "end_date": "2027-04-12",
            "reason": "Invalid transition test",
        },
    )

    assert create_response.status_code == 201

    leave_request_id = create_response.json()["id"]

    reject_response = client.post(
        f"/leave/requests/{leave_request_id}/status",
        headers={"X-Tenant-ID": str(tenant.id)},
        json={"status": "REJECTED"},
    )

    assert reject_response.status_code == 200
    assert reject_response.json()["status"] == "REJECTED"

    approve_response = client.post(
        f"/leave/requests/{leave_request_id}/status",
        headers={"X-Tenant-ID": str(tenant.id)},
        json={"status": "APPROVED"},
    )

    assert approve_response.status_code == 400
    assert approve_response.json()["detail"] == (
        "Invalid leave request status transition: REJECTED -> APPROVED."
    )


def test_approved_leave_request_can_be_cancelled(db):
    tenant = Tenant(
        legal_name="Approved Cancellation API Test Tenant",
        country_code="KE",
        timezone="Africa/Nairobi",
        currency_code="KES",
    )
    db.add(tenant)
    db.flush()

    person = Person(
        tenant_id=tenant.id,
        person_number=f"P-{uuid4().hex[:8]}",
        first_name="Approved",
        last_name="Cancellation",
    )
    db.add(person)
    db.flush()

    employee = Employee(
        tenant_id=tenant.id,
        person_id=person.id,
        employee_number=f"E-{uuid4().hex[:8]}",
        employment_status=EmploymentStatus.ACTIVE,
        employment_type=EmploymentType.PERMANENT,
        hire_date=date(2025, 1, 1),
    )
    db.add(employee)
    db.flush()

    leave_type = LeaveType(
        tenant_id=tenant.id,
        code="ANNUAL",
        name="Annual Leave",
        active=True,
    )
    db.add(leave_type)
    db.flush()

    create_response = client.post(
        "/leave/requests",
        headers={"X-Tenant-ID": str(tenant.id)},
        json={
            "employee_id": str(employee.id),
            "leave_type_id": str(leave_type.id),
            "start_date": "2027-05-10",
            "end_date": "2027-05-12",
            "reason": "Approved cancellation test",
        },
    )

    assert create_response.status_code == 201

    leave_request_id = create_response.json()["id"]

    approve_response = client.post(
        f"/leave/requests/{leave_request_id}/status",
        headers={"X-Tenant-ID": str(tenant.id)},
        json={"status": "APPROVED"},
    )

    assert approve_response.status_code == 200
    assert approve_response.json()["status"] == "APPROVED"

    cancel_response = client.post(
        f"/leave/requests/{leave_request_id}/status",
        headers={"X-Tenant-ID": str(tenant.id)},
        json={"status": "CANCELLED"},
    )

    assert cancel_response.status_code == 200
    assert cancel_response.json()["status"] == "CANCELLED"



def test_pending_leave_request_can_be_cancelled(db):
    tenant = Tenant(
        legal_name="Pending Cancellation API Test Tenant",
        country_code="KE",
        timezone="Africa/Nairobi",
        currency_code="KES",
    )
    db.add(tenant)
    db.flush()

    person = Person(
        tenant_id=tenant.id,
        person_number=f"P-{uuid4().hex[:8]}",
        first_name="Pending",
        last_name="Cancellation",
    )
    db.add(person)
    db.flush()

    employee = Employee(
        tenant_id=tenant.id,
        person_id=person.id,
        employee_number=f"E-{uuid4().hex[:8]}",
        employment_status=EmploymentStatus.ACTIVE,
        employment_type=EmploymentType.PERMANENT,
        hire_date=date(2025, 1, 1),
    )
    db.add(employee)
    db.flush()

    leave_type = LeaveType(
        tenant_id=tenant.id,
        code="ANNUAL",
        name="Annual Leave",
        active=True,
    )
    db.add(leave_type)
    db.flush()

    create_response = client.post(
        "/leave/requests",
        headers={"X-Tenant-ID": str(tenant.id)},
        json={
            "employee_id": str(employee.id),
            "leave_type_id": str(leave_type.id),
            "start_date": "2027-06-10",
            "end_date": "2027-06-12",
            "reason": "Pending cancellation test",
        },
    )

    assert create_response.status_code == 201
    assert create_response.json()["status"] == "PENDING"

    leave_request_id = create_response.json()["id"]

    cancel_response = client.post(
        f"/leave/requests/{leave_request_id}/status",
        headers={"X-Tenant-ID": str(tenant.id)},
        json={"status": "CANCELLED"},
    )

    assert cancel_response.status_code == 200
    assert cancel_response.json()["status"] == "CANCELLED"



def test_cancelled_leave_request_cannot_be_approved(db):
    tenant = Tenant(
        legal_name="Cancelled Terminal API Test Tenant",
        country_code="KE",
        timezone="Africa/Nairobi",
        currency_code="KES",
    )
    db.add(tenant)
    db.flush()

    person = Person(
        tenant_id=tenant.id,
        person_number=f"P-{uuid4().hex[:8]}",
        first_name="Cancelled",
        last_name="Terminal",
    )
    db.add(person)
    db.flush()

    employee = Employee(
        tenant_id=tenant.id,
        person_id=person.id,
        employee_number=f"E-{uuid4().hex[:8]}",
        employment_status=EmploymentStatus.ACTIVE,
        employment_type=EmploymentType.PERMANENT,
        hire_date=date(2025, 1, 1),
    )
    db.add(employee)
    db.flush()

    leave_type = LeaveType(
        tenant_id=tenant.id,
        code="ANNUAL",
        name="Annual Leave",
        active=True,
    )
    db.add(leave_type)
    db.flush()

    create_response = client.post(
        "/leave/requests",
        headers={"X-Tenant-ID": str(tenant.id)},
        json={
            "employee_id": str(employee.id),
            "leave_type_id": str(leave_type.id),
            "start_date": "2027-07-10",
            "end_date": "2027-07-12",
            "reason": "Cancelled terminal test",
        },
    )

    assert create_response.status_code == 201

    leave_request_id = create_response.json()["id"]

    cancel_response = client.post(
        f"/leave/requests/{leave_request_id}/status",
        headers={"X-Tenant-ID": str(tenant.id)},
        json={"status": "CANCELLED"},
    )

    assert cancel_response.status_code == 200
    assert cancel_response.json()["status"] == "CANCELLED"

    approve_response = client.post(
        f"/leave/requests/{leave_request_id}/status",
        headers={"X-Tenant-ID": str(tenant.id)},
        json={"status": "APPROVED"},
    )

    assert approve_response.status_code == 400
    assert approve_response.json()["detail"] == (
        "Invalid leave request status transition: CANCELLED -> APPROVED."
    )




def test_rejected_leave_request_cannot_be_cancelled(db):
    tenant = Tenant(
        legal_name="Rejected Terminal API Test Tenant",
        country_code="KE",
        timezone="Africa/Nairobi",
        currency_code="KES",
    )
    db.add(tenant)
    db.flush()

    person = Person(
        tenant_id=tenant.id,
        person_number=f"P-{uuid4().hex[:8]}",
        first_name="Rejected",
        last_name="Terminal",
    )
    db.add(person)
    db.flush()

    employee = Employee(
        tenant_id=tenant.id,
        person_id=person.id,
        employee_number=f"E-{uuid4().hex[:8]}",
        employment_status=EmploymentStatus.ACTIVE,
        employment_type=EmploymentType.PERMANENT,
        hire_date=date(2025, 1, 1),
    )
    db.add(employee)
    db.flush()

    leave_type = LeaveType(
        tenant_id=tenant.id,
        code="ANNUAL",
        name="Annual Leave",
        active=True,
    )
    db.add(leave_type)
    db.flush()

    create_response = client.post(
        "/leave/requests",
        headers={"X-Tenant-ID": str(tenant.id)},
        json={
            "employee_id": str(employee.id),
            "leave_type_id": str(leave_type.id),
            "start_date": "2027-08-10",
            "end_date": "2027-08-12",
            "reason": "Rejected terminal test",
        },
    )

    assert create_response.status_code == 201

    leave_request_id = create_response.json()["id"]

    reject_response = client.post(
        f"/leave/requests/{leave_request_id}/status",
        headers={"X-Tenant-ID": str(tenant.id)},
        json={"status": "REJECTED"},
    )

    assert reject_response.status_code == 200
    assert reject_response.json()["status"] == "REJECTED"

    cancel_response = client.post(
        f"/leave/requests/{leave_request_id}/status",
        headers={"X-Tenant-ID": str(tenant.id)},
        json={"status": "CANCELLED"},
    )

    assert cancel_response.status_code == 400
    assert cancel_response.json()["detail"] == (
        "Invalid leave request status transition: REJECTED -> CANCELLED."
    )
    


def test_list_leave_requests_returns_tenant_requests(db):
    tenant = Tenant(
        legal_name="Leave List Tenant",
        country_code="KE",
        timezone="Africa/Nairobi",
        currency_code="KES",
    )
    db.add(tenant)
    db.flush()

    person = Person(
        tenant_id=tenant.id,
        person_number=f"P-{uuid4().hex[:8]}",
        first_name="List",
        last_name="Employee",
    )
    db.add(person)
    db.flush()

    employee = Employee(
        tenant_id=tenant.id,
        person_id=person.id,
        employee_number=f"E-{uuid4().hex[:8]}",
        employment_status=EmploymentStatus.ACTIVE,
        employment_type=EmploymentType.PERMANENT,
        hire_date=date(2025, 1, 1),
    )
    db.add(employee)
    db.flush()

    leave_type = LeaveType(
        tenant_id=tenant.id,
        code="ANNUAL",
        name="Annual Leave",
        active=True,
    )
    db.add(leave_type)
    db.flush()

    first_response = client.post(
        "/leave/requests",
        headers={"X-Tenant-ID": str(tenant.id)},
        json={
            "employee_id": str(employee.id),
            "leave_type_id": str(leave_type.id),
            "start_date": "2026-12-01",
            "end_date": "2026-12-03",
            "reason": "First leave",
        },
    )

    assert first_response.status_code == 201

    second_response = client.post(
        "/leave/requests",
        headers={"X-Tenant-ID": str(tenant.id)},
        json={
            "employee_id": str(employee.id),
            "leave_type_id": str(leave_type.id),
            "start_date": "2027-01-10",
            "end_date": "2027-01-12",
            "reason": "Second leave",
        },
    )

    assert second_response.status_code == 201

    response = client.get(
        "/leave/requests",
        headers={"X-Tenant-ID": str(tenant.id)},
    )

    assert response.status_code == 200

    data = response.json()

    assert len(data) == 2
    assert all(item["tenant_id"] == str(tenant.id) for item in data)

    request_ids = {item["id"] for item in data}

    assert first_response.json()["id"] in request_ids
    assert second_response.json()["id"] in request_ids





def test_list_leave_requests_is_tenant_scoped(db):
    tenant_a = Tenant(
        legal_name="Leave List Tenant A",
        country_code="KE",
        timezone="Africa/Nairobi",
        currency_code="KES",
    )
    tenant_b = Tenant(
        legal_name="Leave List Tenant B",
        country_code="KE",
        timezone="Africa/Nairobi",
        currency_code="KES",
    )

    db.add_all([tenant_a, tenant_b])
    db.flush()

    person = Person(
        tenant_id=tenant_a.id,
        person_number=f"P-{uuid4().hex[:8]}",
        first_name="Tenant",
        last_name="A",
    )
    db.add(person)
    db.flush()

    employee = Employee(
        tenant_id=tenant_a.id,
        person_id=person.id,
        employee_number=f"E-{uuid4().hex[:8]}",
        employment_status=EmploymentStatus.ACTIVE,
        employment_type=EmploymentType.PERMANENT,
        hire_date=date(2025, 1, 1),
    )
    db.add(employee)
    db.flush()

    leave_type = LeaveType(
        tenant_id=tenant_a.id,
        code="ANNUAL",
        name="Annual Leave",
        active=True,
    )
    db.add(leave_type)
    db.flush()

    create_response = client.post(
        "/leave/requests",
        headers={"X-Tenant-ID": str(tenant_a.id)},
        json={
            "employee_id": str(employee.id),
            "leave_type_id": str(leave_type.id),
            "start_date": "2027-02-01",
            "end_date": "2027-02-03",
            "reason": "Tenant A leave",
        },
    )

    assert create_response.status_code == 201

    leave_request_id = create_response.json()["id"]

    response_a = client.get(
        "/leave/requests",
        headers={"X-Tenant-ID": str(tenant_a.id)},
    )

    assert response_a.status_code == 200

    data_a = response_a.json()

    assert len(data_a) == 1
    assert data_a[0]["id"] == leave_request_id
    assert data_a[0]["tenant_id"] == str(tenant_a.id)

    response_b = client.get(
        "/leave/requests",
        headers={"X-Tenant-ID": str(tenant_b.id)},
    )

    assert response_b.status_code == 200

    data_b = response_b.json()

    assert data_b == []



def test_list_leave_requests_returns_empty_list_for_tenant_without_requests(db):
    tenant = Tenant(
        legal_name="Empty Leave List Tenant",
        country_code="KE",
        timezone="Africa/Nairobi",
        currency_code="KES",
    )
    db.add(tenant)
    db.flush()

    response = client.get(
        "/leave/requests",
        headers={"X-Tenant-ID": str(tenant.id)},
    )

    assert response.status_code == 200
    assert response.json() == []




def test_list_leave_requests_filters_by_employee(db):
    tenant = Tenant(
        legal_name="Leave Employee Filter Tenant",
        country_code="KE",
        timezone="Africa/Nairobi",
        currency_code="KES",
    )
    db.add(tenant)
    db.flush()

    person_a = Person(
        tenant_id=tenant.id,
        person_number=f"P-{uuid4().hex[:8]}",
        first_name="Employee",
        last_name="A",
    )
    person_b = Person(
        tenant_id=tenant.id,
        person_number=f"P-{uuid4().hex[:8]}",
        first_name="Employee",
        last_name="B",
    )
    db.add_all([person_a, person_b])
    db.flush()

    employee_a = Employee(
        tenant_id=tenant.id,
        person_id=person_a.id,
        employee_number=f"E-{uuid4().hex[:8]}",
        employment_status=EmploymentStatus.ACTIVE,
        employment_type=EmploymentType.PERMANENT,
        hire_date=date(2025, 1, 1),
    )
    employee_b = Employee(
        tenant_id=tenant.id,
        person_id=person_b.id,
        employee_number=f"E-{uuid4().hex[:8]}",
        employment_status=EmploymentStatus.ACTIVE,
        employment_type=EmploymentType.PERMANENT,
        hire_date=date(2025, 1, 1),
    )
    db.add_all([employee_a, employee_b])
    db.flush()

    leave_type = LeaveType(
        tenant_id=tenant.id,
        code="ANNUAL",
        name="Annual Leave",
        active=True,
    )
    db.add(leave_type)
    db.flush()

    first_response = client.post(
        "/leave/requests",
        headers={"X-Tenant-ID": str(tenant.id)},
        json={
            "employee_id": str(employee_a.id),
            "leave_type_id": str(leave_type.id),
            "start_date": "2027-09-01",
            "end_date": "2027-09-03",
            "reason": "Employee A leave",
        },
    )

    assert first_response.status_code == 201

    second_response = client.post(
        "/leave/requests",
        headers={"X-Tenant-ID": str(tenant.id)},
        json={
            "employee_id": str(employee_b.id),
            "leave_type_id": str(leave_type.id),
            "start_date": "2027-10-01",
            "end_date": "2027-10-03",
            "reason": "Employee B leave",
        },
    )

    assert second_response.status_code == 201

    response = client.get(
        f"/leave/requests?employee_id={employee_a.id}",
        headers={"X-Tenant-ID": str(tenant.id)},
    )

    assert response.status_code == 200

    data = response.json()

    assert len(data) == 1
    assert data[0]["employee_id"] == str(employee_a.id)
    assert data[0]["id"] == first_response.json()["id"]



def test_list_leave_requests_filters_by_status(db):
    tenant = Tenant(
        legal_name="Leave Status Filter Tenant",
        country_code="KE",
        timezone="Africa/Nairobi",
        currency_code="KES",
    )
    db.add(tenant)
    db.flush()

    person = Person(
        tenant_id=tenant.id,
        person_number=f"P-{uuid4().hex[:8]}",
        first_name="Status",
        last_name="Employee",
    )
    db.add(person)
    db.flush()

    employee = Employee(
        tenant_id=tenant.id,
        person_id=person.id,
        employee_number=f"E-{uuid4().hex[:8]}",
        employment_status=EmploymentStatus.ACTIVE,
        employment_type=EmploymentType.PERMANENT,
        hire_date=date(2025, 1, 1),
    )
    db.add(employee)
    db.flush()

    leave_type = LeaveType(
        tenant_id=tenant.id,
        code="ANNUAL",
        name="Annual Leave",
        active=True,
    )
    db.add(leave_type)
    db.flush()

    pending_response = client.post(
        "/leave/requests",
        headers={"X-Tenant-ID": str(tenant.id)},
        json={
            "employee_id": str(employee.id),
            "leave_type_id": str(leave_type.id),
            "start_date": "2027-11-01",
            "end_date": "2027-11-03",
            "reason": "Pending leave",
        },
    )

    assert pending_response.status_code == 201

    approved_response = client.post(
        "/leave/requests",
        headers={"X-Tenant-ID": str(tenant.id)},
        json={
            "employee_id": str(employee.id),
            "leave_type_id": str(leave_type.id),
            "start_date": "2027-12-01",
            "end_date": "2027-12-03",
            "reason": "Approved leave",
        },
    )

    assert approved_response.status_code == 201

    approved_id = approved_response.json()["id"]

    transition_response = client.post(
        f"/leave/requests/{approved_id}/status",
        headers={"X-Tenant-ID": str(tenant.id)},
        json={
            "status": "APPROVED",
        },
    )

    assert transition_response.status_code == 200

    response = client.get(
        "/leave/requests?status=APPROVED",
        headers={"X-Tenant-ID": str(tenant.id)},
    )

    assert response.status_code == 200

    data = response.json()

    assert len(data) == 1
    assert data[0]["id"] == approved_id
    assert data[0]["status"] == "APPROVED"


def test_list_leave_requests_filters_by_employee_and_status(db):
    tenant = Tenant(
        legal_name="Leave Combined Filter Tenant",
        country_code="KE",
        timezone="Africa/Nairobi",
        currency_code="KES",
    )
    db.add(tenant)
    db.flush()

    person_a = Person(
        tenant_id=tenant.id,
        person_number=f"P-{uuid4().hex[:8]}",
        first_name="Combined",
        last_name="A",
    )
    person_b = Person(
        tenant_id=tenant.id,
        person_number=f"P-{uuid4().hex[:8]}",
        first_name="Combined",
        last_name="B",
    )
    db.add_all([person_a, person_b])
    db.flush()

    employee_a = Employee(
        tenant_id=tenant.id,
        person_id=person_a.id,
        employee_number=f"E-{uuid4().hex[:8]}",
        employment_status=EmploymentStatus.ACTIVE,
        employment_type=EmploymentType.PERMANENT,
        hire_date=date(2025, 1, 1),
    )
    employee_b = Employee(
        tenant_id=tenant.id,
        person_id=person_b.id,
        employee_number=f"E-{uuid4().hex[:8]}",
        employment_status=EmploymentStatus.ACTIVE,
        employment_type=EmploymentType.PERMANENT,
        hire_date=date(2025, 1, 1),
    )
    db.add_all([employee_a, employee_b])
    db.flush()

    leave_type = LeaveType(
        tenant_id=tenant.id,
        code="ANNUAL",
        name="Annual Leave",
        active=True,
    )
    db.add(leave_type)
    db.flush()

    matching_response = client.post(
        "/leave/requests",
        headers={"X-Tenant-ID": str(tenant.id)},
        json={
            "employee_id": str(employee_a.id),
            "leave_type_id": str(leave_type.id),
            "start_date": "2028-01-10",
            "end_date": "2028-01-12",
            "reason": "Matching request",
        },
    )

    assert matching_response.status_code == 201

    matching_id = matching_response.json()["id"]

    approve_response = client.post(
        f"/leave/requests/{matching_id}/status",
        headers={"X-Tenant-ID": str(tenant.id)},
        json={"status": "APPROVED"},
    )

    assert approve_response.status_code == 200

    employee_a_pending = client.post(
        "/leave/requests",
        headers={"X-Tenant-ID": str(tenant.id)},
        json={
            "employee_id": str(employee_a.id),
            "leave_type_id": str(leave_type.id),
            "start_date": "2028-02-10",
            "end_date": "2028-02-12",
            "reason": "Employee A pending",
        },
    )

    assert employee_a_pending.status_code == 201

    employee_b_approved = client.post(
        "/leave/requests",
        headers={"X-Tenant-ID": str(tenant.id)},
        json={
            "employee_id": str(employee_b.id),
            "leave_type_id": str(leave_type.id),
            "start_date": "2028-03-10",
            "end_date": "2028-03-12",
            "reason": "Employee B approved",
        },
    )

    assert employee_b_approved.status_code == 201

    employee_b_approved_id = employee_b_approved.json()["id"]

    approve_b_response = client.post(
        f"/leave/requests/{employee_b_approved_id}/status",
        headers={"X-Tenant-ID": str(tenant.id)},
        json={"status": "APPROVED"},
    )

    assert approve_b_response.status_code == 200

    response = client.get(
        f"/leave/requests?employee_id={employee_a.id}&status=APPROVED",
        headers={"X-Tenant-ID": str(tenant.id)},
    )

    assert response.status_code == 200

    data = response.json()

    assert len(data) == 1
    assert data[0]["id"] == matching_id
    assert data[0]["employee_id"] == str(employee_a.id)
    assert data[0]["status"] == "APPROVED"




def test_list_leave_requests_filters_remain_tenant_scoped(db):
    tenant_a = Tenant(
        legal_name="Filtered Tenant A",
        country_code="KE",
        timezone="Africa/Nairobi",
        currency_code="KES",
    )
    tenant_b = Tenant(
        legal_name="Filtered Tenant B",
        country_code="KE",
        timezone="Africa/Nairobi",
        currency_code="KES",
    )
    db.add_all([tenant_a, tenant_b])
    db.flush()

    person_a = Person(
        tenant_id=tenant_a.id,
        person_number=f"P-{uuid4().hex[:8]}",
        first_name="Tenant",
        last_name="A",
    )
    person_b = Person(
        tenant_id=tenant_b.id,
        person_number=f"P-{uuid4().hex[:8]}",
        first_name="Tenant",
        last_name="B",
    )
    db.add_all([person_a, person_b])
    db.flush()

    employee_a = Employee(
        tenant_id=tenant_a.id,
        person_id=person_a.id,
        employee_number=f"E-{uuid4().hex[:8]}",
        employment_status=EmploymentStatus.ACTIVE,
        employment_type=EmploymentType.PERMANENT,
        hire_date=date(2025, 1, 1),
    )
    employee_b = Employee(
        tenant_id=tenant_b.id,
        person_id=person_b.id,
        employee_number=f"E-{uuid4().hex[:8]}",
        employment_status=EmploymentStatus.ACTIVE,
        employment_type=EmploymentType.PERMANENT,
        hire_date=date(2025, 1, 1),
    )
    db.add_all([employee_a, employee_b])
    db.flush()

    leave_type_a = LeaveType(
        tenant_id=tenant_a.id,
        code="ANNUAL",
        name="Annual Leave",
        active=True,
    )
    leave_type_b = LeaveType(
        tenant_id=tenant_b.id,
        code="ANNUAL",
        name="Annual Leave",
        active=True,
    )
    db.add_all([leave_type_a, leave_type_b])
    db.flush()

    request_b = client.post(
        "/leave/requests",
        headers={"X-Tenant-ID": str(tenant_b.id)},
        json={
            "employee_id": str(employee_b.id),
            "leave_type_id": str(leave_type_b.id),
            "start_date": "2028-04-10",
            "end_date": "2028-04-12",
            "reason": "Tenant B leave",
        },
    )

    assert request_b.status_code == 201

    response = client.get(
        f"/leave/requests?employee_id={employee_b.id}&status=PENDING",
        headers={"X-Tenant-ID": str(tenant_a.id)},
    )

    assert response.status_code == 200
    assert response.json() == []


def test_leave_request_status_transition_is_tenant_scoped(db):
    tenant_a = Tenant(
        legal_name="Leave Transition Tenant A",
        country_code="KE",
        timezone="Africa/Nairobi",
        currency_code="KES",
    )
    tenant_b = Tenant(
        legal_name="Leave Transition Tenant B",
        country_code="KE",
        timezone="Africa/Nairobi",
        currency_code="KES",
    )
    db.add_all([tenant_a, tenant_b])
    db.flush()

    person_a = Person(
        tenant_id=tenant_a.id,
        person_number=f"P-{uuid4().hex[:8]}",
        first_name="Tenant",
        last_name="A",
    )
    db.add(person_a)
    db.flush()

    employee_a = Employee(
        tenant_id=tenant_a.id,
        person_id=person_a.id,
        employee_number=f"E-{uuid4().hex[:8]}",
        employment_status=EmploymentStatus.ACTIVE,
        employment_type=EmploymentType.PERMANENT,
        hire_date=date(2025, 1, 1),
    )
    db.add(employee_a)
    db.flush()

    leave_type_a = LeaveType(
        tenant_id=tenant_a.id,
        code="ANNUAL",
        name="Annual Leave",
        active=True,
    )
    db.add(leave_type_a)
    db.flush()

    create_response = client.post(
        "/leave/requests",
        headers={"X-Tenant-ID": str(tenant_a.id)},
        json={
            "employee_id": str(employee_a.id),
            "leave_type_id": str(leave_type_a.id),
            "start_date": "2028-05-10",
            "end_date": "2028-05-12",
            "reason": "Tenant A leave",
        },
    )

    assert create_response.status_code == 201

    leave_request_id = create_response.json()["id"]

    cross_tenant_response = client.post(
        f"/leave/requests/{leave_request_id}/status",
        headers={"X-Tenant-ID": str(tenant_b.id)},
        json={
            "status": "APPROVED",
        },
    )

    assert cross_tenant_response.status_code == 400
    assert cross_tenant_response.json()["detail"] == (
        "Leave request not found for this tenant."
    )

    verify_response = client.get(
        f"/leave/requests/{leave_request_id}",
        headers={"X-Tenant-ID": str(tenant_a.id)},
    )

    assert verify_response.status_code == 200
    assert verify_response.json()["status"] == "PENDING"
from datetime import date, datetime
from uuid import uuid4

from fastapi.testclient import TestClient

from app.hr.enums import EmploymentStatus, EmploymentType
from app.hr.models import Employee, Person
from app.main import app
from app.organization.models import Tenant


client = TestClient(app)


def create_tenant(db, name="Attendance Test Tenant"):
    tenant = Tenant(
        legal_name=name,
        country_code="KE",
        timezone="Africa/Nairobi",
        currency_code="KES",
    )
    db.add(tenant)
    db.flush()

    return tenant


def create_employee(
    db,
    tenant,
    *,
    status=EmploymentStatus.ACTIVE,
    first_name="Attendance",
    last_name="Employee",
):
    person = Person(
        tenant_id=tenant.id,
        person_number=f"P-{uuid4().hex[:8]}",
        first_name=first_name,
        last_name=last_name,
    )
    db.add(person)
    db.flush()

    employee = Employee(
        tenant_id=tenant.id,
        person_id=person.id,
        employee_number=f"E-{uuid4().hex[:8]}",
        employment_status=status,
        employment_type=EmploymentType.PERMANENT,
        hire_date=date(2025, 1, 1),
        termination_date=(
            date(2026, 9, 30)
            if status == EmploymentStatus.TERMINATED
            else None
        ),
        termination_reason=(
            "Employment ended"
            if status == EmploymentStatus.TERMINATED
            else None
        ),
    )
    db.add(employee)
    db.flush()

    return employee


def test_create_attendance_record(db):
    tenant = create_tenant(db)
    employee = create_employee(db, tenant)

    response = client.post(
        "/attendance/records",
        headers={"X-Tenant-ID": str(tenant.id)},
        json={
            "employee_id": str(employee.id),
            "attendance_date": "2026-10-07",
            "check_in": "2026-10-07T08:00:00+03:00",
            "check_out": "2026-10-07T17:00:00+03:00",
            "status": "PRESENT",
            "source": "MANUAL",
            "notes": "Normal working day",
        },
    )

    assert response.status_code == 201

    data = response.json()

    assert data["tenant_id"] == str(tenant.id)
    assert data["employee_id"] == str(employee.id)
    assert data["attendance_date"] == "2026-10-07"
    assert data["status"] == "PRESENT"
    assert data["source"] == "MANUAL"
    assert data["notes"] == "Normal working day"
    assert data["check_in"] is not None
    assert data["check_out"] is not None
    assert data["id"] is not None
    assert data["created_at"] is not None
    assert data["updated_at"] is not None


def test_create_attendance_record_allows_missing_check_times(db):
    tenant = create_tenant(db, "Attendance Nullable Times Tenant")
    employee = create_employee(db, tenant)

    response = client.post(
        "/attendance/records",
        headers={"X-Tenant-ID": str(tenant.id)},
        json={
            "employee_id": str(employee.id),
            "attendance_date": "2026-10-08",
            "status": "ABSENT",
            "source": "SYSTEM",
            "notes": "No check-in or check-out",
        },
    )

    assert response.status_code == 201

    data = response.json()

    assert data["employee_id"] == str(employee.id)
    assert data["attendance_date"] == "2026-10-08"
    assert data["status"] == "ABSENT"
    assert data["source"] == "SYSTEM"
    assert data["check_in"] is None
    assert data["check_out"] is None


def test_create_attendance_record_rejects_terminated_employee(db):
    tenant = create_tenant(db, "Attendance Terminated Tenant")

    employee = create_employee(
        db,
        tenant,
        status=EmploymentStatus.TERMINATED,
        first_name="Terminated",
        last_name="Employee",
    )

    response = client.post(
        "/attendance/records",
        headers={"X-Tenant-ID": str(tenant.id)},
        json={
            "employee_id": str(employee.id),
            "attendance_date": "2026-10-07",
            "check_in": "2026-10-07T08:00:00+03:00",
            "check_out": "2026-10-07T17:00:00+03:00",
            "status": "PRESENT",
            "source": "MANUAL",
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == (
        "Terminated employees cannot receive new attendance records."
    )


def test_create_attendance_record_rejects_cross_tenant_employee(db):
    tenant_a = create_tenant(db, "Attendance Tenant A")
    tenant_b = create_tenant(db, "Attendance Tenant B")

    employee_a = create_employee(
        db,
        tenant_a,
        first_name="Tenant",
        last_name="A",
    )

    response = client.post(
        "/attendance/records",
        headers={"X-Tenant-ID": str(tenant_b.id)},
        json={
            "employee_id": str(employee_a.id),
            "attendance_date": "2026-10-07",
            "status": "PRESENT",
            "source": "MANUAL",
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == (
        "Employee not found for this tenant."
    )


def test_create_attendance_record_rejects_duplicate_employee_date(db):
    tenant = create_tenant(db, "Attendance Duplicate Tenant")
    employee = create_employee(db, tenant)

    payload = {
        "employee_id": str(employee.id),
        "attendance_date": "2026-10-09",
        "check_in": "2026-10-09T08:00:00+03:00",
        "check_out": "2026-10-09T17:00:00+03:00",
        "status": "PRESENT",
        "source": "MANUAL",
    }

    first_response = client.post(
        "/attendance/records",
        headers={"X-Tenant-ID": str(tenant.id)},
        json=payload,
    )

    assert first_response.status_code == 201

    second_response = client.post(
        "/attendance/records",
        headers={"X-Tenant-ID": str(tenant.id)},
        json=payload,
    )

    assert second_response.status_code == 400
    assert second_response.json()["detail"] == (
        "Attendance record already exists for this employee and date."
    )


def test_create_attendance_record_rejects_check_out_before_check_in(db):
    tenant = create_tenant(db, "Attendance Time Validation Tenant")
    employee = create_employee(db, tenant)

    response = client.post(
        "/attendance/records",
        headers={"X-Tenant-ID": str(tenant.id)},
        json={
            "employee_id": str(employee.id),
            "attendance_date": "2026-10-10",
            "check_in": "2026-10-10T17:00:00+03:00",
            "check_out": "2026-10-10T08:00:00+03:00",
            "status": "PRESENT",
            "source": "MANUAL",
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == (
        "check_out must be on or after check_in."
    )


def test_attendance_is_tenant_scoped(db):
    tenant_a = create_tenant(db, "Attendance Scope Tenant A")
    tenant_b = create_tenant(db, "Attendance Scope Tenant B")

    employee_a = create_employee(
        db,
        tenant_a,
        first_name="Tenant",
        last_name="A",
    )

    create_response = client.post(
        "/attendance/records",
        headers={"X-Tenant-ID": str(tenant_a.id)},
        json={
            "employee_id": str(employee_a.id),
            "attendance_date": "2026-10-11",
            "status": "PRESENT",
            "source": "MANUAL",
        },
    )

    assert create_response.status_code == 201

    cross_tenant_response = client.post(
        "/attendance/records",
        headers={"X-Tenant-ID": str(tenant_b.id)},
        json={
            "employee_id": str(employee_a.id),
            "attendance_date": "2026-10-11",
            "status": "PRESENT",
            "source": "MANUAL",
        },
    )

    assert cross_tenant_response.status_code == 400
    assert cross_tenant_response.json()["detail"] == (
        "Employee not found for this tenant."
    )


def test_create_attendance_record_allows_check_in_without_check_out(db):
    tenant = create_tenant(db, "Attendance Open Shift Tenant")
    employee = create_employee(db, tenant)

    response = client.post(
        "/attendance/records",
        headers={"X-Tenant-ID": str(tenant.id)},
        json={
            "employee_id": str(employee.id),
            "attendance_date": "2026-10-12",
            "check_in": "2026-10-12T08:15:00+03:00",
            "status": "LATE",
            "source": "DEVICE",
        },
    )

    assert response.status_code == 201

    data = response.json()

    assert data["check_in"] is not None
    assert data["check_out"] is None
    assert data["status"] == "LATE"
    assert data["source"] == "DEVICE"




def test_list_attendance_records(db):
    tenant = create_tenant(db, "Attendance List Tenant")
    employee = create_employee(db, tenant)

    for day in range(1, 4):
        response = client.post(
            "/attendance/records",
            headers={"X-Tenant-ID": str(tenant.id)},
            json={
                "employee_id": str(employee.id),
                "attendance_date": f"2026-10-0{day}",
                "status": "PRESENT",
                "source": "MANUAL",
            },
        )

        assert response.status_code == 201

    response = client.get(
        "/attendance/records",
        headers={"X-Tenant-ID": str(tenant.id)},
    )

    assert response.status_code == 200

    data = response.json()

    assert data["total"] == 3
    assert len(data["items"]) == 3

    assert [
        item["attendance_date"]
        for item in data["items"]
    ] == [
        "2026-10-03",
        "2026-10-02",
        "2026-10-01",
    ]


def test_list_attendance_records_filters_by_employee(db):
    tenant = create_tenant(db, "Attendance Employee Filter Tenant")

    employee_a = create_employee(
        db,
        tenant,
        first_name="Employee",
        last_name="A",
    )

    employee_b = create_employee(
        db,
        tenant,
        first_name="Employee",
        last_name="B",
    )

    for day, employee in [
        (1, employee_a),
        (2, employee_b),
        (3, employee_a),
    ]:
        response = client.post(
            "/attendance/records",
            headers={"X-Tenant-ID": str(tenant.id)},
            json={
                "employee_id": str(employee.id),
                "attendance_date": f"2026-10-0{day}",
                "status": "PRESENT",
                "source": "MANUAL",
            },
        )

        assert response.status_code == 201

    response = client.get(
        "/attendance/records",
        headers={"X-Tenant-ID": str(tenant.id)},
        params={"employee_id": str(employee_a.id)},
    )

    assert response.status_code == 200

    data = response.json()

    assert data["total"] == 2
    assert all(
        item["employee_id"] == str(employee_a.id)
        for item in data["items"]
    )


def test_list_attendance_records_filters_by_exact_date(db):
    tenant = create_tenant(db, "Attendance Exact Date Tenant")
    employee = create_employee(db, tenant)

    for day in range(1, 4):
        response = client.post(
            "/attendance/records",
            headers={"X-Tenant-ID": str(tenant.id)},
            json={
                "employee_id": str(employee.id),
                "attendance_date": f"2026-10-0{day}",
                "status": "PRESENT",
                "source": "MANUAL",
            },
        )

        assert response.status_code == 201

    response = client.get(
        "/attendance/records",
        headers={"X-Tenant-ID": str(tenant.id)},
        params={"attendance_date": "2026-10-02"},
    )

    assert response.status_code == 200

    data = response.json()

    assert data["total"] == 1
    assert data["items"][0]["attendance_date"] == "2026-10-02"


def test_list_attendance_records_filters_by_date_range(db):
    tenant = create_tenant(db, "Attendance Date Range Tenant")
    employee = create_employee(db, tenant)

    for day in range(1, 6):
        response = client.post(
            "/attendance/records",
            headers={"X-Tenant-ID": str(tenant.id)},
            json={
                "employee_id": str(employee.id),
                "attendance_date": f"2026-10-0{day}",
                "status": "PRESENT",
                "source": "MANUAL",
            },
        )

        assert response.status_code == 201

    response = client.get(
        "/attendance/records",
        headers={"X-Tenant-ID": str(tenant.id)},
        params={
            "start_date": "2026-10-02",
            "end_date": "2026-10-04",
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["total"] == 3

    assert [
        item["attendance_date"]
        for item in data["items"]
    ] == [
        "2026-10-04",
        "2026-10-03",
        "2026-10-02",
    ]


def test_list_attendance_records_filters_by_status(db):
    tenant = create_tenant(db, "Attendance Status Filter Tenant")
    employee = create_employee(db, tenant)

    statuses = [
        ("2026-10-01", "PRESENT"),
        ("2026-10-02", "LATE"),
        ("2026-10-03", "ABSENT"),
        ("2026-10-04", "LATE"),
    ]

    for attendance_date, attendance_status in statuses:
        response = client.post(
            "/attendance/records",
            headers={"X-Tenant-ID": str(tenant.id)},
            json={
                "employee_id": str(employee.id),
                "attendance_date": attendance_date,
                "status": attendance_status,
                "source": "MANUAL",
            },
        )

        assert response.status_code == 201

    response = client.get(
        "/attendance/records",
        headers={"X-Tenant-ID": str(tenant.id)},
        params={"attendance_status": "LATE"},
    )

    assert response.status_code == 200

    data = response.json()

    assert data["total"] == 2
    assert all(
        item["status"] == "LATE"
        for item in data["items"]
    )


def test_list_attendance_records_is_tenant_scoped(db):
    tenant_a = create_tenant(db, "Attendance GET Tenant A")
    tenant_b = create_tenant(db, "Attendance GET Tenant B")

    employee_a = create_employee(
        db,
        tenant_a,
        first_name="Tenant",
        last_name="A",
    )

    employee_b = create_employee(
        db,
        tenant_b,
        first_name="Tenant",
        last_name="B",
    )

    response = client.post(
        "/attendance/records",
        headers={"X-Tenant-ID": str(tenant_a.id)},
        json={
            "employee_id": str(employee_a.id),
            "attendance_date": "2026-10-01",
            "status": "PRESENT",
            "source": "MANUAL",
        },
    )

    assert response.status_code == 201

    response = client.post(
        "/attendance/records",
        headers={"X-Tenant-ID": str(tenant_b.id)},
        json={
            "employee_id": str(employee_b.id),
            "attendance_date": "2026-10-02",
            "status": "LATE",
            "source": "MANUAL",
        },
    )

    assert response.status_code == 201

    response = client.get(
        "/attendance/records",
        headers={"X-Tenant-ID": str(tenant_a.id)},
    )

    assert response.status_code == 200

    data = response.json()

    assert data["total"] == 1
    assert data["items"][0]["tenant_id"] == str(tenant_a.id)
    assert data["items"][0]["employee_id"] == str(employee_a.id)



def test_get_attendance_record(db):
    tenant = create_tenant(db, "Attendance Detail API Tenant")
    employee = create_employee(db, tenant)

    create_response = client.post(
        "/attendance/records",
        headers={"X-Tenant-ID": str(tenant.id)},
        json={
            "employee_id": str(employee.id),
            "attendance_date": "2026-10-15",
            "check_in": "2026-10-15T08:00:00+03:00",
            "check_out": "2026-10-15T17:00:00+03:00",
            "status": "PRESENT",
            "source": "MANUAL",
            "notes": "Detail API test",
        },
    )

    assert create_response.status_code == 201

    record_id = create_response.json()["id"]

    response = client.get(
        f"/attendance/records/{record_id}",
        headers={"X-Tenant-ID": str(tenant.id)},
    )

    assert response.status_code == 200

    data = response.json()

    assert data["id"] == record_id
    assert data["tenant_id"] == str(tenant.id)
    assert data["employee_id"] == str(employee.id)
    assert data["attendance_date"] == "2026-10-15"
    assert data["status"] == "PRESENT"
    assert data["source"] == "MANUAL"
    assert data["notes"] == "Detail API test"


def test_get_attendance_record_returns_404_for_missing_record(db):
    tenant = create_tenant(db, "Attendance Missing API Tenant")

    response = client.get(
        f"/attendance/records/{uuid4()}",
        headers={"X-Tenant-ID": str(tenant.id)},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == (
        "Attendance record not found for this tenant."
    )


def test_get_attendance_record_rejects_cross_tenant_access(db):
    tenant_a = create_tenant(db, "Attendance Detail API Tenant A")
    tenant_b = create_tenant(db, "Attendance Detail API Tenant B")

    employee_a = create_employee(
        db,
        tenant_a,
        first_name="Tenant",
        last_name="A",
    )

    create_response = client.post(
        "/attendance/records",
        headers={"X-Tenant-ID": str(tenant_a.id)},
        json={
            "employee_id": str(employee_a.id),
            "attendance_date": "2026-10-16",
            "status": "PRESENT",
            "source": "MANUAL",
        },
    )

    assert create_response.status_code == 201

    record_id = create_response.json()["id"]

    response = client.get(
        f"/attendance/records/{record_id}",
        headers={"X-Tenant-ID": str(tenant_b.id)},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == (
        "Attendance record not found for this tenant."
    )


def test_update_attendance_record(db):
    tenant = create_tenant(db, "Attendance Update API Tenant")
    employee = create_employee(db, tenant)

    create_response = client.post(
        "/attendance/records",
        headers={"X-Tenant-ID": str(tenant.id)},
        json={
            "employee_id": str(employee.id),
            "attendance_date": "2026-10-20",
            "check_in": "2026-10-20T08:00:00+03:00",
            "check_out": "2026-10-20T17:00:00+03:00",
            "status": "PRESENT",
            "source": "MANUAL",
            "notes": "Original notes",
        },
    )

    assert create_response.status_code == 201

    record_id = create_response.json()["id"]

    response = client.patch(
        f"/attendance/records/{record_id}",
        headers={"X-Tenant-ID": str(tenant.id)},
        json={
            "check_in": "2026-10-20T08:30:00+03:00",
            "status": "LATE",
            "notes": "Updated notes",
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["id"] == record_id
    assert data["tenant_id"] == str(tenant.id)
    assert data["employee_id"] == str(employee.id)
    assert data["attendance_date"] == "2026-10-20"
    assert datetime.fromisoformat(data["check_in"]) == datetime.fromisoformat(
    "2026-10-20T08:30:00+03:00")


    assert datetime.fromisoformat(data["check_out"]) == datetime.fromisoformat(
    "2026-10-20T17:00:00+03:00")

    assert data["status"] == "LATE"
    assert data["source"] == "MANUAL"
    assert data["notes"] == "Updated notes"


def test_update_attendance_record_supports_partial_update(db):
    tenant = create_tenant(db, "Attendance Partial Update API Tenant")
    employee = create_employee(db, tenant)

    create_response = client.post(
        "/attendance/records",
        headers={"X-Tenant-ID": str(tenant.id)},
        json={
            "employee_id": str(employee.id),
            "attendance_date": "2026-10-21",
            "check_in": "2026-10-21T08:00:00+03:00",
            "check_out": "2026-10-21T17:00:00+03:00",
            "status": "PRESENT",
            "source": "MANUAL",
            "notes": "Keep this note",
        },
    )

    assert create_response.status_code == 201

    record_id = create_response.json()["id"]

    response = client.patch(
        f"/attendance/records/{record_id}",
        headers={"X-Tenant-ID": str(tenant.id)},
        json={
            "status": "LATE",
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["status"] == "LATE"
    assert datetime.fromisoformat(data["check_in"]) == datetime.fromisoformat(
    "2026-10-21T08:00:00+03:00")


    assert datetime.fromisoformat(data["check_out"]) == datetime.fromisoformat(
    "2026-10-21T17:00:00+03:00")

    
    assert data["source"] == "MANUAL"
    assert data["notes"] == "Keep this note"


def test_update_attendance_record_can_clear_nullable_fields(db):
    tenant = create_tenant(db, "Attendance Clear API Tenant")
    employee = create_employee(db, tenant)

    create_response = client.post(
        "/attendance/records",
        headers={"X-Tenant-ID": str(tenant.id)},
        json={
            "employee_id": str(employee.id),
            "attendance_date": "2026-10-22",
            "check_in": "2026-10-22T08:00:00+03:00",
            "check_out": "2026-10-22T17:00:00+03:00",
            "status": "PRESENT",
            "source": "MANUAL",
            "notes": "Clear me",
        },
    )

    assert create_response.status_code == 201

    record_id = create_response.json()["id"]

    response = client.patch(
        f"/attendance/records/{record_id}",
        headers={"X-Tenant-ID": str(tenant.id)},
        json={
            "check_in": None,
            "check_out": None,
            "notes": None,
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["check_in"] is None
    assert data["check_out"] is None
    assert data["notes"] is None


def test_update_attendance_record_rejects_invalid_check_times(db):
    tenant = create_tenant(db, "Attendance Invalid Update API Tenant")
    employee = create_employee(db, tenant)

    create_response = client.post(
        "/attendance/records",
        headers={"X-Tenant-ID": str(tenant.id)},
        json={
            "employee_id": str(employee.id),
            "attendance_date": "2026-10-23",
            "check_in": "2026-10-23T08:00:00+03:00",
            "check_out": "2026-10-23T17:00:00+03:00",
            "status": "PRESENT",
            "source": "MANUAL",
        },
    )

    assert create_response.status_code == 201

    record_id = create_response.json()["id"]

    response = client.patch(
        f"/attendance/records/{record_id}",
        headers={"X-Tenant-ID": str(tenant.id)},
        json={
            "check_out": "2026-10-23T07:00:00+03:00",
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == (
        "check_out must be on or after check_in."
    )


def test_update_attendance_record_returns_404_for_missing_record(db):
    tenant = create_tenant(db, "Attendance Missing Update API Tenant")

    response = client.patch(
        f"/attendance/records/{uuid4()}",
        headers={"X-Tenant-ID": str(tenant.id)},
        json={
            "status": "LATE",
        },
    )

    assert response.status_code == 404
    assert response.json()["detail"] == (
        "Attendance record not found for this tenant."
    )


def test_update_attendance_record_rejects_cross_tenant_access(db):
    tenant_a = create_tenant(db, "Attendance Update API Tenant A")
    tenant_b = create_tenant(db, "Attendance Update API Tenant B")

    employee_a = create_employee(
        db,
        tenant_a,
        first_name="Tenant",
        last_name="A",
    )

    create_response = client.post(
        "/attendance/records",
        headers={"X-Tenant-ID": str(tenant_a.id)},
        json={
            "employee_id": str(employee_a.id),
            "attendance_date": "2026-10-24",
            "status": "PRESENT",
            "source": "MANUAL",
        },
    )

    assert create_response.status_code == 201

    record_id = create_response.json()["id"]

    response = client.patch(
        f"/attendance/records/{record_id}",
        headers={"X-Tenant-ID": str(tenant_b.id)},
        json={
            "status": "LATE",
        },
    )

    assert response.status_code == 404
    assert response.json()["detail"] == (
        "Attendance record not found for this tenant."
    )


def test_update_attendance_record_rejects_terminated_employee(db):
    tenant = create_tenant(db, "Attendance Terminated Update API Tenant")
    employee = create_employee(db, tenant)

    create_response = client.post(
        "/attendance/records",
        headers={"X-Tenant-ID": str(tenant.id)},
        json={
            "employee_id": str(employee.id),
            "attendance_date": "2026-10-25",
            "status": "PRESENT",
            "source": "MANUAL",
        },
    )

    assert create_response.status_code == 201

    record_id = create_response.json()["id"]

    employee.employment_status = EmploymentStatus.TERMINATED
    db.flush()

    response = client.patch(
        f"/attendance/records/{record_id}",
        headers={"X-Tenant-ID": str(tenant.id)},
        json={
            "status": "LATE",
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == (
        "Terminated employees cannot have their attendance records updated."
    )
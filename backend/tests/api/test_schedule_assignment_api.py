
from datetime import date, time
from uuid import uuid4

from fastapi.testclient import TestClient

from app.hr.enums import EmploymentStatus, EmploymentType
from app.hr.models import Employee, Person
from app.main import app
from app.organization.models import Tenant
from app.schedule.enums import ScheduleDay
from app.schedule.models import WorkScheduleDay, WorkSchedule, WorkShift


client = TestClient(app)


def create_tenant(db, name="Assignment API Tenant"):
    tenant = Tenant(
        legal_name=f"{name}-{uuid4().hex[:8]}",
        country_code="KE",
        timezone="Africa/Nairobi",
        currency_code="KES",
    )
    db.add(tenant)
    db.flush()
    return tenant


def create_employee(db, tenant_id, *, status=EmploymentStatus.ACTIVE):
    suffix = uuid4().hex[:8]

    person = Person(
        tenant_id=tenant_id,
        person_number=f"P-{suffix}",
        first_name="Test",
        last_name="Employee",
    )
    db.add(person)
    db.flush()

    employee = Employee(
        tenant_id=tenant_id,
        person_id=person.id,
        employee_number=f"E-{suffix}",
        employment_status=status,
        employment_type=EmploymentType.PERMANENT,
        hire_date=date(2020, 1, 1),
    )
    db.add(employee)
    db.flush()
    return employee


def create_schedule(db, tenant_id):
    suffix = uuid4().hex[:8]

    shift = WorkShift(
        tenant_id=tenant_id,
        code=f"DAY-{suffix}",
        name="Day Shift",
        start_time=time(8, 0),
        end_time=time(17, 0),
    )
    db.add(shift)
    db.flush()

    schedule = WorkSchedule(
        tenant_id=tenant_id,
        code=f"STD-{suffix}",
        name="Standard Schedule",
    )
    db.add(schedule)
    db.flush()

    schedule_day = WorkScheduleDay(
        tenant_id=tenant_id,
        work_schedule_id=schedule.id,
        day=ScheduleDay.MONDAY,
        work_shift_id=shift.id,
    )
    db.add(schedule_day)
    db.flush()

    return schedule


def create_assignment(
    tenant_id,
    employee_id,
    work_schedule_id,
    *,
    effective_from="2026-01-01",
    effective_to=None,
):
    payload = {
        "employee_id": str(employee_id),
        "work_schedule_id": str(work_schedule_id),
        "effective_from": effective_from,
    }
    if effective_to is not None:
        payload["effective_to"] = effective_to

    return client.post(
        "/schedule/assignments",
        headers={"X-Tenant-ID": str(tenant_id)},
        json=payload,
    )


def test_create_schedule_assignment(db):
    tenant = create_tenant(db)
    employee = create_employee(db, tenant.id)
    schedule = create_schedule(db, tenant.id)

    response = create_assignment(
        tenant.id,
        employee.id,
        schedule.id,
        effective_from="2026-01-01",
        effective_to="2026-06-01",
    )

    assert response.status_code == 201
    data = response.json()
    assert data["tenant_id"] == str(tenant.id)
    assert data["employee_id"] == str(employee.id)
    assert data["work_schedule_id"] == str(schedule.id)
    assert data["effective_from"] == "2026-01-01"
    assert data["effective_to"] == "2026-06-01"
    assert data["id"] is not None
    assert data["created_at"] is not None
    assert data["updated_at"] is not None


def test_create_open_ended_schedule_assignment(db):
    tenant = create_tenant(db)
    employee = create_employee(db, tenant.id)
    schedule = create_schedule(db, tenant.id)

    response = create_assignment(tenant.id, employee.id, schedule.id)

    assert response.status_code == 201
    assert response.json()["effective_to"] is None


def test_assignment_rejects_end_date_equal_to_start_date(db):
    tenant = create_tenant(db)
    employee = create_employee(db, tenant.id)
    schedule = create_schedule(db, tenant.id)

    response = create_assignment(
        tenant.id,
        employee.id,
        schedule.id,
        effective_from="2026-01-01",
        effective_to="2026-01-01",
    )

    assert response.status_code == 400
    assert "effective_to must be later" in response.json()["detail"]


def test_assignment_rejects_terminated_employee(db):
    tenant = create_tenant(db)
    employee = create_employee(
        db,
        tenant.id,
        status=EmploymentStatus.TERMINATED,
    )
    schedule = create_schedule(db, tenant.id)

    response = create_assignment(tenant.id, employee.id, schedule.id)

    assert response.status_code == 400
    assert "terminated employees" in response.json()["detail"].lower()


def test_assignment_rejects_employee_from_another_tenant(db):
    tenant_a = create_tenant(db, "Assignment Tenant A")
    tenant_b = create_tenant(db, "Assignment Tenant B")
    employee = create_employee(db, tenant_b.id)
    schedule = create_schedule(db, tenant_a.id)

    response = create_assignment(tenant_a.id, employee.id, schedule.id)

    assert response.status_code == 400
    assert "employee not found" in response.json()["detail"].lower()


def test_assignment_rejects_schedule_from_another_tenant(db):
    tenant_a = create_tenant(db, "Assignment Tenant A")
    tenant_b = create_tenant(db, "Assignment Tenant B")
    employee = create_employee(db, tenant_a.id)
    schedule = create_schedule(db, tenant_b.id)

    response = create_assignment(tenant_a.id, employee.id, schedule.id)

    assert response.status_code == 400
    assert "work schedule not found" in response.json()["detail"].lower()


def test_assignment_rejects_overlapping_period(db):
    tenant = create_tenant(db)
    employee = create_employee(db, tenant.id)
    schedule = create_schedule(db, tenant.id)

    first = create_assignment(
        tenant.id,
        employee.id,
        schedule.id,
        effective_from="2026-01-01",
        effective_to="2026-04-01",
    )
    assert first.status_code == 201

    second = create_assignment(
        tenant.id,
        employee.id,
        schedule.id,
        effective_from="2026-03-01",
        effective_to="2026-05-01",
    )

    assert second.status_code == 400
    assert "overlapping" in second.json()["detail"].lower()


def test_assignment_allows_adjacent_periods(db):
    tenant = create_tenant(db)
    employee = create_employee(db, tenant.id)
    schedule = create_schedule(db, tenant.id)

    first = create_assignment(
        tenant.id,
        employee.id,
        schedule.id,
        effective_from="2026-01-01",
        effective_to="2026-04-01",
    )
    assert first.status_code == 201

    second = create_assignment(
        tenant.id,
        employee.id,
        schedule.id,
        effective_from="2026-04-01",
        effective_to="2026-07-01",
    )

    assert second.status_code == 201


def test_assignment_requires_tenant_header(db):
    tenant = create_tenant(db)
    employee = create_employee(db, tenant.id)
    schedule = create_schedule(db, tenant.id)

    response = client.post(
        "/schedule/assignments",
        json={
            "employee_id": str(employee.id),
            "work_schedule_id": str(schedule.id),
            "effective_from": "2026-01-01",
        },
    )

    assert response.status_code == 422


def test_list_schedule_assignments_is_tenant_scoped(db):
    tenant_a = create_tenant(db, "List Tenant A")
    tenant_b = create_tenant(db, "List Tenant B")

    employee_a = create_employee(db, tenant_a.id)
    employee_b = create_employee(db, tenant_b.id)

    schedule_a = create_schedule(db, tenant_a.id)
    schedule_b = create_schedule(db, tenant_b.id)

    assignment_a = create_assignment(
        tenant_a.id, employee_a.id, schedule_a.id
    )
    assignment_b = create_assignment(
        tenant_b.id, employee_b.id, schedule_b.id
    )

    assert assignment_a.status_code == 201
    assert assignment_b.status_code == 201

    response = client.get(
        "/schedule/assignments",
        headers={"X-Tenant-ID": str(tenant_a.id)},
    )

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["tenant_id"] == str(tenant_a.id)
    assert data[0]["employee_id"] == str(employee_a.id)


def test_list_schedule_assignments_filters_by_employee(db):
    tenant = create_tenant(db)
    employee_a = create_employee(db, tenant.id)
    employee_b = create_employee(db, tenant.id)
    schedule = create_schedule(db, tenant.id)

    assignment_a = create_assignment(
        tenant.id, employee_a.id, schedule.id
    )
    assignment_b = create_assignment(
        tenant.id, employee_b.id, schedule.id
    )

    assert assignment_a.status_code == 201
    assert assignment_b.status_code == 201

    response = client.get(
        "/schedule/assignments",
        headers={"X-Tenant-ID": str(tenant.id)},
        params={"employee_id": str(employee_a.id)},
    )

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["employee_id"] == str(employee_a.id)


def test_list_schedule_assignments_returns_empty_list(db):
    tenant = create_tenant(db)

    response = client.get(
        "/schedule/assignments",
        headers={"X-Tenant-ID": str(tenant.id)},
    )

    assert response.status_code == 200
    assert response.json() == []





def test_daily_schedule_returns_assigned_employee_and_shift(db):
    tenant = create_tenant(db)
    employee = create_employee(db, tenant.id)
    schedule = create_schedule(db, tenant.id)

    assignment = create_assignment(
        tenant.id,
        employee.id,
        schedule.id,
        effective_from="2026-01-01",
    )
    assert assignment.status_code == 201

    response = client.get(
        "/schedule/daily",
        headers={"X-Tenant-ID": str(tenant.id)},
        params={"on_date": "2026-10-26"},  # Monday
    )

    assert response.status_code == 200
    data = response.json()

    assert data["on_date"] == "2026-10-26"
    assert data["day"] == "MONDAY"
    assert len(data["employees"]) == 1

    item = data["employees"][0]
    assert item["employee_id"] == str(employee.id)
    assert item["assignment_id"] is not None
    assert item["work_schedule_id"] == str(schedule.id)
    assert item["work_shift_code"].startswith("DAY-")
    assert item["shift_start_time"] == "08:00:00"
    assert item["shift_end_time"] == "17:00:00"


def test_daily_schedule_includes_employee_without_assignment(db):
    tenant = create_tenant(db)
    employee = create_employee(db, tenant.id)

    response = client.get(
        "/schedule/daily",
        headers={"X-Tenant-ID": str(tenant.id)},
        params={"on_date": "2026-10-26"},
    )

    assert response.status_code == 200
    data = response.json()

    assert len(data["employees"]) == 1
    item = data["employees"][0]
    assert item["employee_id"] == str(employee.id)
    assert item["assignment_id"] is None
    assert item["work_schedule_id"] is None
    assert item["work_shift_id"] is None


def test_daily_schedule_is_tenant_scoped(db):
    tenant_a = create_tenant(db, "Daily Tenant A")
    tenant_b = create_tenant(db, "Daily Tenant B")

    employee_a = create_employee(db, tenant_a.id)
    employee_b = create_employee(db, tenant_b.id)

    response = client.get(
        "/schedule/daily",
        headers={"X-Tenant-ID": str(tenant_a.id)},
        params={"on_date": "2026-10-26"},
    )

    assert response.status_code == 200
    data = response.json()

    employee_ids = {
        item["employee_id"] for item in data["employees"]
    }
    assert employee_ids == {str(employee_a.id)}
    assert str(employee_b.id) not in employee_ids


def test_daily_schedule_requires_tenant_header(db):
    response = client.get(
        "/schedule/daily",
        params={"on_date": "2026-10-26"},
    )

    assert response.status_code == 422


def test_daily_schedule_rejects_invalid_date(db):
    tenant = create_tenant(db)

    response = client.get(
        "/schedule/daily",
        headers={"X-Tenant-ID": str(tenant.id)},
        params={"on_date": "not-a-date"},
    )

    assert response.status_code == 422




def test_effective_employee_schedule_returns_assigned_shift(db):
    tenant = create_tenant(db)
    employee = create_employee(db, tenant.id)
    schedule = create_schedule(db, tenant.id)

    assignment = create_assignment(
        tenant.id,
        employee.id,
        schedule.id,
        effective_from="2026-01-01",
    )
    assert assignment.status_code == 201

    response = client.get(
        f"/schedule/employees/{employee.id}/effective",
        headers={"X-Tenant-ID": str(tenant.id)},
        params={"on_date": "2026-10-26"},
    )

    assert response.status_code == 200
    data = response.json()

    assert data["on_date"] == "2026-10-26"
    assert data["day"] == "MONDAY"
    assert data["employee_id"] == str(employee.id)
    assert data["employee_number"] == employee.employee_number
    assert data["assignment_id"] is not None
    assert data["work_schedule_id"] == str(schedule.id)
    assert data["work_shift_code"].startswith("DAY-")
    assert data["shift_start_time"] == "08:00:00"
    assert data["shift_end_time"] == "17:00:00"



def test_effective_employee_schedule_returns_nulls_without_assignment(db):
    tenant = create_tenant(db)
    employee = create_employee(db, tenant.id)

    response = client.get(
        f"/schedule/employees/{employee.id}/effective",
        headers={"X-Tenant-ID": str(tenant.id)},
        params={"on_date": "2026-10-26"},
    )

    assert response.status_code == 200
    data = response.json()

    assert data["employee_id"] == str(employee.id)
    assert data["on_date"] == "2026-10-26"
    assert data["day"] == "MONDAY"
    assert data["assignment_id"] is None
    assert data["work_schedule_id"] is None
    assert data["work_shift_id"] is None


def test_effective_employee_schedule_returns_404_for_other_tenant(db):
    tenant_a = create_tenant(db, "Effective Tenant A")
    tenant_b = create_tenant(db, "Effective Tenant B")
    employee_b = create_employee(db, tenant_b.id)

    response = client.get(
        f"/schedule/employees/{employee_b.id}/effective",
        headers={"X-Tenant-ID": str(tenant_a.id)},
        params={"on_date": "2026-10-26"},
    )

    assert response.status_code == 404



def test_effective_employee_schedule_returns_404_for_missing_employee(db):
    tenant = create_tenant(db)

    response = client.get(
        f"/schedule/employees/{uuid4()}/effective",
        headers={"X-Tenant-ID": str(tenant.id)},
        params={"on_date": "2026-10-26"},
    )

    assert response.status_code == 404

def test_effective_employee_schedule_returns_null_shift_on_day_off(db):
    tenant = create_tenant(db)
    employee = create_employee(db, tenant.id)
    schedule = create_schedule(db, tenant.id)

    assignment = create_assignment(
        tenant.id,
        employee.id,
        schedule.id,
        effective_from="2026-01-01",
    )
    assert assignment.status_code == 201

    response = client.get(
        f"/schedule/employees/{employee.id}/effective",
        headers={"X-Tenant-ID": str(tenant.id)},
        params={"on_date": "2026-10-27"},  # Tuesday
    )

    assert response.status_code == 200
    data = response.json()

    assert data["day"] == "TUESDAY"
    assert data["assignment_id"] is not None
    assert data["work_schedule_id"] == str(schedule.id)
    assert data["work_shift_id"] is None
    assert data["work_shift_code"] is None
    assert data["shift_start_time"] is None
    assert data["shift_end_time"] is None

def test_effective_employee_schedule_includes_assignment_on_start_date(db):
    tenant = create_tenant(db)
    employee = create_employee(db, tenant.id)
    schedule = create_schedule(db, tenant.id)

    assignment = create_assignment(
        tenant.id,
        employee.id,
        schedule.id,
        effective_from="2026-10-26",
        effective_to="2026-10-28",
    )
    assert assignment.status_code == 201

    response = client.get(
        f"/schedule/employees/{employee.id}/effective",
        headers={"X-Tenant-ID": str(tenant.id)},
        params={"on_date": "2026-10-26"},
    )

    assert response.status_code == 200
    data = response.json()

    assert data["assignment_id"] == assignment.json()["id"]
    assert data["work_schedule_id"] == str(schedule.id)


def test_effective_employee_schedule_excludes_assignment_on_end_date(db):
    tenant = create_tenant(db)
    employee = create_employee(db, tenant.id)
    schedule = create_schedule(db, tenant.id)

    assignment = create_assignment(
        tenant.id,
        employee.id,
        schedule.id,
        effective_from="2026-10-26",
        effective_to="2026-10-28",
    )
    assert assignment.status_code == 201

    response = client.get(
        f"/schedule/employees/{employee.id}/effective",
        headers={"X-Tenant-ID": str(tenant.id)},
        params={"on_date": "2026-10-28"},
    )

    assert response.status_code == 200
    data = response.json()

    assert data["assignment_id"] is None
    assert data["work_schedule_id"] is None
    assert data["work_shift_id"] is None


def test_effective_employee_schedule_switches_on_adjacent_assignment_boundary(db):
    tenant = create_tenant(db)
    employee = create_employee(db, tenant.id)

    schedule_a = create_schedule(db, tenant.id)
    schedule_b = create_schedule(db, tenant.id)

    first = create_assignment(
        tenant.id,
        employee.id,
        schedule_a.id,
        effective_from="2026-01-01",
        effective_to="2026-04-01",
    )
    assert first.status_code == 201

    second = create_assignment(
        tenant.id,
        employee.id,
        schedule_b.id,
        effective_from="2026-04-01",
        effective_to="2026-07-01",
    )
    assert second.status_code == 201

    response_before = client.get(
        f"/schedule/employees/{employee.id}/effective",
        headers={"X-Tenant-ID": str(tenant.id)},
        params={"on_date": "2026-03-31"},
    )

    assert response_before.status_code == 200
    assert (
        response_before.json()["assignment_id"]
        == first.json()["id"]
    )
    assert (
        response_before.json()["work_schedule_id"]
        == str(schedule_a.id)
    )

    response_at_boundary = client.get(
        f"/schedule/employees/{employee.id}/effective",
        headers={"X-Tenant-ID": str(tenant.id)},
        params={"on_date": "2026-04-01"},
    )

    assert response_at_boundary.status_code == 200
    assert (
        response_at_boundary.json()["assignment_id"]
        == second.json()["id"]
    )
    assert (
        response_at_boundary.json()["work_schedule_id"]
        == str(schedule_b.id)
    )

def test_daily_schedule_shows_no_active_assignment_after_expiry(db):
    tenant = create_tenant(db)
    employee = create_employee(db, tenant.id)
    schedule = create_schedule(db, tenant.id)

    assignment = create_assignment(
        tenant.id,
        employee.id,
        schedule.id,
        effective_from="2026-10-26",
        effective_to="2026-10-28",
    )
    assert assignment.status_code == 201

    response = client.get(
        "/schedule/daily",
        headers={"X-Tenant-ID": str(tenant.id)},
        params={"on_date": "2026-10-28"},
    )

    assert response.status_code == 200
    data = response.json()

    assert data["on_date"] == "2026-10-28"
    assert len(data["employees"]) == 1

    item = data["employees"][0]
    assert item["employee_id"] == str(employee.id)
    assert item["assignment_id"] is None
    assert item["work_schedule_id"] is None
    assert item["work_shift_id"] is None
    assert item["work_shift_code"] is None
    assert item["shift_start_time"] is None
    assert item["shift_end_time"] is None



def test_daily_schedule_excludes_terminated_employee(db):
    tenant = create_tenant(db)

    active_employee = create_employee(db, tenant.id)
    terminated_employee = create_employee(
        db,
        tenant.id,
        status=EmploymentStatus.TERMINATED,
    )

    schedule = create_schedule(db, tenant.id)

    active_assignment = create_assignment(
        tenant.id,
        active_employee.id,
        schedule.id,
        effective_from="2026-01-01",
    )
    assert active_assignment.status_code == 201

    response = client.get(
        "/schedule/daily",
        headers={"X-Tenant-ID": str(tenant.id)},
        params={"on_date": "2026-10-26"},
    )

    assert response.status_code == 200
    data = response.json()

    employee_ids = {
        item["employee_id"] for item in data["employees"]
    }

    assert str(active_employee.id) in employee_ids
    assert str(terminated_employee.id) not in employee_ids
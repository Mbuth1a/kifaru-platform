
from datetime import date
from uuid import uuid4

import pytest
from app.schedule.service import (
    DailyScheduleService,
    EmployeeScheduleAssignmentService,
)
from app.hr.enums import EmploymentStatus, EmploymentType
from app.hr.models import Employee, Person
from app.organization.models import Tenant
from app.schedule.models import EmployeeScheduleAssignment
from app.schedule.models import (
    EmployeeScheduleAssignment,
    WorkSchedule,
    WorkScheduleDay,
    WorkShift,
)
from app.schedule.enums import ScheduleDay


def create_tenant(db, name="Assignment Test Tenant"):
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
    tenant_id,
    *,
    employee_number="EMP-ASSIGN-001",
    status=EmploymentStatus.ACTIVE,
):
    person = Person(
        tenant_id=tenant_id,
        person_number=f"PERSON-{uuid4().hex[:10]}",
        first_name="Test",
        last_name="Employee",
    )
    db.add(person)
    db.flush()

    employee = Employee(
        tenant_id=tenant_id,
        person_id=person.id,
        employee_number=employee_number,
        employment_status=status,
        employment_type=EmploymentType.PERMANENT,
        hire_date=date(2025, 1, 1),
    )
    db.add(employee)
    db.flush()
    return employee


def create_schedule(db, tenant_id, *, code=None):
    shift = WorkShift(
        tenant_id=tenant_id,
        code=f"SHIFT-{uuid4().hex[:8]}",
        name="Day Shift",
        start_time=__import__("datetime").time(8, 0),
        end_time=__import__("datetime").time(17, 0),
    )
    db.add(shift)
    db.flush()

    schedule = WorkSchedule(
        tenant_id=tenant_id,
        code=code or f"SCHED-{uuid4().hex[:8]}",
        name="Standard Schedule",
    )
    db.add(schedule)
    db.flush()

    day = __import__(
        "app.schedule.models", fromlist=["WorkScheduleDay"]
    ).WorkScheduleDay(
        tenant_id=tenant_id,
        work_schedule_id=schedule.id,
        day=ScheduleDay.MONDAY,
        work_shift_id=shift.id,
    )
    db.add(day)
    db.flush()

    return schedule


def test_create_assignment(db):
    tenant = create_tenant(db)
    employee = create_employee(db, tenant.id)
    schedule = create_schedule(db, tenant.id)

    service = EmployeeScheduleAssignmentService(db)
    assignment = service.create_assignment(
        tenant_id=tenant.id,
        employee_id=employee.id,
        work_schedule_id=schedule.id,
        effective_from=date(2026, 1, 1),
        effective_to=date(2026, 4, 1),
    )

    assert assignment.id is not None
    assert assignment.tenant_id == tenant.id
    assert assignment.employee_id == employee.id
    assert assignment.work_schedule_id == schedule.id
    assert assignment.effective_from == date(2026, 1, 1)
    assert assignment.effective_to == date(2026, 4, 1)


def test_create_assignment_allows_open_ended_assignment(db):
    tenant = create_tenant(db)
    employee = create_employee(db, tenant.id)
    schedule = create_schedule(db, tenant.id)

    assignment = EmployeeScheduleAssignmentService(db).create_assignment(
        tenant_id=tenant.id,
        employee_id=employee.id,
        work_schedule_id=schedule.id,
        effective_from=date(2026, 1, 1),
    )

    assert assignment.effective_to is None


def test_create_assignment_rejects_end_date_equal_to_start_date(db):
    tenant = create_tenant(db)
    employee = create_employee(db, tenant.id)
    schedule = create_schedule(db, tenant.id)

    with pytest.raises(ValueError, match="effective_to must be later"):
        EmployeeScheduleAssignmentService(db).create_assignment(
            tenant_id=tenant.id,
            employee_id=employee.id,
            work_schedule_id=schedule.id,
            effective_from=date(2026, 1, 1),
            effective_to=date(2026, 1, 1),
        )


def test_create_assignment_rejects_end_date_before_start_date(db):
    tenant = create_tenant(db)
    employee = create_employee(db, tenant.id)
    schedule = create_schedule(db, tenant.id)

    with pytest.raises(ValueError, match="effective_to must be later"):
        EmployeeScheduleAssignmentService(db).create_assignment(
            tenant_id=tenant.id,
            employee_id=employee.id,
            work_schedule_id=schedule.id,
            effective_from=date(2026, 2, 1),
            effective_to=date(2026, 1, 1),
        )


def test_create_assignment_rejects_employee_from_another_tenant(db):
    tenant_a = create_tenant(db, "Assignment Tenant A")
    tenant_b = create_tenant(db, "Assignment Tenant B")
    employee_b = create_employee(db, tenant_b.id)
    schedule_a = create_schedule(db, tenant_a.id)

    with pytest.raises(ValueError, match="Employee not found for this tenant"):
        EmployeeScheduleAssignmentService(db).create_assignment(
            tenant_id=tenant_a.id,
            employee_id=employee_b.id,
            work_schedule_id=schedule_a.id,
            effective_from=date(2026, 1, 1),
        )


def test_create_assignment_rejects_missing_employee(db):
    tenant = create_tenant(db)
    schedule = create_schedule(db, tenant.id)

    with pytest.raises(ValueError, match="Employee not found for this tenant"):
        EmployeeScheduleAssignmentService(db).create_assignment(
            tenant_id=tenant.id,
            employee_id=uuid4(),
            work_schedule_id=schedule.id,
            effective_from=date(2026, 1, 1),
        )


def test_create_assignment_rejects_terminated_employee(db):
    tenant = create_tenant(db)
    employee = create_employee(
        db,
        tenant.id,
        status=EmploymentStatus.TERMINATED,
    )
    schedule = create_schedule(db, tenant.id)

    with pytest.raises(
        ValueError,
        match="Terminated employees cannot be assigned a work schedule",
    ):
        EmployeeScheduleAssignmentService(db).create_assignment(
            tenant_id=tenant.id,
            employee_id=employee.id,
            work_schedule_id=schedule.id,
            effective_from=date(2026, 1, 1),
        )


def test_create_assignment_rejects_schedule_from_another_tenant(db):
    tenant_a = create_tenant(db, "Schedule Owner Tenant")
    tenant_b = create_tenant(db, "Employee Owner Tenant")
    employee_b = create_employee(db, tenant_b.id)
    schedule_a = create_schedule(db, tenant_a.id)

    with pytest.raises(
        ValueError,
        match="Work schedule not found for this tenant",
    ):
        EmployeeScheduleAssignmentService(db).create_assignment(
            tenant_id=tenant_b.id,
            employee_id=employee_b.id,
            work_schedule_id=schedule_a.id,
            effective_from=date(2026, 1, 1),
        )


def test_create_assignment_rejects_overlapping_periods(db):
    tenant = create_tenant(db)
    employee = create_employee(db, tenant.id)
    schedule = create_schedule(db, tenant.id)
    service = EmployeeScheduleAssignmentService(db)

    service.create_assignment(
        tenant_id=tenant.id,
        employee_id=employee.id,
        work_schedule_id=schedule.id,
        effective_from=date(2026, 1, 1),
        effective_to=date(2026, 4, 1),
    )

    with pytest.raises(ValueError, match="overlapping the requested dates"):
        service.create_assignment(
            tenant_id=tenant.id,
            employee_id=employee.id,
            work_schedule_id=schedule.id,
            effective_from=date(2026, 3, 1),
            effective_to=date(2026, 6, 1),
        )


def test_create_assignment_allows_adjacent_periods(db):
    tenant = create_tenant(db)
    employee = create_employee(db, tenant.id)
    schedule = create_schedule(db, tenant.id)
    service = EmployeeScheduleAssignmentService(db)

    service.create_assignment(
        tenant_id=tenant.id,
        employee_id=employee.id,
        work_schedule_id=schedule.id,
        effective_from=date(2026, 1, 1),
        effective_to=date(2026, 4, 1),
    )

    second = service.create_assignment(
        tenant_id=tenant.id,
        employee_id=employee.id,
        work_schedule_id=schedule.id,
        effective_from=date(2026, 4, 1),
        effective_to=date(2026, 7, 1),
    )

    assert second.effective_from == date(2026, 4, 1)


def test_create_assignment_allows_overlapping_periods_for_different_employees(db):
    tenant = create_tenant(db)
    employee_a = create_employee(db, tenant.id, employee_number="EMP-A")
    employee_b = create_employee(db, tenant.id, employee_number="EMP-B")
    schedule = create_schedule(db, tenant.id)
    service = EmployeeScheduleAssignmentService(db)

    first = service.create_assignment(
        tenant_id=tenant.id,
        employee_id=employee_a.id,
        work_schedule_id=schedule.id,
        effective_from=date(2026, 1, 1),
        effective_to=date(2026, 4, 1),
    )
    second = service.create_assignment(
        tenant_id=tenant.id,
        employee_id=employee_b.id,
        work_schedule_id=schedule.id,
        effective_from=date(2026, 2, 1),
        effective_to=date(2026, 5, 1),
    )

    assert first.employee_id != second.employee_id



def test_daily_schedule_includes_assigned_employee_and_shift(db):
    tenant = create_tenant(db)
    employee = create_employee(db, tenant.id, employee_number="EMP-DAILY-001")
    schedule = create_schedule(db, tenant.id)

    EmployeeScheduleAssignmentService(db).create_assignment(
        tenant_id=tenant.id,
        employee_id=employee.id,
        work_schedule_id=schedule.id,
        effective_from=date(2026, 1, 1),
    )

    result = DailyScheduleService(db).get_daily_schedule(
        tenant_id=tenant.id,
        on_date=date(2026, 10, 26),  # Monday
    )

    assert result["day"] == ScheduleDay.MONDAY
    assert len(result["employees"]) == 1

    item = result["employees"][0]
    assert item["employee_id"] == employee.id
    assert item["employee_number"] == "EMP-DAILY-001"
    assert item["work_schedule_id"] == schedule.id
    assert item["work_shift_code"].startswith("SHIFT-")
    assert item["shift_start_time"].hour == 8
    assert item["shift_end_time"].hour == 17


def test_daily_schedule_includes_employee_without_assignment(db):
    tenant = create_tenant(db)
    employee = create_employee(db, tenant.id, employee_number="EMP-DAILY-002")

    result = DailyScheduleService(db).get_daily_schedule(
        tenant_id=tenant.id,
        on_date=date(2026, 10, 26),
    )

    assert len(result["employees"]) == 1
    item = result["employees"][0]
    assert item["employee_id"] == employee.id
    assert item["assignment_id"] is None
    assert item["work_schedule_id"] is None
    assert item["work_shift_id"] is None


def test_daily_schedule_represents_scheduled_day_off(db):
    tenant = create_tenant(db)
    employee = create_employee(db, tenant.id, employee_number="EMP-DAILY-003")
    schedule = create_schedule(db, tenant.id)

    EmployeeScheduleAssignmentService(db).create_assignment(
        tenant_id=tenant.id,
        employee_id=employee.id,
        work_schedule_id=schedule.id,
        effective_from=date(2026, 1, 1),
    )

    # The helper defines Monday only; Tuesday has no schedule-day row.
    result = DailyScheduleService(db).get_daily_schedule(
        tenant_id=tenant.id,
        on_date=date(2026, 10, 27),  # Tuesday
    )

    item = result["employees"][0]
    assert item["work_schedule_id"] == schedule.id
    assert item["work_shift_id"] is None
    assert item["shift_start_time"] is None
    assert item["shift_end_time"] is None


def test_daily_schedule_excludes_terminated_employees(db):
    tenant = create_tenant(db)
    create_employee(
        db,
        tenant.id,
        employee_number="EMP-DAILY-004",
        status=EmploymentStatus.TERMINATED,
    )
    create_employee(
        db,
        tenant.id,
        employee_number="EMP-DAILY-005",
        status=EmploymentStatus.ACTIVE,
    )

    result = DailyScheduleService(db).get_daily_schedule(
        tenant_id=tenant.id,
        on_date=date(2026, 10, 26),
    )

    assert len(result["employees"]) == 1
    assert result["employees"][0]["employee_number"] == "EMP-DAILY-005"
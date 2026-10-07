from datetime import date, datetime, timezone
from uuid import uuid4

import pytest

from app.attendance.enums import AttendanceSource, AttendanceStatus
from app.attendance.service import AttendanceService
from app.hr.enums import EmploymentStatus, EmploymentType
from app.hr.models import Employee, Person
from app.organization.models import Tenant


def create_tenant(db, name="Attendance Service Tenant"):
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
    )
    db.add(employee)
    db.flush()

    return employee


def create_attendance(
    db,
    *,
    tenant_id,
    employee_id,
    attendance_date,
    status=AttendanceStatus.PRESENT,
):
    record = AttendanceService(db).create_attendance_record(
        tenant_id=tenant_id,
        employee_id=employee_id,
        attendance_date=attendance_date,
        check_in=datetime(
            attendance_date.year,
            attendance_date.month,
            attendance_date.day,
            8,
            0,
            tzinfo=timezone.utc,
        ),
        check_out=datetime(
            attendance_date.year,
            attendance_date.month,
            attendance_date.day,
            17,
            0,
            tzinfo=timezone.utc,
        ),
        status=status,
        source=AttendanceSource.MANUAL,
    )

    db.commit()

    return record


def test_list_attendance_records_returns_tenant_records(db):
    tenant = create_tenant(db)
    employee = create_employee(db, tenant)

    create_attendance(
        db,
        tenant_id=tenant.id,
        employee_id=employee.id,
        attendance_date=date(2026, 10, 1),
    )

    create_attendance(
        db,
        tenant_id=tenant.id,
        employee_id=employee.id,
        attendance_date=date(2026, 10, 2),
    )

    service = AttendanceService(db)

    records = service.list_attendance_records(
        tenant_id=tenant.id,
    )

    assert len(records) == 2
    assert records[0].attendance_date == date(2026, 10, 2)
    assert records[1].attendance_date == date(2026, 10, 1)


def test_list_attendance_records_filters_by_employee(db):
    tenant = create_tenant(db)
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

    create_attendance(
        db,
        tenant_id=tenant.id,
        employee_id=employee_a.id,
        attendance_date=date(2026, 10, 1),
    )

    create_attendance(
        db,
        tenant_id=tenant.id,
        employee_id=employee_b.id,
        attendance_date=date(2026, 10, 2),
    )

    service = AttendanceService(db)

    records = service.list_attendance_records(
        tenant_id=tenant.id,
        employee_id=employee_a.id,
    )

    assert len(records) == 1
    assert records[0].employee_id == employee_a.id


def test_list_attendance_records_filters_by_exact_date(db):
    tenant = create_tenant(db)
    employee = create_employee(db, tenant)

    create_attendance(
        db,
        tenant_id=tenant.id,
        employee_id=employee.id,
        attendance_date=date(2026, 10, 1),
    )

    create_attendance(
        db,
        tenant_id=tenant.id,
        employee_id=employee.id,
        attendance_date=date(2026, 10, 2),
    )

    service = AttendanceService(db)

    records = service.list_attendance_records(
        tenant_id=tenant.id,
        attendance_date=date(2026, 10, 2),
    )

    assert len(records) == 1
    assert records[0].attendance_date == date(2026, 10, 2)


def test_list_attendance_records_filters_by_date_range(db):
    tenant = create_tenant(db)
    employee = create_employee(db, tenant)

    for day in range(1, 6):
        create_attendance(
            db,
            tenant_id=tenant.id,
            employee_id=employee.id,
            attendance_date=date(2026, 10, day),
        )

    service = AttendanceService(db)

    records = service.list_attendance_records(
        tenant_id=tenant.id,
        start_date=date(2026, 10, 2),
        end_date=date(2026, 10, 4),
    )

    assert len(records) == 3
    assert [record.attendance_date for record in records] == [
        date(2026, 10, 4),
        date(2026, 10, 3),
        date(2026, 10, 2),
    ]


def test_list_attendance_records_filters_by_status(db):
    tenant = create_tenant(db)
    employee = create_employee(db, tenant)

    create_attendance(
        db,
        tenant_id=tenant.id,
        employee_id=employee.id,
        attendance_date=date(2026, 10, 1),
        status=AttendanceStatus.PRESENT,
    )

    create_attendance(
        db,
        tenant_id=tenant.id,
        employee_id=employee.id,
        attendance_date=date(2026, 10, 2),
        status=AttendanceStatus.LATE,
    )

    service = AttendanceService(db)

    records = service.list_attendance_records(
        tenant_id=tenant.id,
        status=AttendanceStatus.LATE,
    )

    assert len(records) == 1
    assert records[0].status == AttendanceStatus.LATE


def test_list_attendance_records_is_tenant_scoped(db):
    tenant_a = create_tenant(db, "Attendance Service Tenant A")
    tenant_b = create_tenant(db, "Attendance Service Tenant B")

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

    create_attendance(
        db,
        tenant_id=tenant_a.id,
        employee_id=employee_a.id,
        attendance_date=date(2026, 10, 1),
    )

    create_attendance(
        db,
        tenant_id=tenant_b.id,
        employee_id=employee_b.id,
        attendance_date=date(2026, 10, 2),
    )

    service = AttendanceService(db)

    records = service.list_attendance_records(
        tenant_id=tenant_a.id,
    )

    assert len(records) == 1
    assert records[0].tenant_id == tenant_a.id
    assert records[0].employee_id == employee_a.id



def test_get_attendance_record_returns_record(db):
    tenant = create_tenant(db, "Attendance Detail Tenant")
    employee = create_employee(db, tenant)

    record = create_attendance(
        db,
        tenant_id=tenant.id,
        employee_id=employee.id,
        attendance_date=date(2026, 10, 15),
    )

    service = AttendanceService(db)

    result = service.get_attendance_record(
        tenant_id=tenant.id,
        record_id=record.id,
    )

    assert result.id == record.id
    assert result.tenant_id == tenant.id
    assert result.employee_id == employee.id
    assert result.attendance_date == date(2026, 10, 15)


def test_get_attendance_record_rejects_missing_record(db):
    tenant = create_tenant(db, "Attendance Missing Detail Tenant")

    service = AttendanceService(db)

    with pytest.raises(
        ValueError,
        match="Attendance record not found for this tenant.",
    ):
        service.get_attendance_record(
            tenant_id=tenant.id,
            record_id=uuid4(),
        )


def test_get_attendance_record_is_tenant_scoped(db):
    tenant_a = create_tenant(db, "Attendance Detail Tenant A")
    tenant_b = create_tenant(db, "Attendance Detail Tenant B")

    employee_a = create_employee(
        db,
        tenant_a,
        first_name="Tenant",
        last_name="A",
    )

    record = create_attendance(
        db,
        tenant_id=tenant_a.id,
        employee_id=employee_a.id,
        attendance_date=date(2026, 10, 16),
    )

    service = AttendanceService(db)

    with pytest.raises(
        ValueError,
        match="Attendance record not found for this tenant.",
    ):
        service.get_attendance_record(
            tenant_id=tenant_b.id,
            record_id=record.id,
        )



def test_update_attendance_record_updates_supplied_fields(db):
    tenant = create_tenant(db, "Attendance Update Tenant")
    employee = create_employee(db, tenant)

    record = create_attendance(
        db,
        tenant_id=tenant.id,
        employee_id=employee.id,
        attendance_date=date(2026, 10, 20),
    )

    service = AttendanceService(db)

    new_check_in = datetime(
        2026,
        10,
        20,
        8,
        30,
        tzinfo=timezone.utc,
    )

    updated = service.update_attendance_record(
        tenant_id=tenant.id,
        record_id=record.id,
        check_in=new_check_in,
        update_check_in=True,
    )

    assert updated.id == record.id
    assert updated.check_in == new_check_in
    assert updated.check_out == record.check_out
    assert updated.status == AttendanceStatus.PRESENT
    assert updated.source == AttendanceSource.MANUAL


def test_update_attendance_record_updates_multiple_fields(db):
    tenant = create_tenant(db, "Attendance Multi Update Tenant")
    employee = create_employee(db, tenant)

    record = create_attendance(
        db,
        tenant_id=tenant.id,
        employee_id=employee.id,
        attendance_date=date(2026, 10, 21),
    )

    service = AttendanceService(db)

    new_check_in = datetime(
        2026,
        10,
        21,
        9,
        15,
        tzinfo=timezone.utc,
    )

    new_check_out = datetime(
        2026,
        10,
        21,
        17,
        30,
        tzinfo=timezone.utc,
    )

    updated = service.update_attendance_record(
        tenant_id=tenant.id,
        record_id=record.id,
        check_in=new_check_in,
        check_out=new_check_out,
        status=AttendanceStatus.LATE,
        source=AttendanceSource.DEVICE,
        notes="Updated from device",
        update_check_in=True,
        update_check_out=True,
        update_status=True,
        update_source=True,
        update_notes=True,
    )

    assert updated.check_in == new_check_in
    assert updated.check_out == new_check_out
    assert updated.status == AttendanceStatus.LATE
    assert updated.source == AttendanceSource.DEVICE
    assert updated.notes == "Updated from device"


def test_update_attendance_record_can_clear_nullable_fields(db):
    tenant = create_tenant(db, "Attendance Clear Fields Tenant")
    employee = create_employee(db, tenant)

    record = create_attendance(
        db,
        tenant_id=tenant.id,
        employee_id=employee.id,
        attendance_date=date(2026, 10, 22),
    )

    service = AttendanceService(db)

    updated = service.update_attendance_record(
        tenant_id=tenant.id,
        record_id=record.id,
        check_in=None,
        check_out=None,
        notes=None,
        update_check_in=True,
        update_check_out=True,
        update_notes=True,
    )

    assert updated.check_in is None
    assert updated.check_out is None
    assert updated.notes is None


def test_update_attendance_record_rejects_invalid_check_times(db):
    tenant = create_tenant(db, "Attendance Invalid Update Tenant")
    employee = create_employee(db, tenant)

    record = create_attendance(
        db,
        tenant_id=tenant.id,
        employee_id=employee.id,
        attendance_date=date(2026, 10, 23),
    )

    service = AttendanceService(db)

    invalid_check_out = datetime(
        2026,
        10,
        23,
        7,
        0,
        tzinfo=timezone.utc,
    )

    with pytest.raises(
        ValueError,
        match="check_out must be on or after check_in.",
    ):
        service.update_attendance_record(
            tenant_id=tenant.id,
            record_id=record.id,
            check_out=invalid_check_out,
            update_check_out=True,
        )


def test_update_attendance_record_rejects_missing_record(db):
    tenant = create_tenant(db, "Attendance Missing Update Tenant")

    service = AttendanceService(db)

    with pytest.raises(
        ValueError,
        match="Attendance record not found for this tenant.",
    ):
        service.update_attendance_record(
            tenant_id=tenant.id,
            record_id=uuid4(),
            status=AttendanceStatus.LATE,
            update_status=True,
        )


def test_update_attendance_record_is_tenant_scoped(db):
    tenant_a = create_tenant(db, "Attendance Update Tenant A")
    tenant_b = create_tenant(db, "Attendance Update Tenant B")

    employee_a = create_employee(
        db,
        tenant_a,
        first_name="Tenant",
        last_name="A",
    )

    record = create_attendance(
        db,
        tenant_id=tenant_a.id,
        employee_id=employee_a.id,
        attendance_date=date(2026, 10, 24),
    )

    service = AttendanceService(db)

    with pytest.raises(
        ValueError,
        match="Attendance record not found for this tenant.",
    ):
        service.update_attendance_record(
            tenant_id=tenant_b.id,
            record_id=record.id,
            status=AttendanceStatus.LATE,
            update_status=True,
        )


def test_update_attendance_record_rejects_terminated_employee(db):
    tenant = create_tenant(db, "Attendance Terminated Update Tenant")
    employee = create_employee(
        db,
        tenant,
        status=EmploymentStatus.ACTIVE,
    )

    record = create_attendance(
        db,
        tenant_id=tenant.id,
        employee_id=employee.id,
        attendance_date=date(2026, 10, 25),
    )

    employee.employment_status = EmploymentStatus.TERMINATED
    db.flush()

    service = AttendanceService(db)

    with pytest.raises(
        ValueError,
        match=(
            "Terminated employees cannot have their attendance "
            "records updated."
        ),
    ):
        service.update_attendance_record(
            tenant_id=tenant.id,
            record_id=record.id,
            status=AttendanceStatus.LATE,
            update_status=True,
        )
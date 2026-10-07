from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from sqlalchemy.orm import Session

from app.hr.enums import EmploymentStatus
from app.hr.models import Employee

from .enums import AttendanceStatus
from .models import AttendanceRecord


class AttendanceService:
    """
    Application/service layer for Attendance Management.

    Responsibilities:
    - Enforce tenant isolation
    - Validate employee ownership
    - Prevent attendance for terminated employees
    - Prevent duplicate attendance for an employee/date
    - Validate check-in/check-out ordering
    - Retrieve tenant-scoped attendance records

    Transaction ownership remains with the API route.
    This service may flush() but does not commit or rollback.
    """

    def __init__(self, db: Session):
        self.db = db

    def _get_employee(
        self,
        *,
        tenant_id: UUID,
        employee_id: UUID,
    ) -> Employee:

        employee = (
            self.db.query(Employee)
            .filter(
                Employee.id == employee_id,
                Employee.tenant_id == tenant_id,
            )
            .first()
        )

        if employee is None:
            raise ValueError(
                "Employee not found for this tenant."
            )

        return employee

    def _check_duplicate(
        self,
        *,
        tenant_id: UUID,
        employee_id: UUID,
        attendance_date: date,
    ) -> None:

        existing_record = (
            self.db.query(AttendanceRecord)
            .filter(
                AttendanceRecord.tenant_id == tenant_id,
                AttendanceRecord.employee_id == employee_id,
                AttendanceRecord.attendance_date == attendance_date,
            )
            .first()
        )

        if existing_record is not None:
            raise ValueError(
                "Attendance record already exists for this employee and date."
            )

    def _validate_check_times(
        self,
        *,
        check_in: datetime | None,
        check_out: datetime | None,
    ) -> None:

        if (
            check_in is not None
            and check_out is not None
            and check_out < check_in
        ):
            raise ValueError(
                "check_out must be on or after check_in."
            )

    def create_attendance_record(
        self,
        *,
        tenant_id: UUID,
        employee_id: UUID,
        attendance_date: date,
        check_in: datetime | None = None,
        check_out: datetime | None = None,
        status: AttendanceStatus,
        source,
        notes: str | None = None,
    ) -> AttendanceRecord:

        employee = self._get_employee(
            tenant_id=tenant_id,
            employee_id=employee_id,
        )

        if employee.employment_status == EmploymentStatus.TERMINATED:
            raise ValueError(
                "Terminated employees cannot receive new attendance records."
            )

        self._validate_check_times(
            check_in=check_in,
            check_out=check_out,
        )

        self._check_duplicate(
            tenant_id=tenant_id,
            employee_id=employee_id,
            attendance_date=attendance_date,
        )

        attendance_record = AttendanceRecord(
            tenant_id=tenant_id,
            employee_id=employee_id,
            attendance_date=attendance_date,
            check_in=check_in,
            check_out=check_out,
            status=status,
            source=source,
            notes=notes,
        )

        self.db.add(attendance_record)
        self.db.flush()

        return attendance_record

    def list_attendance_records(
        self,
        *,
        tenant_id: UUID,
        employee_id: UUID | None = None,
        attendance_date: date | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
        status: AttendanceStatus | None = None,
    ) -> list[AttendanceRecord]:

        query = (
            self.db.query(AttendanceRecord)
            .filter(
                AttendanceRecord.tenant_id == tenant_id,
            )
        )

        if employee_id is not None:
            query = query.filter(
                AttendanceRecord.employee_id == employee_id,
            )

        if attendance_date is not None:
            query = query.filter(
                AttendanceRecord.attendance_date == attendance_date,
            )

        if start_date is not None:
            query = query.filter(
                AttendanceRecord.attendance_date >= start_date,
            )

        if end_date is not None:
            query = query.filter(
                AttendanceRecord.attendance_date <= end_date,
            )

        if status is not None:
            query = query.filter(
                AttendanceRecord.status == status,
            )

        return query.order_by(
            AttendanceRecord.attendance_date.desc(),
            AttendanceRecord.created_at.desc(),
        ).all()


    def get_attendance_record(
        self,
        *,
        tenant_id: UUID,
        record_id: UUID,
    ) -> AttendanceRecord:

        attendance_record = (
            self.db.query(AttendanceRecord)
            .filter(
                AttendanceRecord.id == record_id,
                AttendanceRecord.tenant_id == tenant_id,
            )
            .first()
        )

        if attendance_record is None:
            raise ValueError(
                "Attendance record not found for this tenant."
            )

        return attendance_record



    def update_attendance_record(
        self,
        *,
        tenant_id: UUID,
        record_id: UUID,
        check_in: datetime | None = None,
        check_out: datetime | None = None,
        status: AttendanceStatus | None = None,
        source=None,
        notes: str | None = None,
        update_check_in: bool = False,
        update_check_out: bool = False,
        update_status: bool = False,
        update_source: bool = False,
        update_notes: bool = False,
    ) -> AttendanceRecord:

        attendance_record = self.get_attendance_record(
            tenant_id=tenant_id,
            record_id=record_id,
        )

        employee = self._get_employee(
            tenant_id=tenant_id,
            employee_id=attendance_record.employee_id,
        )

        if employee.employment_status == EmploymentStatus.TERMINATED:
            raise ValueError(
                "Terminated employees cannot have their attendance records updated."
            )

        new_check_in = (
            check_in
            if update_check_in
            else attendance_record.check_in
        )

        new_check_out = (
            check_out
            if update_check_out
            else attendance_record.check_out
        )

        self._validate_check_times(
            check_in=new_check_in,
            check_out=new_check_out,
        )

        if update_check_in:
            attendance_record.check_in = check_in

        if update_check_out:
            attendance_record.check_out = check_out

        if update_status:
            attendance_record.status = status

        if update_source:
            attendance_record.source = source

        if update_notes:
            attendance_record.notes = notes

        self.db.flush()

        return attendance_record
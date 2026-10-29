from uuid import UUID
from datetime import date
from sqlalchemy import or_

from app.hr.enums import EmploymentStatus
from app.hr.models import Employee
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.schedule.enums import ScheduleDay
from app.schedule.models import WorkSchedule, WorkScheduleDay, WorkShift, EmployeeScheduleAssignment


class WorkShiftService:
    """Business logic for tenant-scoped work shifts."""

    def __init__(self, db: Session):
        self.db = db

    def create_work_shift(
        self,
        tenant_id: UUID,
        code: str,
        name: str,
        start_time,
        end_time,
    ) -> WorkShift:
        if start_time == end_time:
            raise ValueError("Work shift start and end times must differ.")

        normalized_code = code.strip()
        normalized_name = name.strip()

        if not normalized_code:
            raise ValueError("Work shift code cannot be blank.")

        if not normalized_name:
            raise ValueError("Work shift name cannot be blank.")

        existing = self.db.scalar(
            select(WorkShift).where(
                WorkShift.tenant_id == tenant_id,
                WorkShift.code == normalized_code,
            )
        )
        if existing is not None:
            raise ValueError(
                f"Work shift code '{normalized_code}' already exists for this tenant."
            )

        work_shift = WorkShift(
            tenant_id=tenant_id,
            code=normalized_code,
            name=normalized_name,
            start_time=start_time,
            end_time=end_time,
        )
        self.db.add(work_shift)
        self.db.flush()

        return work_shift

    def get_work_shift(
        self,
        tenant_id: UUID,
        work_shift_id: UUID,
    ) -> WorkShift:
        work_shift = self.db.scalar(
            select(WorkShift).where(
                WorkShift.tenant_id == tenant_id,
                WorkShift.id == work_shift_id,
            )
        )
        if work_shift is None:
            raise ValueError("Work shift not found.")

        return work_shift

    def list_work_shifts(self, tenant_id: UUID) -> list[WorkShift]:
        statement = (
            select(WorkShift)
            .where(WorkShift.tenant_id == tenant_id)
            .order_by(WorkShift.code, WorkShift.id)
        )
        return list(self.db.scalars(statement).all())


class WorkScheduleService:
    """Business logic for tenant-scoped work schedules."""

    def __init__(self, db: Session):
        self.db = db

    def create_work_schedule(
        self,
        tenant_id: UUID,
        code: str,
        name: str,
        days: list,
    ) -> WorkSchedule:
        normalized_code = code.strip()
        normalized_name = name.strip()

        if not normalized_code:
            raise ValueError("Work schedule code cannot be blank.")

        if not normalized_name:
            raise ValueError("Work schedule name cannot be blank.")

        existing = self.db.scalar(
            select(WorkSchedule).where(
                WorkSchedule.tenant_id == tenant_id,
                WorkSchedule.code == normalized_code,
            )
        )
        if existing is not None:
            raise ValueError(
                f"Work schedule code '{normalized_code}' already exists for this tenant."
            )

        if not days:
            raise ValueError("A work schedule must contain at least one day.")

        seen_days: set[ScheduleDay] = set()
        schedule_days: list[WorkScheduleDay] = []

        for item in days:
            day = item.day
            work_shift_id = item.work_shift_id

            if day in seen_days:
                raise ValueError(
                    f"Day '{day.value}' appears more than once in the work schedule."
                )
            seen_days.add(day)

            work_shift = self.db.scalar(
                select(WorkShift).where(
                    WorkShift.tenant_id == tenant_id,
                    WorkShift.id == work_shift_id,
                )
            )
            if work_shift is None:
                raise ValueError(
                    f"Work shift '{work_shift_id}' not found for this tenant."
                )

            schedule_days.append(
                WorkScheduleDay(
                    tenant_id=tenant_id,
                    day=day,
                    work_shift_id=work_shift.id,
                )
            )

        work_schedule = WorkSchedule(
            tenant_id=tenant_id,
            code=normalized_code,
            name=normalized_name,
            days=schedule_days,
        )

        self.db.add(work_schedule)
        self.db.flush()

        return work_schedule

    def get_work_schedule(
        self,
        tenant_id: UUID,
        work_schedule_id: UUID,
    ) -> WorkSchedule:
        statement = (
            select(WorkSchedule)
            .options(selectinload(WorkSchedule.days))
            .where(
                WorkSchedule.tenant_id == tenant_id,
                WorkSchedule.id == work_schedule_id,
            )
        )
        work_schedule = self.db.scalar(statement)

        if work_schedule is None:
            raise ValueError("Work schedule not found.")

        return work_schedule

    def list_work_schedules(self, tenant_id: UUID) -> list[WorkSchedule]:
        statement = (
            select(WorkSchedule)
            .options(selectinload(WorkSchedule.days))
            .where(WorkSchedule.tenant_id == tenant_id)
            .order_by(WorkSchedule.code, WorkSchedule.id)
        )
        return list(self.db.scalars(statement).all())



class EmployeeScheduleAssignmentService:
    """Manage tenant-scoped employee work schedule assignments."""

    def __init__(self, db: Session):
        self.db = db

    def create_assignment(
        self,
        tenant_id: UUID,
        employee_id: UUID,
        work_schedule_id: UUID,
        effective_from: date,
        effective_to: date | None = None,
    ) -> EmployeeScheduleAssignment:
        if effective_to is not None and effective_to <= effective_from:
            raise ValueError(
                "effective_to must be later than effective_from."
            )

        employee = self.db.scalar(
            select(Employee).where(
                Employee.id == employee_id,
                Employee.tenant_id == tenant_id,
            )
        )

        if employee is None:
            raise ValueError("Employee not found for this tenant.")

        if employee.employment_status == EmploymentStatus.TERMINATED:
            raise ValueError(
                "Terminated employees cannot be assigned a work schedule."
            )

        schedule = self.db.scalar(
            select(WorkSchedule).where(
                WorkSchedule.id == work_schedule_id,
                WorkSchedule.tenant_id == tenant_id,
            )
        )

        if schedule is None:
            raise ValueError("Work schedule not found for this tenant.")

        overlap_conditions = [
            EmployeeScheduleAssignment.tenant_id == tenant_id,
            EmployeeScheduleAssignment.employee_id == employee_id,
            or_(
                EmployeeScheduleAssignment.effective_to.is_(None),
                EmployeeScheduleAssignment.effective_to > effective_from,
            ),
        ]

        if effective_to is not None:
            overlap_conditions.append(
                EmployeeScheduleAssignment.effective_from < effective_to
            )

        overlapping_assignment = self.db.scalar(
            select(EmployeeScheduleAssignment.id)
            .where(*overlap_conditions)
            .limit(1)
        )

        if overlapping_assignment is not None:
            raise ValueError(
                "Employee already has a schedule assignment "
                "overlapping the requested dates."
            )

        assignment = EmployeeScheduleAssignment(
            tenant_id=tenant_id,
            employee_id=employee_id,
            work_schedule_id=work_schedule_id,
            effective_from=effective_from,
            effective_to=effective_to,
        )

        self.db.add(assignment)
        self.db.flush()

        return assignment


    def list_assignments(
        self,
        tenant_id: UUID,
        employee_id: UUID | None = None,
    ) -> list[EmployeeScheduleAssignment]:
        statement = select(EmployeeScheduleAssignment).where(
            EmployeeScheduleAssignment.tenant_id == tenant_id,
        )

        if employee_id is not None:
            statement = statement.where(
                EmployeeScheduleAssignment.employee_id == employee_id,
            )

        statement = statement.order_by(
            EmployeeScheduleAssignment.effective_from.desc(),
            EmployeeScheduleAssignment.id,
        )

        return list(self.db.scalars(statement).all())



class DailyScheduleService:
    """Build a tenant-scoped daily employee schedule overview."""

    def __init__(self, db: Session):
        self.db = db
    def get_effective_employee_schedule(
        self,
        tenant_id: UUID,
        employee_id: UUID,
        on_date: date,
    ) -> dict:
        day = ScheduleDay[on_date.strftime("%A").upper()]

        statement = (
            select(
                Employee,
                EmployeeScheduleAssignment,
                WorkSchedule,
                WorkScheduleDay,
                WorkShift,
            )
            .join(Employee.person)
            .outerjoin(
                EmployeeScheduleAssignment,
                (
                    EmployeeScheduleAssignment.employee_id == Employee.id
                )
                & (
                    EmployeeScheduleAssignment.tenant_id
                    == Employee.tenant_id
                )
                & (
                    EmployeeScheduleAssignment.effective_from <= on_date
                )
                & (
                    EmployeeScheduleAssignment.effective_to.is_(None)
                    | (EmployeeScheduleAssignment.effective_to > on_date)
                ),
            )
            .outerjoin(
                WorkSchedule,
                (
                    WorkSchedule.id
                    == EmployeeScheduleAssignment.work_schedule_id
                )
                & (WorkSchedule.tenant_id == tenant_id),
            )
            .outerjoin(
                WorkScheduleDay,
                (WorkScheduleDay.work_schedule_id == WorkSchedule.id)
                & (WorkScheduleDay.tenant_id == tenant_id)
                & (WorkScheduleDay.day == day),
            )
            .outerjoin(
                WorkShift,
                (WorkShift.id == WorkScheduleDay.work_shift_id)
                & (WorkShift.tenant_id == tenant_id),
            )
            .where(
                Employee.tenant_id == tenant_id,
                Employee.id == employee_id,
                Employee.employment_status != EmploymentStatus.TERMINATED,
            )
        )

        row = self.db.execute(statement).one_or_none()

        if row is None:
            raise ValueError("Employee not found.")

        employee, assignment, schedule, schedule_day, shift = row

        return {
            "employee_id": employee.id,
            "employee_number": employee.employee_number,
            "first_name": employee.person.first_name,
            "last_name": employee.person.last_name,
            "employment_status": employee.employment_status.value,
            "assignment_id": assignment.id if assignment else None,
            "work_schedule_id": schedule.id if schedule else None,
            "work_schedule_code": schedule.code if schedule else None,
            "work_schedule_name": schedule.name if schedule else None,
            "work_shift_id": shift.id if shift else None,
            "work_shift_code": shift.code if shift else None,
            "work_shift_name": shift.name if shift else None,
            "shift_start_time": shift.start_time if shift else None,
            "shift_end_time": shift.end_time if shift else None,
            "on_date": on_date,
            "day": day,
        }
    def get_daily_schedule(
        self,
        tenant_id: UUID,
        on_date: date,
    ) -> dict:
        day = ScheduleDay[
            on_date.strftime("%A").upper()
        ]

        statement = (
            select(
                Employee,
                EmployeeScheduleAssignment,
                WorkSchedule,
                WorkScheduleDay,
                WorkShift,
            )
            .join(
                Employee.person,
            )
            .outerjoin(
                EmployeeScheduleAssignment,
                (
                    EmployeeScheduleAssignment.employee_id == Employee.id
                )
                & (
                    EmployeeScheduleAssignment.tenant_id
                    == Employee.tenant_id
                )
                & (
                    EmployeeScheduleAssignment.effective_from <= on_date
                )
                & (
                    (EmployeeScheduleAssignment.effective_to.is_(None))
                    | (EmployeeScheduleAssignment.effective_to > on_date)
                ),
            )
            .outerjoin(
                WorkSchedule,
                (
                    WorkSchedule.id
                    == EmployeeScheduleAssignment.work_schedule_id
                )
                & (WorkSchedule.tenant_id == tenant_id),
            )
            .outerjoin(
                WorkScheduleDay,
                (
                    WorkScheduleDay.work_schedule_id == WorkSchedule.id
                )
                & (WorkScheduleDay.tenant_id == tenant_id)
                & (WorkScheduleDay.day == day),
            )
            .outerjoin(
                WorkShift,
                (
                    WorkShift.id == WorkScheduleDay.work_shift_id
                )
                & (WorkShift.tenant_id == tenant_id),
            )
            .where(
                Employee.tenant_id == tenant_id,
                Employee.employment_status != EmploymentStatus.TERMINATED,
            )
            .order_by(Employee.employee_number)
        )

        rows = self.db.execute(statement).all()

        employees = []
        for employee, assignment, schedule, schedule_day, shift in rows:
            employees.append(
                {
                    "employee_id": employee.id,
                    "employee_number": employee.employee_number,
                    "first_name": employee.person.first_name,
                    "last_name": employee.person.last_name,
                    "employment_status": employee.employment_status.value,
                    "assignment_id": assignment.id if assignment else None,
                    "work_schedule_id": schedule.id if schedule else None,
                    "work_schedule_code": schedule.code if schedule else None,
                    "work_schedule_name": schedule.name if schedule else None,
                    "work_shift_id": shift.id if shift else None,
                    "work_shift_code": shift.code if shift else None,
                    "work_shift_name": shift.name if shift else None,
                    "shift_start_time": shift.start_time if shift else None,
                    "shift_end_time": shift.end_time if shift else None,
                }
            )

        return {
            "on_date": on_date,
            "day": day,
            "employees": employees,
        }

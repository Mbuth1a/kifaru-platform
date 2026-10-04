from __future__ import annotations

from datetime import date
from uuid import UUID

from sqlalchemy.orm import Session

from app.hr.enums import EmploymentStatus
from app.hr.models import Employee

from .enums import LeaveRequestStatus
from .models import LeaveRequest, LeaveType


class LeaveService:
    """
    Application/service layer for Leave Management.

    Responsibilities:
    - Enforce tenant isolation
    - Validate employee ownership
    - Prevent leave for terminated employees
    - Validate leave type ownership and status
    - Calculate inclusive requested days
    - Prevent overlapping active leave requests
    - Create leave requests in PENDING status

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

    def _get_leave_type(
        self,
        *,
        tenant_id: UUID,
        leave_type_id: UUID,
    ) -> LeaveType:

        leave_type = (
            self.db.query(LeaveType)
            .filter(
                LeaveType.id == leave_type_id,
                LeaveType.tenant_id == tenant_id,
            )
            .first()
        )

        if leave_type is None:
            raise ValueError(
                "Leave type not found for this tenant."
            )

        if not leave_type.active:
            raise ValueError(
                "Leave type is inactive."
            )

        return leave_type

    def _validate_dates(
        self,
        *,
        start_date: date,
        end_date: date,
    ) -> None:

        if end_date < start_date:
            raise ValueError(
                "end_date must be on or after start_date."
            )

    def _calculate_requested_days(
        self,
        *,
        start_date: date,
        end_date: date,
    ) -> int:

        return (end_date - start_date).days + 1

    def _check_overlap(
        self,
        *,
        tenant_id: UUID,
        employee_id: UUID,
        start_date: date,
        end_date: date,
    ) -> None:

        overlapping_request = (
            self.db.query(LeaveRequest)
            .filter(
                LeaveRequest.tenant_id == tenant_id,
                LeaveRequest.employee_id == employee_id,
                LeaveRequest.status.in_(
                    [
                        LeaveRequestStatus.PENDING,
                        LeaveRequestStatus.APPROVED,
                    ]
                ),
                LeaveRequest.start_date <= end_date,
                LeaveRequest.end_date >= start_date,
            )
            .first()
        )

        if overlapping_request is not None:
            raise ValueError(
                "Leave request overlaps an existing pending or approved leave request."
            )



    def create_leave_type(
        self,
        *,
        tenant_id: UUID,
        code: str,
        name: str,
        description: str | None = None,
        active: bool = True,
    ) -> LeaveType:

        existing_type = (
            self.db.query(LeaveType)
            .filter(
                LeaveType.tenant_id == tenant_id,
                (
                    (LeaveType.code == code)
                    | (LeaveType.name == name)
                ),
            )
            .first()
        )

        if existing_type is not None:
            if existing_type.code == code:
                raise ValueError(
                    "Leave type code already exists for this tenant."
                )

            raise ValueError(
                "Leave type name already exists for this tenant."
            )

        leave_type = LeaveType(
            tenant_id=tenant_id,
            code=code,
            name=name,
            description=description,
            active=active,
        )

        self.db.add(leave_type)
        self.db.flush()

        return leave_type   


    def get_leave_type(
        self,
        *,
        tenant_id: UUID,
        leave_type_id: UUID,
    ) -> LeaveType:

        leave_type = (
            self.db.query(LeaveType)
            .filter(
                LeaveType.id == leave_type_id,
                LeaveType.tenant_id == tenant_id,
            )
            .first()
        )

        if leave_type is None:
            raise ValueError(
                "Leave type not found for this tenant."
            )

        return leave_type




    def get_leave_request(
        self,
        *,
        tenant_id: UUID,
        leave_request_id: UUID,
    ) -> LeaveRequest:

        leave_request = (
            self.db.query(LeaveRequest)
            .filter(
                LeaveRequest.id == leave_request_id,
                LeaveRequest.tenant_id == tenant_id,
            )
            .first()
        )

        if leave_request is None:
            raise ValueError(
                "Leave request not found for this tenant."
            )

        return leave_request
    def list_leave_requests(
        self,
        *,
        tenant_id: UUID,
        employee_id: UUID | None = None,
        status: LeaveRequestStatus | None = None,
    ) -> list[LeaveRequest]:

        query = (
            self.db.query(LeaveRequest)
            .filter(
                LeaveRequest.tenant_id == tenant_id,
            )
        )

        if employee_id is not None:
            query = query.filter(
                LeaveRequest.employee_id == employee_id,
            )

        if status is not None:
            query = query.filter(
                LeaveRequest.status == status,
            )

        return (
            query
            .order_by(LeaveRequest.created_at.desc())
            .all()
        )


    

    def create_leave_request(
        self,
        *,
        tenant_id: UUID,
        employee_id: UUID,
        leave_type_id: UUID,
        start_date: date,
        end_date: date,
        reason: str | None = None,
    ) -> LeaveRequest:

        employee = self._get_employee(
            tenant_id=tenant_id,
            employee_id=employee_id,
        )

        if employee.employment_status == EmploymentStatus.TERMINATED:
            raise ValueError(
                "Terminated employees cannot create new leave requests."
            )

        self._get_leave_type(
            tenant_id=tenant_id,
            leave_type_id=leave_type_id,
        )

        self._validate_dates(
            start_date=start_date,
            end_date=end_date,
        )

        requested_days = self._calculate_requested_days(
            start_date=start_date,
            end_date=end_date,
        )

        self._check_overlap(
            tenant_id=tenant_id,
            employee_id=employee_id,
            start_date=start_date,
            end_date=end_date,
        )

        leave_request = LeaveRequest(
            tenant_id=tenant_id,
            employee_id=employee_id,
            leave_type_id=leave_type_id,
            start_date=start_date,
            end_date=end_date,
            requested_days=requested_days,
            reason=reason,
            status=LeaveRequestStatus.PENDING,
        )

        self.db.add(leave_request)
        self.db.flush()

        return leave_request


    def transition_leave_request(
    self,
    *,
    tenant_id: UUID,
    leave_request_id: UUID,
    new_status: LeaveRequestStatus,
    ) -> LeaveRequest:

        leave_request = (
            self.db.query(LeaveRequest)
            .filter(
                LeaveRequest.id == leave_request_id,
                LeaveRequest.tenant_id == tenant_id,
            )
            .first()
        )

        if leave_request is None:
            raise ValueError(
                "Leave request not found for this tenant."
            )

        current_status = leave_request.status

        allowed_transitions = {
            LeaveRequestStatus.PENDING: {
                LeaveRequestStatus.APPROVED,
                LeaveRequestStatus.REJECTED,
                LeaveRequestStatus.CANCELLED,
            },
            LeaveRequestStatus.APPROVED: {
                LeaveRequestStatus.CANCELLED,
            },
            LeaveRequestStatus.REJECTED: set(),
            LeaveRequestStatus.CANCELLED: set(),
        }

        if new_status not in allowed_transitions[current_status]:
            raise ValueError(
                f"Invalid leave request status transition: "
                f"{current_status.value} -> {new_status.value}."
            )

        leave_request.status = new_status

        self.db.flush()

        return leave_request
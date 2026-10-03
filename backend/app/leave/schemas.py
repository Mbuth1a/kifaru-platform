from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


from app.leave.enums import (
    LeaveRequestStatus
)

class LeaveTypeCreate(BaseModel):
    code: str = Field(min_length=1, max_length=50)
    name: str = Field(min_length=1, max_length=150)
    description: str | None = Field(
        default=None,
        max_length=500,
    )
    active: bool = True


class LeaveTypeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    code: str
    name: str
    description: str | None
    active: bool
    created_at: datetime
    updated_at: datetime


class LeaveRequestCreate(BaseModel):
    employee_id: UUID
    leave_type_id: UUID
    start_date: date
    end_date: date
    reason: str | None = Field(
        default=None,
        max_length=1000,
    )


class LeaveRequestResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    employee_id: UUID
    leave_type_id: UUID
    start_date: date
    end_date: date
    requested_days: int
    reason: str | None
    status: LeaveRequestStatus
    created_at: datetime
    updated_at: datetime


class LeaveRequestStatusTransitionCreate(BaseModel):
    status: LeaveRequestStatus
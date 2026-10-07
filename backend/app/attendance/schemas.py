from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.attendance.enums import AttendanceSource, AttendanceStatus


class AttendanceRecordCreate(BaseModel):
    employee_id: UUID
    attendance_date: date
    check_in: datetime | None = None
    check_out: datetime | None = None
    status: AttendanceStatus
    source: AttendanceSource
    notes: str | None = Field(
        default=None,
        max_length=1000,
    )


class AttendanceRecordResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    employee_id: UUID
    attendance_date: date
    check_in: datetime | None
    check_out: datetime | None
    status: AttendanceStatus
    source: AttendanceSource
    notes: str | None
    created_at: datetime
    updated_at: datetime


class AttendanceRecordListResponse(BaseModel):
    items: list[AttendanceRecordResponse]
    total: int



class AttendanceRecordUpdate(BaseModel):
    check_in: datetime | None = None
    check_out: datetime | None = None
    status: AttendanceStatus | None = None
    source: AttendanceSource | None = None
    notes: str | None = Field(
        default=None,
        max_length=1000,
    )

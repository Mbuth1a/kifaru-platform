
from datetime import date, datetime, time
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.schedule.enums import ScheduleDay


class WorkShiftCreate(BaseModel):
    code: str = Field(min_length=1, max_length=100)
    name: str = Field(min_length=1, max_length=255)
    start_time: time
    end_time: time


class WorkShiftResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    code: str
    name: str
    start_time: time
    end_time: time
    created_at: datetime
    updated_at: datetime


class WorkScheduleDayCreate(BaseModel):
    day: ScheduleDay
    work_shift_id: UUID


class WorkScheduleCreate(BaseModel):
    code: str = Field(min_length=1, max_length=100)
    name: str = Field(min_length=1, max_length=255)
    days: list[WorkScheduleDayCreate] = Field(min_length=1)


class WorkScheduleDayResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    work_schedule_id: UUID
    day: ScheduleDay
    work_shift_id: UUID
    created_at: datetime
    updated_at: datetime


class WorkScheduleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    code: str
    name: str
    days: list[WorkScheduleDayResponse]
    created_at: datetime
    updated_at: datetime




class EmployeeScheduleAssignmentCreate(BaseModel):
    employee_id: UUID
    work_schedule_id: UUID
    effective_from: date
    effective_to: date | None = None


class EmployeeScheduleAssignmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    employee_id: UUID
    work_schedule_id: UUID
    effective_from: date
    effective_to: date | None
    created_at: datetime
    updated_at: datetime


class DailyScheduleEmployeeResponse(BaseModel):
    employee_id: UUID
    employee_number: str
    first_name: str
    last_name: str
    employment_status: str

    assignment_id: UUID | None
    work_schedule_id: UUID | None
    work_schedule_code: str | None
    work_schedule_name: str | None

    work_shift_id: UUID | None
    work_shift_code: str | None
    work_shift_name: str | None
    shift_start_time: time | None
    shift_end_time: time | None


class DailyScheduleResponse(BaseModel):
    on_date: date
    day: ScheduleDay
    employees: list[DailyScheduleEmployeeResponse]



class EffectiveEmployeeScheduleResponse(DailyScheduleEmployeeResponse):
    on_date: date
    day: ScheduleDay
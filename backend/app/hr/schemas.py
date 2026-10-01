from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from .enums import EmploymentStatus, EmploymentType, Gender


class PersonCreate(BaseModel):
    person_number: str = Field(min_length=1, max_length=50)
    first_name: str = Field(min_length=1, max_length=100)
    middle_name: str | None = Field(default=None, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)
    preferred_name: str | None = Field(default=None, max_length=100)
    date_of_birth: date | None = None
    gender: Gender | None = None
    nationality_code: str | None = Field(
        default=None,
        min_length=2,
        max_length=2,
    )
    national_id_number: str | None = Field(
        default=None,
        max_length=100,
    )
    tax_identifier: str | None = Field(
        default=None,
        max_length=100,
    )


class PersonResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    person_number: str
    first_name: str
    middle_name: str | None
    last_name: str
    preferred_name: str | None
    date_of_birth: date | None
    gender: Gender | None
    nationality_code: str | None
    national_id_number: str | None
    tax_identifier: str | None
    created_at: datetime
    updated_at: datetime


class EmployeeCreate(BaseModel):
    person_id: UUID
    employee_number: str = Field(min_length=1, max_length=50)
    employment_status: EmploymentStatus
    employment_type: EmploymentType
    hire_date: date
    termination_date: date | None = None
    termination_reason: str | None = Field(
        default=None,
        max_length=255,
    )


class EmployeeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    person_id: UUID
    employee_number: str
    employment_status: EmploymentStatus
    employment_type: EmploymentType
    hire_date: date
    termination_date: date | None
    termination_reason: str | None
    created_at: datetime
    updated_at: datetime


class EmploymentAssignmentCreate(BaseModel):
    employee_id: UUID
    organization_unit_id: UUID
    job_title: str = Field(min_length=1, max_length=150)
    manager_employee_id: UUID | None = None
    effective_from: datetime
    effective_to: datetime | None = None


class EmploymentAssignmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    employee_id: UUID
    organization_unit_id: UUID
    job_title: str
    manager_employee_id: UUID | None
    effective_from: datetime
    effective_to: datetime | None
    created_at: datetime
    updated_at: datetime
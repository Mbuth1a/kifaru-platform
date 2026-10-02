from datetime import date, datetime
from uuid import UUID
from decimal import Decimal
from pydantic import BaseModel, ConfigDict, Field


from app.hr.enums import (
    CompensationBasis,
    EmploymentStatus,
    EmploymentType,
    Gender,
    PayFrequency,
)

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




class EmploymentTermCreate(BaseModel):
    employee_id: UUID
    effective_from: datetime
    effective_to: datetime | None = None
    pay_frequency: PayFrequency
    compensation_basis: CompensationBasis
    currency_code: str = Field(min_length=3, max_length=3)
    amount: Decimal = Field(gt=0, max_digits=18, decimal_places=2)


class EmploymentTermResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    employee_id: UUID
    effective_from: datetime
    effective_to: datetime | None
    pay_frequency: PayFrequency
    compensation_basis: CompensationBasis
    currency_code: str
    amount: Decimal
    created_at: datetime
    updated_at: datetime


class EmploymentStatusHistoryCreate(BaseModel):
    employee_id: UUID
    status: EmploymentStatus
    effective_from: datetime
    effective_to: datetime | None = None
    reason: str | None = Field(default=None, max_length=255)


class EmploymentStatusHistoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    employee_id: UUID
    status: EmploymentStatus
    effective_from: datetime
    effective_to: datetime | None
    reason: str | None
    created_at: datetime
    updated_at: datetime


class EmploymentStatusTransitionCreate(BaseModel):
    status: EmploymentStatus
    effective_from: datetime
    reason: str | None = Field(
        default=None,
        max_length=255,
    )
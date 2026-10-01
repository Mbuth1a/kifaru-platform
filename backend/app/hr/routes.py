from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_db
from app.hr.schemas import (
    EmployeeCreate,
    EmployeeResponse,
    EmploymentAssignmentCreate,
    EmploymentAssignmentResponse,
    PersonCreate,
    PersonResponse,
)
from app.hr.service import (
    EmployeeService,
    EmploymentAssignmentService,
    PersonService,
)

router = APIRouter(
    prefix="/hr",
    tags=["HR"],
)


def get_tenant_id(x_tenant_id: UUID = Header(...)) -> UUID:
    return x_tenant_id


@router.post(
    "/persons",
    response_model=PersonResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_person(
    payload: PersonCreate,
    tenant_id: UUID = Depends(get_tenant_id),
    db: Session = Depends(get_db),
):
    try:
        return PersonService(db).create_person(
            tenant_id=tenant_id,
            person_number=payload.person_number,
            first_name=payload.first_name,
            middle_name=payload.middle_name,
            last_name=payload.last_name,
            preferred_name=payload.preferred_name,
            date_of_birth=payload.date_of_birth,
            gender=payload.gender,
            nationality_code=payload.nationality_code,
            national_id_number=payload.national_id_number,
            tax_identifier=payload.tax_identifier,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.get(
    "/persons/{person_id}",
    response_model=PersonResponse,
)
def get_person(
    person_id: UUID,
    tenant_id: UUID = Depends(get_tenant_id),
    db: Session = Depends(get_db),
):
    try:
        return PersonService(db).get_person(
            tenant_id=tenant_id,
            person_id=person_id,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc


@router.post(
    "/employees",
    response_model=EmployeeResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_employee(
    payload: EmployeeCreate,
    tenant_id: UUID = Depends(get_tenant_id),
    db: Session = Depends(get_db),
):
    try:
       return EmployeeService(db).create_employee(
            tenant_id=tenant_id,
            person_id=payload.person_id,
            employee_number=payload.employee_number,
            employment_status=payload.employment_status,
            employment_type=payload.employment_type,
            hire_date=payload.hire_date,
            termination_date=payload.termination_date,
            termination_reason=payload.termination_reason,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.get(
    "/employees/{employee_id}",
    response_model=EmployeeResponse,
)
def get_employee(
    employee_id: UUID,
    tenant_id: UUID = Depends(get_tenant_id),
    db: Session = Depends(get_db),
):
    try:
        return EmployeeService(db).get_employee(
            tenant_id=tenant_id,
            employee_id=employee_id,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc


@router.post(
    "/employment-assignments",
    response_model=EmploymentAssignmentResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_employment_assignment(
    payload: EmploymentAssignmentCreate,
    tenant_id: UUID = Depends(get_tenant_id),
    db: Session = Depends(get_db),
):
    try:
        return EmploymentAssignmentService(db).create_assignment(
            tenant_id=tenant_id,
            employee_id=payload.employee_id,
            organization_unit_id=payload.organization_unit_id,
            job_title=payload.job_title,
            effective_from=payload.effective_from,
            effective_to=payload.effective_to,
            manager_employee_id=payload.manager_employee_id,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.get(
    "/employment-assignments/{assignment_id}",
    response_model=EmploymentAssignmentResponse,
)
def get_employment_assignment(
    assignment_id: UUID,
    tenant_id: UUID = Depends(get_tenant_id),
    db: Session = Depends(get_db),
):
    try:
        return EmploymentAssignmentService(db).get_assignment(
            tenant_id=tenant_id,
            assignment_id=assignment_id,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc


@router.get(
    "/employees/{employee_id}/assignment/current",
    response_model=EmploymentAssignmentResponse | None,
)
def get_current_assignment(
    employee_id: UUID,
    tenant_id: UUID = Depends(get_tenant_id),
    db: Session = Depends(get_db),
):
    try:
        return EmploymentAssignmentService(db).get_current_assignment(
            tenant_id=tenant_id,
            employee_id=employee_id,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc


@router.get(
    "/employees/{employee_id}/assignment/history",
    response_model=list[EmploymentAssignmentResponse],
)
def get_assignment_history(
    employee_id: UUID,
    tenant_id: UUID = Depends(get_tenant_id),
    db: Session = Depends(get_db),
):
    try:
        return EmploymentAssignmentService(db).get_assignment_history(
            tenant_id=tenant_id,
            employee_id=employee_id,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
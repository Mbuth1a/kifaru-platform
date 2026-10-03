from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_db, get_tenant_id

from app.hr.schemas import (
    EmployeeCreate,
    EmployeeResponse,
    EmploymentAssignmentCreate,
    EmploymentAssignmentResponse,
    EmploymentStatusHistoryResponse,
    EmploymentStatusTransitionCreate,
    EmploymentTermCreate,
    EmploymentTermResponse,
    PersonCreate,
    PersonResponse,
)


from app.hr.service import (
    EmployeeService,
    EmploymentAssignmentService,
    EmploymentStatusHistoryService,
    EmploymentTermService,
    PersonService,
)

router = APIRouter(
    prefix="/hr",
    tags=["HR"],
)




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
        person = PersonService(db).create_person(
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

        db.commit()

        return person

    except ValueError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    except Exception:
        db.rollback()
        raise

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
        employee = EmployeeService(db).create_employee(
            tenant_id=tenant_id,
            person_id=payload.person_id,
            employee_number=payload.employee_number,
            employment_status=payload.employment_status,
            employment_type=payload.employment_type,
            hire_date=payload.hire_date,
            termination_date=payload.termination_date,
            termination_reason=payload.termination_reason,
        )

        db.commit()

        return employee

    except ValueError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    except Exception:
        db.rollback()
        raise

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
        assignment = EmploymentAssignmentService(db).create_assignment(
            tenant_id=tenant_id,
            employee_id=payload.employee_id,
            organization_unit_id=payload.organization_unit_id,
            job_title=payload.job_title,
            effective_from=payload.effective_from,
            effective_to=payload.effective_to,
            manager_employee_id=payload.manager_employee_id,
        )

        db.commit()

        return assignment

    except ValueError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    except Exception:
        db.rollback()
        raise
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




@router.post(
    "/employment-terms",
    response_model=EmploymentTermResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_employment_term(
    payload: EmploymentTermCreate,
    tenant_id: UUID = Depends(get_tenant_id),
    db: Session = Depends(get_db),
):
    try:
        term = EmploymentTermService(db).create_term(
            tenant_id=tenant_id,
            employee_id=payload.employee_id,
            effective_from=payload.effective_from,
            effective_to=payload.effective_to,
            pay_frequency=payload.pay_frequency,
            compensation_basis=payload.compensation_basis,
            currency_code=payload.currency_code,
            amount=payload.amount,
        )

        db.commit()

        return term

    except ValueError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    except Exception:
        db.rollback()
        raise


@router.get(
    "/employment-terms/{term_id}",
    response_model=EmploymentTermResponse,
)
def get_employment_term(
    term_id: UUID,
    tenant_id: UUID = Depends(get_tenant_id),
    db: Session = Depends(get_db),
):
    try:
        return EmploymentTermService(db).get_term(
            tenant_id=tenant_id,
            term_id=term_id,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc


@router.get(
    "/employees/{employee_id}/term/current",
    response_model=EmploymentTermResponse | None,
)
def get_current_employment_term(
    employee_id: UUID,
    tenant_id: UUID = Depends(get_tenant_id),
    db: Session = Depends(get_db),
):
    try:
        return EmploymentTermService(db).get_current_term(
            tenant_id=tenant_id,
            employee_id=employee_id,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc


@router.get(
    "/employees/{employee_id}/term/history",
    response_model=list[EmploymentTermResponse],
)
def get_employment_term_history(
    employee_id: UUID,
    tenant_id: UUID = Depends(get_tenant_id),
    db: Session = Depends(get_db),
):
    try:
        return EmploymentTermService(db).get_term_history(
            tenant_id=tenant_id,
            employee_id=employee_id,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc



@router.post(
    "/employees/{employee_id}/status",
    response_model=EmploymentStatusHistoryResponse,
    status_code=status.HTTP_201_CREATED,
)
def transition_employee_status(
    employee_id: UUID,
    payload: EmploymentStatusTransitionCreate,
    tenant_id: UUID = Depends(get_tenant_id),
    db: Session = Depends(get_db),
):
    try:
        history = EmploymentStatusHistoryService(db).transition_status(
            tenant_id=tenant_id,
            employee_id=employee_id,
            status=payload.status,
            effective_from=payload.effective_from,
            reason=payload.reason,
        )

        db.commit()

        return history

    except ValueError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    except Exception:
        db.rollback()
        raise


@router.get(
    "/employees/{employee_id}/status/current",
    response_model=EmploymentStatusHistoryResponse | None,
)
def get_current_employee_status(
    employee_id: UUID,
    tenant_id: UUID = Depends(get_tenant_id),
    db: Session = Depends(get_db),
):
    try:
        return EmploymentStatusHistoryService(db).get_current_status(
            tenant_id=tenant_id,
            employee_id=employee_id,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc


@router.get(
    "/employees/{employee_id}/status/history",
    response_model=list[EmploymentStatusHistoryResponse],
)
def get_employee_status_history(
    employee_id: UUID,
    tenant_id: UUID = Depends(get_tenant_id),
    db: Session = Depends(get_db),
):
    try:
        return EmploymentStatusHistoryService(db).get_status_history(
            tenant_id=tenant_id,
            employee_id=employee_id,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
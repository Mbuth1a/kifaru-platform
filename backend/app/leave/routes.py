from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from fastapi import APIRouter, Depends, HTTPException, Query, status
from app.core.dependencies import get_db, get_tenant_id
from app.leave.enums import LeaveRequestStatus
from app.leave.schemas import (
    LeaveRequestCreate,
    LeaveRequestResponse,
    LeaveRequestStatusTransitionCreate,
    LeaveTypeCreate,
    LeaveTypeResponse,
)

from .service import LeaveService


router = APIRouter(
    prefix="/leave",
    tags=["Leave"],
)



@router.post(
    "/types",
    response_model=LeaveTypeResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_leave_type(
    payload: LeaveTypeCreate,
    tenant_id: UUID = Depends(get_tenant_id),
    db: Session = Depends(get_db),
):
    try:
        leave_type = LeaveService(db).create_leave_type(
            tenant_id=tenant_id,
            code=payload.code,
            name=payload.name,
            description=payload.description,
            active=payload.active,
        )

        db.commit()

        return leave_type

    except ValueError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    except Exception:
        db.rollback()
        raise




@router.post(
    "/requests",
    response_model=LeaveRequestResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_leave_request(
    payload: LeaveRequestCreate,
    tenant_id: UUID = Depends(get_tenant_id),
    db: Session = Depends(get_db),
):
    try:
        leave_request = LeaveService(db).create_leave_request(
            tenant_id=tenant_id,
            employee_id=payload.employee_id,
            leave_type_id=payload.leave_type_id,
            start_date=payload.start_date,
            end_date=payload.end_date,
            reason=payload.reason,
        )

        db.commit()

        return leave_request

    except ValueError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    except Exception:
        db.rollback()
        raise



@router.post(
    "/requests/{leave_request_id}/status",
    response_model=LeaveRequestResponse,
    status_code=status.HTTP_200_OK,
)
def transition_leave_request_status(
    leave_request_id: UUID,
    payload: LeaveRequestStatusTransitionCreate,
    tenant_id: UUID = Depends(get_tenant_id),
    db: Session = Depends(get_db),
):
    try:
        leave_request = LeaveService(db).transition_leave_request(
            tenant_id=tenant_id,
            leave_request_id=leave_request_id,
            new_status=payload.status,
        )

        db.commit()

        return leave_request

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
    "/types/{leave_type_id}",
    response_model=LeaveTypeResponse,
    status_code=status.HTTP_200_OK,
)
def get_leave_type(
    leave_type_id: UUID,
    tenant_id: UUID = Depends(get_tenant_id),
    db: Session = Depends(get_db),
):
    try:
        return LeaveService(db).get_leave_type(
            tenant_id=tenant_id,
            leave_type_id=leave_type_id,
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    

@router.get(
    "/requests",
    response_model=list[LeaveRequestResponse],
    status_code=status.HTTP_200_OK,
)
def list_leave_requests(
    employee_id: UUID | None = None,
    status_filter: LeaveRequestStatus | None = Query(
        default=None,
        alias="status",
    ),
    tenant_id: UUID = Depends(get_tenant_id),
    db: Session = Depends(get_db),
):
    return LeaveService(db).list_leave_requests(
        tenant_id=tenant_id,
        employee_id=employee_id,
        status=status_filter,
    )




@router.get(
    "/requests/{leave_request_id}",
    response_model=LeaveRequestResponse,
    status_code=status.HTTP_200_OK,
)
def get_leave_request(
    leave_request_id: UUID,
    tenant_id: UUID = Depends(get_tenant_id),
    db: Session = Depends(get_db),
):
    try:
        return LeaveService(db).get_leave_request(
            tenant_id=tenant_id,
            leave_request_id=leave_request_id,
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
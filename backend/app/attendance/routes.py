from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import date

from app.attendance.enums import AttendanceStatus
from app.core.dependencies import get_db, get_tenant_id

from .schemas import (
    AttendanceRecordCreate,
    AttendanceRecordListResponse,
    AttendanceRecordResponse,
    AttendanceRecordUpdate,
)
from .service import AttendanceService


router = APIRouter(
    prefix="/attendance",
    tags=["Attendance"],
)


@router.post(
    "/records",
    response_model=AttendanceRecordResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_attendance_record(
    payload: AttendanceRecordCreate,
    tenant_id: UUID = Depends(get_tenant_id),
    db: Session = Depends(get_db),
):
    service = AttendanceService(db)

    try:
        attendance_record = service.create_attendance_record(
            tenant_id=tenant_id,
            employee_id=payload.employee_id,
            attendance_date=payload.attendance_date,
            check_in=payload.check_in,
            check_out=payload.check_out,
            status=payload.status,
            source=payload.source,
            notes=payload.notes,
        )

        db.commit()

        return attendance_record

    except ValueError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )

    except Exception:
        db.rollback()
        raise




@router.get(
    "/records",
    response_model=AttendanceRecordListResponse,
    status_code=status.HTTP_200_OK,
)
def list_attendance_records(
    employee_id: UUID | None = None,
    attendance_date: date | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
    attendance_status: AttendanceStatus | None = None,
    tenant_id: UUID = Depends(get_tenant_id),
    db: Session = Depends(get_db),
):
    service = AttendanceService(db)

    records = service.list_attendance_records(
        tenant_id=tenant_id,
        employee_id=employee_id,
        attendance_date=attendance_date,
        start_date=start_date,
        end_date=end_date,
        status=attendance_status,
    )

    return {
        "items": records,
        "total": len(records),
    }


@router.patch(
    "/records/{record_id}",
    response_model=AttendanceRecordResponse,
    status_code=status.HTTP_200_OK,
)
def update_attendance_record(
    record_id: UUID,
    payload: AttendanceRecordUpdate,
    tenant_id: UUID = Depends(get_tenant_id),
    db: Session = Depends(get_db),
):
    service = AttendanceService(db)

    try:
        attendance_record = service.update_attendance_record(
            tenant_id=tenant_id,
            record_id=record_id,
            check_in=payload.check_in,
            check_out=payload.check_out,
            status=payload.status,
            source=payload.source,
            notes=payload.notes,
            update_check_in="check_in" in payload.model_fields_set,
            update_check_out="check_out" in payload.model_fields_set,
            update_status="status" in payload.model_fields_set,
            update_source="source" in payload.model_fields_set,
            update_notes="notes" in payload.model_fields_set,
        )

        db.commit()

        return attendance_record

    except ValueError as exc:
        db.rollback()

        if str(exc) == "Attendance record not found for this tenant.":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(exc),
            )

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )

    except Exception:
        db.rollback()
        raise

@router.get(
    "/records/{record_id}",
    response_model=AttendanceRecordResponse,
    status_code=status.HTTP_200_OK,
)
def get_attendance_record(
    record_id: UUID,
    tenant_id: UUID = Depends(get_tenant_id),
    db: Session = Depends(get_db),
):
    service = AttendanceService(db)

    try:
        return service.get_attendance_record(
            tenant_id=tenant_id,
            record_id=record_id,
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        )

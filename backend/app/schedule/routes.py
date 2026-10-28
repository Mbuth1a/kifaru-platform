from datetime import date
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, status

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.dependencies import get_db, get_tenant_id
from app.schedule.schemas import (
    WorkScheduleCreate,
    WorkScheduleResponse,
    WorkShiftCreate,
    WorkShiftResponse,
    EmployeeScheduleAssignmentCreate,
    EmployeeScheduleAssignmentResponse,
    DailyScheduleEmployeeResponse,
    DailyScheduleResponse,
)
from app.schedule.service import (
    DailyScheduleService,
    EmployeeScheduleAssignmentService,
    WorkScheduleService,
    WorkShiftService,
)

router = APIRouter(
    prefix="/schedule",
    tags=["Schedule"],
)


@router.post(
    "/work-shifts",
    response_model=WorkShiftResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_work_shift(
    payload: WorkShiftCreate,
    tenant_id: UUID = Depends(get_tenant_id),
    db: Session = Depends(get_db),
):
    try:
        work_shift = WorkShiftService(db).create_work_shift(
            tenant_id=tenant_id,
            code=payload.code,
            name=payload.name,
            start_time=payload.start_time,
            end_time=payload.end_time,
        )
        db.commit()
        db.refresh(work_shift)
        return work_shift

    except ValueError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A work shift with this code already exists for this tenant.",
        ) from exc

    except Exception:
        db.rollback()
        raise


@router.get(
    "/work-shifts",
    response_model=list[WorkShiftResponse],
    status_code=status.HTTP_200_OK,
)
def list_work_shifts(
    tenant_id: UUID = Depends(get_tenant_id),
    db: Session = Depends(get_db),
):
    return WorkShiftService(db).list_work_shifts(tenant_id=tenant_id)


@router.get(
    "/work-shifts/{work_shift_id}",
    response_model=WorkShiftResponse,
    status_code=status.HTTP_200_OK,
)
def get_work_shift(
    work_shift_id: UUID,
    tenant_id: UUID = Depends(get_tenant_id),
    db: Session = Depends(get_db),
):
    try:
        return WorkShiftService(db).get_work_shift(
            tenant_id=tenant_id,
            work_shift_id=work_shift_id,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc


@router.post(
    "/work-schedules",
    response_model=WorkScheduleResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_work_schedule(
    payload: WorkScheduleCreate,
    tenant_id: UUID = Depends(get_tenant_id),
    db: Session = Depends(get_db),
):
    try:
        work_schedule = WorkScheduleService(db).create_work_schedule(
            tenant_id=tenant_id,
            code=payload.code,
            name=payload.name,
            days=payload.days,
        )
        db.commit()
        db.refresh(work_schedule)
        return WorkScheduleService(db).get_work_schedule(
            tenant_id=tenant_id,
            work_schedule_id=work_schedule.id,
        )

    except ValueError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="The work schedule conflicts with an existing database constraint.",
        ) from exc

    except Exception:
        db.rollback()
        raise


@router.get(
    "/work-schedules",
    response_model=list[WorkScheduleResponse],
    status_code=status.HTTP_200_OK,
)
def list_work_schedules(
    tenant_id: UUID = Depends(get_tenant_id),
    db: Session = Depends(get_db),
):
    return WorkScheduleService(db).list_work_schedules(tenant_id=tenant_id)


@router.get(
    "/work-schedules/{work_schedule_id}",
    response_model=WorkScheduleResponse,
    status_code=status.HTTP_200_OK,
)
def get_work_schedule(
    work_schedule_id: UUID,
    tenant_id: UUID = Depends(get_tenant_id),
    db: Session = Depends(get_db),
):
    try:
        return WorkScheduleService(db).get_work_schedule(
            tenant_id=tenant_id,
            work_schedule_id=work_schedule_id,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc



@router.post(
    "/assignments",
    response_model=EmployeeScheduleAssignmentResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_schedule_assignment(
    payload: EmployeeScheduleAssignmentCreate,
    tenant_id: UUID = Depends(get_tenant_id),
    db: Session = Depends(get_db),
):
    try:
        assignment = EmployeeScheduleAssignmentService(db).create_assignment(
            tenant_id=tenant_id,
            employee_id=payload.employee_id,
            work_schedule_id=payload.work_schedule_id,
            effective_from=payload.effective_from,
            effective_to=payload.effective_to,
        )
        db.commit()
        db.refresh(assignment)
        return assignment

    except ValueError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "The schedule assignment conflicts with an existing "
                "database constraint."
            ),
        ) from exc

    except Exception:
        db.rollback()
        raise




@router.get(
    "/assignments",
    response_model=list[EmployeeScheduleAssignmentResponse],
    status_code=status.HTTP_200_OK,
)
def list_schedule_assignments(
    employee_id: UUID | None = Query(default=None),
    tenant_id: UUID = Depends(get_tenant_id),
    db: Session = Depends(get_db),
):
    return EmployeeScheduleAssignmentService(db).list_assignments(
        tenant_id=tenant_id,
        employee_id=employee_id,
    )



@router.get(
    "/daily",
    response_model=DailyScheduleResponse,
    status_code=status.HTTP_200_OK,
)
def get_daily_schedule(
    on_date: date = Query(...),
    tenant_id: UUID = Depends(get_tenant_id),
    db: Session = Depends(get_db),
):
    result = DailyScheduleService(db).get_daily_schedule(
        tenant_id=tenant_id,
        on_date=on_date,
    )
    return result
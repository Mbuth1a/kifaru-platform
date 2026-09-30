from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from uuid import UUID

from fastapi import Header, HTTPException
from app.core.database import SessionLocal
from app.organization.schemas import (
    OrganizationUnitCreate,
    OrganizationUnitParentUpdate,
    OrganizationUnitResponse,
)
from app.organization.service import OrganizationUnitService
from app.core.dependencies import get_db

from .schemas import (
    LegalEntityCreate,
    LegalEntityResponse,
)
from .service import LegalEntityService

router = APIRouter(prefix="/legal-entities", tags=["Legal Entities"])


router = APIRouter(
    prefix="/organization",
    tags=["Organization"],
)
service = LegalEntityService()


@router.post(
    "",
    response_model=LegalEntityResponse,
    status_code=201,
)
def create_legal_entity(
    payload: LegalEntityCreate,
    db: Session = Depends(get_db),
):
    return service.create(db, payload)





def get_tenant_id(
    x_tenant_id: UUID = Header(...),
) -> UUID:
    return x_tenant_id


@router.post("/units", response_model=OrganizationUnitResponse, status_code=201)
def create_organization_unit(
    payload: OrganizationUnitCreate,
    tenant_id: UUID = Depends(get_tenant_id),
    db: Session = Depends(get_db),
):
    service = OrganizationUnitService(db)

    try:
        unit = service.create(
            tenant_id=tenant_id,
            legal_entity_id=payload.legal_entity_id,
            parent_id=payload.parent_id,
            code=payload.code,
            name=payload.name,
            unit_type=payload.unit_type,
            effective_from=payload.effective_from,
            effective_to=payload.effective_to,
            metadata_json=payload.metadata,
        )

        db.commit()
        db.refresh(unit)

        return unit

    except ValueError as exc:
        db.rollback()
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        )



@router.get(
    "/units/{unit_id}",
    response_model=OrganizationUnitResponse,
)
def get_organization_unit(
    unit_id: UUID,
    tenant_id: UUID = Depends(get_tenant_id),
    db: Session = Depends(get_db),
):
    service = OrganizationUnitService(db)

    try:
        return service.get(
        unit_id=unit_id,
        tenant_id=tenant_id,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        )


@router.patch(
    "/units/{unit_id}/parent",
    response_model=OrganizationUnitResponse,
)
def change_organization_unit_parent(
    unit_id: UUID,
    payload: OrganizationUnitParentUpdate,
    tenant_id: UUID = Depends(get_tenant_id),
    db: Session = Depends(get_db),
):
    service = OrganizationUnitService(db)

    try:
        unit = service.change_parent(
            tenant_id=tenant_id,
            unit_id=unit_id,
            new_parent_id=payload.parent_id,
        )

        db.commit()
        db.refresh(unit)

        return unit

    except ValueError as exc:
        db.rollback()

        message = str(exc)

        if "not found" in message.lower():
            status_code = 404
        else:
            status_code = 400

        raise HTTPException(
            status_code=status_code,
            detail=message,
        )


@router.get(
    "/units/{unit_id}/children",
    response_model=list[OrganizationUnitResponse],
)
def get_organization_unit_children(
    unit_id: UUID,
    tenant_id: UUID = Depends(get_tenant_id),
    db: Session = Depends(get_db),
):
    service = OrganizationUnitService(db)

    try:
        return service.get_children(
            tenant_id=tenant_id,
            unit_id=unit_id,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        )




@router.get(
    "/units/{unit_id}/descendants",
    response_model=list[OrganizationUnitResponse],
)
def get_organization_unit_descendants(
    unit_id: UUID,
    tenant_id: UUID = Depends(get_tenant_id),
    db: Session = Depends(get_db),
):
    service = OrganizationUnitService(db)

    try:
        return service.get_descendants(
            tenant_id=tenant_id,
            unit_id=unit_id,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        )

 

@router.get(
    "/units/{unit_id}/ancestors",
    response_model=list[OrganizationUnitResponse],
)
def get_organization_unit_ancestors(
    unit_id: UUID,
    tenant_id: UUID = Depends(get_tenant_id),
    db: Session = Depends(get_db),
):
    service = OrganizationUnitService(db)

    try:
        return service.get_ancestors(
            tenant_id=tenant_id,
            unit_id=unit_id,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        )


    

    
    
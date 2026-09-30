from __future__ import annotations

from fastapi import HTTPException

from .models import LegalEntity
from .repository import LegalEntityRepository

from datetime import datetime
from uuid import UUID

from sqlalchemy.orm import Session

from app.organization.models import OrganizationUnit


class LegalEntityService:

    def __init__(self):
        self.repo = LegalEntityRepository()

    def create(self, db, payload):

        if self.repo.exists_by_name(
            db,
            payload.tenant_id,
            payload.legal_name,
        ):
            raise HTTPException(
                status_code=409,
                detail="Legal entity already exists for this tenant.",
            )

        entity = LegalEntity(**payload.model_dump())

        return self.repo.create(db, entity)






class OrganizationUnitService:
    """
    Application/service layer for Organization Unit operations.

    Responsibilities:
    - Validate tenant ownership
    - Validate legal entity ownership
    - Validate parent ownership
    - Prevent self-parenting
    - Prevent hierarchy cycles
    - Provide hierarchy traversal operations
    """

    def __init__(self, db: Session):
        self.db = db

    # ------------------------------------------------------------------
    # Validation helpers
    # ------------------------------------------------------------------

    def _get_unit(
        self,
        unit_id: UUID,
        tenant_id: UUID,
    ) -> OrganizationUnit:
        unit = (
            self.db.query(OrganizationUnit)
            .filter(
                OrganizationUnit.id == unit_id,
                OrganizationUnit.tenant_id == tenant_id,
            )
            .first()
        )

        if unit is None:
            raise ValueError("Organization unit not found.")

        return unit

    def _validate_effective_dates(
        self,
        effective_from: datetime,
        effective_to: datetime | None,
    ) -> None:
        if effective_to is not None and effective_to <= effective_from:
            raise ValueError(
                "effective_to must be later than effective_from."
            )

    def _validate_parent(
        self,
        tenant_id: UUID,
        unit_id: UUID | None,
        parent_id: UUID | None,
    ) -> OrganizationUnit | None:
        if parent_id is None:
            return None

        if unit_id is not None and parent_id == unit_id:
            raise ValueError(
                "An organization unit cannot be its own parent."
            )

        parent = (
            self.db.query(OrganizationUnit)
            .filter(
                OrganizationUnit.id == parent_id,
                OrganizationUnit.tenant_id == tenant_id,
            )
            .first()
        )

        if parent is None:
            raise ValueError(
                "Parent organization unit not found."
            )

        return parent

    # ------------------------------------------------------------------
    # Create
    # ------------------------------------------------------------------

    def create(
        self,
        *,
        tenant_id: UUID,
        code: str,
        name: str,
        unit_type,
        effective_from: datetime,
        effective_to: datetime | None = None,
        legal_entity_id: UUID | None = None,
        parent_id: UUID | None = None,
        metadata_json: dict | None = None,
    ) -> OrganizationUnit:

        self._validate_effective_dates(
            effective_from,
            effective_to,
        )

        self._validate_parent(
            tenant_id=tenant_id,
            unit_id=None,
            parent_id=parent_id,
        )

        if legal_entity_id is not None:
            from app.organization.models import LegalEntity

            legal_entity = (
                self.db.query(LegalEntity)
                .filter(
                    LegalEntity.id == legal_entity_id,
                    LegalEntity.tenant_id == tenant_id,
                )
                .first()
            )

            if legal_entity is None:
                raise ValueError(
                    "Legal entity not found for this tenant."
                )

        organization_unit = OrganizationUnit(
            tenant_id=tenant_id,
            legal_entity_id=legal_entity_id,
            parent_id=parent_id,
            code=code,
            name=name,
            unit_type=unit_type,
            effective_from=effective_from,
            effective_to=effective_to,
            metadata_json=metadata_json or {},
        )

        self.db.add(organization_unit)
        self.db.flush()

        return organization_unit

    # ------------------------------------------------------------------
    # Change parent
    # ------------------------------------------------------------------

    def change_parent(
        self,
        *,
        tenant_id: UUID,
        unit_id: UUID,
        new_parent_id: UUID | None,
    ) -> OrganizationUnit:

        unit = self._get_unit(
            unit_id=unit_id,
            tenant_id=tenant_id,
        )

        if new_parent_id == unit_id:
            raise ValueError(
                "An organization unit cannot be its own parent."
            )

        if new_parent_id is None:
            unit.parent_id = None
            self.db.flush()
            return unit

        new_parent = self._validate_parent(
            tenant_id=tenant_id,
            unit_id=unit_id,
            parent_id=new_parent_id,
        )

        assert new_parent is not None

        # Walk upward from the proposed parent.
        #
        # If we encounter the unit being moved, the proposed
        # relationship would create a cycle.
        current = new_parent

        visited: set[UUID] = set()

        while current is not None:

            if current.id in visited:
                raise ValueError(
                    "Existing organization hierarchy contains a cycle."
                )

            visited.add(current.id)

            if current.id == unit_id:
                raise ValueError(
                    "Changing the parent would create a hierarchy cycle."
                )

            if current.parent_id is None:
                break

            current = self._get_unit(
                unit_id=current.parent_id,
                tenant_id=tenant_id,
            )

        unit.parent_id = new_parent_id

        self.db.flush()

        return unit

    # ------------------------------------------------------------------
    # Children
    # ------------------------------------------------------------------

    def get_children(
        self,
        *,
        tenant_id: UUID,
        unit_id: UUID,
    ) -> list[OrganizationUnit]:

        self._get_unit(
            unit_id=unit_id,
            tenant_id=tenant_id,
        )

        return (
            self.db.query(OrganizationUnit)
            .filter(
                OrganizationUnit.tenant_id == tenant_id,
                OrganizationUnit.parent_id == unit_id,
            )
            .order_by(OrganizationUnit.code)
            .all()
        )

    # ------------------------------------------------------------------
    # Descendants
    # ------------------------------------------------------------------

    def get_descendants(
        self,
        *,
        tenant_id: UUID,
        unit_id: UUID,
    ) -> list[OrganizationUnit]:

        self._get_unit(
            unit_id=unit_id,
            tenant_id=tenant_id,
        )

        descendants: list[OrganizationUnit] = []
        queue = [unit_id]
        visited: set[UUID] = set()

        while queue:

            current_id = queue.pop(0)

            if current_id in visited:
                continue

            visited.add(current_id)

            children = (
                self.db.query(OrganizationUnit)
                .filter(
                    OrganizationUnit.tenant_id == tenant_id,
                    OrganizationUnit.parent_id == current_id,
                )
                .order_by(OrganizationUnit.code)
                .all()
            )

            for child in children:
                descendants.append(child)
                queue.append(child.id)

        return descendants

    # ------------------------------------------------------------------
    # Ancestors
    # ------------------------------------------------------------------

    def get_ancestors(
        self,
        *,
        tenant_id: UUID,
        unit_id: UUID,
    ) -> list[OrganizationUnit]:

        unit = self._get_unit(
            unit_id=unit_id,
            tenant_id=tenant_id,
        )

        ancestors: list[OrganizationUnit] = []
        visited: set[UUID] = set()

        current_parent_id = unit.parent_id

        while current_parent_id is not None:

            if current_parent_id in visited:
                raise ValueError(
                    "Organization hierarchy contains a cycle."
                )

            visited.add(current_parent_id)

            parent = self._get_unit(
                unit_id=current_parent_id,
                tenant_id=tenant_id,
            )

            ancestors.append(parent)

            current_parent_id = parent.parent_id

        return ancestors
    def get(
        self,
        *,
        tenant_id: UUID,
        unit_id: UUID,
    ) -> OrganizationUnit:
        return self._get_unit(
            unit_id=unit_id,
            tenant_id=tenant_id,
        )
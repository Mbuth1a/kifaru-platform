from uuid import UUID
from datetime import datetime
from pydantic import AliasChoices, BaseModel, ConfigDict, Field

from app.organization.enums import (
    OrganizationUnitStatus,
    OrganizationUnitType,
)

class LegalEntityCreate(BaseModel):
    tenant_id: UUID

    legal_name: str = Field(min_length=2, max_length=255)

    registration_number: str | None = None
    tax_identifier: str | None = None

    country_code: str = Field(min_length=3, max_length=3)
    currency_code: str = Field(min_length=3, max_length=3)
    timezone: str


class LegalEntityResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    legal_name: str
    registration_number: str | None
    tax_identifier: str | None
    country_code: str
    currency_code: str
    timezone: str
    status: str

class OrganizationUnitCreate(BaseModel):
    legal_entity_id: UUID | None = None
    parent_id: UUID | None = None

    code: str = Field(min_length=1, max_length=100)
    name: str = Field(min_length=1, max_length=255)

    unit_type: OrganizationUnitType

    effective_from: datetime
    effective_to: datetime | None = None

    metadata: dict = Field(default_factory=dict)


class OrganizationUnitParentUpdate(BaseModel):
    parent_id: UUID | None = None


class OrganizationUnitResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    legal_entity_id: UUID | None
    parent_id: UUID | None
    code: str
    name: str
    unit_type: OrganizationUnitType
    status: OrganizationUnitStatus
    effective_from: datetime
    effective_to: datetime | None

    metadata: dict = Field(
        validation_alias=AliasChoices("metadata_json", "metadata")
    )

    created_at: datetime
    updated_at: datetime
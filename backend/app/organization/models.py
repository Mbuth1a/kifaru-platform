from datetime import datetime
import uuid

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    JSON,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import (
    Mapped,
    mapped_column,
    relationship,
)

from app.core.database import Base

from .enums import (
    LegalEntityStatus,
    OrganizationUnitStatus,
    OrganizationUnitType,
    TenantStatus,
)

class Tenant(Base):
    __tablename__ = "tenant"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    legal_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    trading_name: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    registration_number: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    tax_identifier: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    country_code: Mapped[str] = mapped_column(
        String(2),
        nullable=False,
    )

    timezone: Mapped[str] = mapped_column(
        String(64),
        default="Africa/Nairobi",
    )

    currency_code: Mapped[str] = mapped_column(
        String(3),
        default="KES",
    )

    status: Mapped[TenantStatus] = mapped_column(
        Enum(TenantStatus, name="tenant_status"),
        default=TenantStatus.PROVISIONING,
        nullable=False,
    )

    metadata_json: Mapped[dict] = mapped_column(
        "metadata",
        JSON,
        default=dict,
        nullable=False,
    )

    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    deactivated_at: Mapped[DateTime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    legal_entities = relationship(
    "LegalEntity",
    back_populates="tenant",
    cascade="all, delete-orphan",
    )
    organization_units = relationship(
    "OrganizationUnit",
    back_populates="tenant",
)



class LegalEntity(Base):
    __tablename__ = "legal_entity"

    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "legal_name",
            name="uq_legal_entity_name_per_tenant",
        ),
        Index("ix_legal_entity_tenant", "tenant_id"),
        Index("ix_legal_entity_status", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenant.id", ondelete="RESTRICT"),
        nullable=False,
    )

    legal_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    registration_number: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    tax_identifier: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    country_code: Mapped[str] = mapped_column(
        String(3),
        nullable=False,
    )

    currency_code: Mapped[str] = mapped_column(
        String(3),
        nullable=False,
    )

    timezone: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )

    status: Mapped[LegalEntityStatus] = mapped_column(
        Enum(LegalEntityStatus, name="legal_entity_status"),
        default=LegalEntityStatus.ACTIVE,
        nullable=False,
    )

    metadata_json: Mapped[dict] = mapped_column(
        "metadata",
        JSON,
        default=dict,
        nullable=False,
    )

    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    deactivated_at: Mapped[DateTime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    tenant = relationship("Tenant", back_populates="legal_entities")



class OrganizationUnit(Base):
    __tablename__ = "organization_unit"

    __table_args__ = (
    CheckConstraint(
        "effective_to IS NULL OR effective_to > effective_from",
        name="ck_organization_unit_effective_dates",
    ),

    UniqueConstraint(
        "tenant_id",
        "code",
        name="uq_organization_unit_tenant_code",
    ),

    UniqueConstraint(
        "tenant_id",
        "id",
        name="uq_organization_unit_tenant_id",
    ),

    ForeignKeyConstraint(
        ["tenant_id", "parent_id"],
        [
            "organization_unit.tenant_id",
            "organization_unit.id",
        ],
        ondelete="RESTRICT",
        name="fk_organization_unit_parent_same_tenant",
    ),

    Index(
        "ix_organization_unit_tenant",
        "tenant_id",
    ),

    Index(
        "ix_organization_unit_parent",
        "tenant_id",
        "parent_id",
    ),

    Index(
        "ix_organization_unit_legal_entity",
        "tenant_id",
        "legal_entity_id",
    ),

    Index(
        "ix_organization_unit_status",
        "tenant_id",
        "status",
    ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "tenant.id",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )

    legal_entity_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "legal_entity.id",
            ondelete="RESTRICT",
        ),
        nullable=True,
    )

    parent_id: Mapped[uuid.UUID | None] = mapped_column(
    UUID(as_uuid=True),
    nullable=True,
    )

    code: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    unit_type: Mapped[OrganizationUnitType] = mapped_column(
        Enum(
            OrganizationUnitType,
            name="organization_unit_type",
        ),
        nullable=False,
    )

    status: Mapped[OrganizationUnitStatus] = mapped_column(
        Enum(
            OrganizationUnitStatus,
            name="organization_unit_status",
        ),
        default=OrganizationUnitStatus.ACTIVE,
        nullable=False,
    )

    effective_from: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    effective_to: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    metadata_json: Mapped[dict] = mapped_column(
        "metadata",
        JSON,
        default=dict,
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    tenant = relationship(
        "Tenant",
        back_populates="organization_units",
    )

    legal_entity = relationship(
        "LegalEntity",
    )

    parent = relationship(
        "OrganizationUnit",
        remote_side=[id],
        back_populates="children",
        foreign_keys=[parent_id],
        overlaps="tenant,organization_units",
    )

    children = relationship(
        "OrganizationUnit",
        back_populates="parent",
        foreign_keys=[parent_id],
        overlaps="tenant,organization_units",
    )
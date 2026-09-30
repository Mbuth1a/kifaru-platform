"""create organization unit table

Revision ID: 858e73963589
Revises: 94a3b5af9b14
Create Date: 2026-09-25 10:42:22.261066

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "858e73963589"
down_revision: Union[str, Sequence[str], None] = "94a3b5af9b14"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""

    organization_unit_type = postgresql.ENUM(
        "COMPANY",
        "DIVISION",
        "DEPARTMENT",
        "TEAM",
        "BUSINESS_UNIT",
        name="organization_unit_type",
        create_type=False,
    )

    organization_unit_status = postgresql.ENUM(
        "ACTIVE",
        "INACTIVE",
        "DEACTIVATED",
        name="organization_unit_status",
        create_type=False,
    )

    organization_unit_type.create(
        op.get_bind(),
        checkfirst=True,
    )

    organization_unit_status.create(
        op.get_bind(),
        checkfirst=True,
    )

    op.create_table(
        "organization_unit",

        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),

        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),

        sa.Column(
            "legal_entity_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),

        sa.Column(
            "parent_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),

        sa.Column(
            "code",
            sa.String(length=100),
            nullable=False,
        ),

        sa.Column(
            "name",
            sa.String(length=255),
            nullable=False,
        ),

        sa.Column(
            "unit_type",
            organization_unit_type,
            nullable=False,
        ),

        sa.Column(
            "status",
            organization_unit_status,
            nullable=False,
        ),

        sa.Column(
            "effective_from",
            sa.DateTime(timezone=True),
            nullable=False,
        ),

        sa.Column(
            "effective_to",
            sa.DateTime(timezone=True),
            nullable=True,
        ),

        sa.Column(
            "metadata",
            sa.JSON(),
            nullable=False,
        ),

        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),

        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),

        sa.CheckConstraint(
            "effective_to IS NULL OR effective_to > effective_from",
            name="ck_organization_unit_effective_dates",
        ),

        sa.ForeignKeyConstraint(
            ["legal_entity_id"],
            ["legal_entity.id"],
            ondelete="RESTRICT",
        ),

        sa.ForeignKeyConstraint(
            ["tenant_id", "parent_id"],
            [
                "organization_unit.tenant_id",
                "organization_unit.id",
            ],
            name="fk_organization_unit_parent_same_tenant",
            ondelete="RESTRICT",
        ),

        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenant.id"],
            ondelete="RESTRICT",
        ),

        sa.PrimaryKeyConstraint("id"),

        sa.UniqueConstraint(
            "tenant_id",
            "id",
            name="uq_organization_unit_tenant_id",
        ),

        sa.UniqueConstraint(
            "tenant_id",
            "code",
            name="uq_organization_unit_tenant_code",
        ),
    )

    op.create_index(
        "ix_organization_unit_tenant",
        "organization_unit",
        ["tenant_id"],
    )

    op.create_index(
        "ix_organization_unit_parent",
        "organization_unit",
        ["tenant_id", "parent_id"],
    )

    op.create_index(
        "ix_organization_unit_legal_entity",
        "organization_unit",
        ["tenant_id", "legal_entity_id"],
    )

    op.create_index(
        "ix_organization_unit_status",
        "organization_unit",
        ["tenant_id", "status"],
    )


def downgrade() -> None:
    """Downgrade schema."""

    op.drop_index(
        "ix_organization_unit_status",
        table_name="organization_unit",
    )

    op.drop_index(
        "ix_organization_unit_legal_entity",
        table_name="organization_unit",
    )

    op.drop_index(
        "ix_organization_unit_parent",
        table_name="organization_unit",
    )

    op.drop_index(
        "ix_organization_unit_tenant",
        table_name="organization_unit",
    )

    op.drop_table("organization_unit")

    organization_unit_status = postgresql.ENUM(
        "ACTIVE",
        "INACTIVE",
        "DEACTIVATED",
        name="organization_unit_status",
    )

    organization_unit_type = postgresql.ENUM(
        "COMPANY",
        "DIVISION",
        "DEPARTMENT",
        "TEAM",
        "BUSINESS_UNIT",
        name="organization_unit_type",
    )

    organization_unit_status.drop(
        op.get_bind(),
        checkfirst=True,
    )

    organization_unit_type.drop(
        op.get_bind(),
        checkfirst=True,
    )
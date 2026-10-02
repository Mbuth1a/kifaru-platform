"""create employment status history table

Revision ID: 462d15a65c72
Revises: f5e13fca9ecf
Create Date: 2026-10-02 00:46:01.296369

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ExcludeConstraint, ENUM


# revision identifiers, used by Alembic.
revision: str = "462d15a65c72"
down_revision: Union[str, Sequence[str], None] = "f5e13fca9ecf"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create employment status history table."""
    op.create_table(
        "employment_status_history",
        sa.Column(
            "id",
            sa.UUID(),
            nullable=False,
        ),
        sa.Column(
            "tenant_id",
            sa.UUID(),
            nullable=False,
        ),
        sa.Column(
            "employee_id",
            sa.UUID(),
            nullable=False,
        ),
        sa.Column(
            "status",
              ENUM(
                "ACTIVE",
                "ON_LEAVE",
                "SUSPENDED",
                "TERMINATED",
                "RETIRED",
                name="employment_status",
                create_type=False,
            ),
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
            "reason",
            sa.String(length=255),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenant.id"],
            name="employment_status_history_tenant_id_fkey",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "employee_id"],
            ["employee.tenant_id", "employee.id"],
            name="fk_employment_status_history_employee_same_tenant",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint(
            "id",
            name="pk_employment_status_history",
        ),
        sa.UniqueConstraint(
            "tenant_id",
            "id",
            name="uq_employment_status_history_tenant_id",
        ),
        sa.CheckConstraint(
            """
            effective_to IS NULL
            OR effective_to > effective_from
            """,
            name="ck_employment_status_history_effective_dates",
        ),
        ExcludeConstraint(
                (
                    "tenant_id",
                    "=",
                ),
                (
                    "employee_id",
                    "=",
                ),
                (
                    sa.func.tstzrange(
                        sa.column("effective_from"),
                        sa.func.coalesce(
                            sa.column("effective_to"),
                            sa.text("'infinity'::timestamptz"),
                        ),
                        "[)",
                    ),
                    "&&",
                ),
                name="ex_employment_status_history_no_overlap",
                using="gist",
            ),
        )

    op.create_index(
        "ix_employment_status_history_tenant",
        "employment_status_history",
        ["tenant_id"],
    )

    op.create_index(
        "ix_employment_status_history_employee",
        "employment_status_history",
        ["tenant_id", "employee_id"],
    )

    op.create_index(
        "ix_employment_status_history_effective_dates",
        "employment_status_history",
        ["tenant_id", "effective_from", "effective_to"],
    )


def downgrade() -> None:
    """Drop employment status history table."""
    op.drop_index(
        "ix_employment_status_history_effective_dates",
        table_name="employment_status_history",
    )

    op.drop_index(
        "ix_employment_status_history_employee",
        table_name="employment_status_history",
    )

    op.drop_index(
        "ix_employment_status_history_tenant",
        table_name="employment_status_history",
    )

    op.drop_table("employment_status_history")
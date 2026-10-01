"""create employment term table

Revision ID: f5e13fca9ecf
Revises: 3e5b9bd9313a
Create Date: 2026-10-01
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "f5e13fca9ecf"
down_revision: Union[str, Sequence[str], None] = "3e5b9bd9313a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Required for the PostgreSQL EXCLUDE constraint.
    op.execute("CREATE EXTENSION IF NOT EXISTS btree_gist")

    pay_frequency = postgresql.ENUM(
        "MONTHLY",
        "BIWEEKLY",
        "WEEKLY",
        "DAILY",
        "HOURLY",
        name="pay_frequency",
    )
    pay_frequency.create(op.get_bind(), checkfirst=True)

    compensation_basis = postgresql.ENUM(
        "SALARY",
        "WAGE",
        name="compensation_basis",
    )
    compensation_basis.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "employment_term",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            nullable=False,
        ),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "employee_id",
            postgresql.UUID(as_uuid=True),
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
            "pay_frequency",
            postgresql.ENUM(
                "MONTHLY",
                "BIWEEKLY",
                "WEEKLY",
                "DAILY",
                "HOURLY",
                name="pay_frequency",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column(
            "compensation_basis",
            postgresql.ENUM(
                "SALARY",
                "WAGE",
                name="compensation_basis",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column(
            "currency_code",
            sa.String(length=3),
            nullable=False,
        ),
        sa.Column(
            "amount",
            sa.Numeric(18, 2),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenant.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "employee_id"],
            ["employee.tenant_id", "employee.id"],
            ondelete="RESTRICT",
            name="fk_employment_term_employee_same_tenant",
        ),
        sa.UniqueConstraint(
            "tenant_id",
            "id",
            name="uq_employment_term_tenant_id",
        ),
        sa.CheckConstraint(
            "effective_to IS NULL OR effective_to > effective_from",
            name="ck_employment_term_effective_dates",
        ),
        sa.CheckConstraint(
            "amount > 0",
            name="ck_employment_term_positive_amount",
        ),
    )

    op.create_index(
        "ix_employment_term_tenant",
        "employment_term",
        ["tenant_id"],
    )

    op.create_index(
        "ix_employment_term_employee",
        "employment_term",
        ["tenant_id", "employee_id"],
    )

    op.create_index(
        "ix_employment_term_effective_dates",
        "employment_term",
        ["tenant_id", "effective_from", "effective_to"],
    )

    op.execute(
        """
        ALTER TABLE employment_term
        ADD CONSTRAINT ex_employment_term_no_overlap
        EXCLUDE USING gist (
            tenant_id WITH =,
            employee_id WITH =,
            tstzrange(
                effective_from,
                COALESCE(effective_to, 'infinity'::timestamptz),
                '[)'
            ) WITH &&
        )
        """
    )


def downgrade() -> None:
    op.execute(
        """
        ALTER TABLE employment_term
        DROP CONSTRAINT IF EXISTS ex_employment_term_no_overlap
        """
    )

    op.drop_index(
        "ix_employment_term_effective_dates",
        table_name="employment_term",
    )

    op.drop_index(
        "ix_employment_term_employee",
        table_name="employment_term",
    )

    op.drop_index(
        "ix_employment_term_tenant",
        table_name="employment_term",
    )

    op.drop_table("employment_term")

    compensation_basis = postgresql.ENUM(
        "SALARY",
        "WAGE",
        name="compensation_basis",
    )
    compensation_basis.drop(op.get_bind(), checkfirst=True)

    pay_frequency = postgresql.ENUM(
        "MONTHLY",
        "BIWEEKLY",
        "WEEKLY",
        "DAILY",
        "HOURLY",
        name="pay_frequency",
    )
    pay_frequency.drop(op.get_bind(), checkfirst=True)
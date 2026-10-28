"""create employee schedule assignment table

Revision ID: d7c7ebe40ffb
Revises: 1892ff75ab95
Create Date: 2026-10-25 18:52:59.033012

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'd7c7ebe40ffb'
down_revision: Union[str, Sequence[str], None] = '1892ff75ab95'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None



def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS btree_gist")

    op.create_table(
        "employee_schedule_assignment",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("employee_id", sa.UUID(), nullable=False),
        sa.Column("work_schedule_id", sa.UUID(), nullable=False),
        sa.Column("effective_from", sa.Date(), nullable=False),
        sa.Column("effective_to", sa.Date(), nullable=True),
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
            name="ck_employee_schedule_assignment_effective_dates",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "employee_id"],
            ["employee.tenant_id", "employee.id"],
            name="fk_employee_schedule_assignment_employee_tenant",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "work_schedule_id"],
            ["work_schedule.tenant_id", "work_schedule.id"],
            name="fk_employee_schedule_assignment_schedule_tenant",
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
            name="uq_employee_schedule_assignment_tenant_id",
        ),
    )

    op.create_index(
        "ix_employee_schedule_assignment_effective_dates",
        "employee_schedule_assignment",
        ["tenant_id", "effective_from", "effective_to"],
    )
    op.create_index(
        "ix_employee_schedule_assignment_employee",
        "employee_schedule_assignment",
        ["tenant_id", "employee_id"],
    )
    op.create_index(
        "ix_employee_schedule_assignment_tenant",
        "employee_schedule_assignment",
        ["tenant_id"],
    )

    op.execute(
        """
        ALTER TABLE employee_schedule_assignment
        ADD CONSTRAINT ex_employee_schedule_assignment_no_overlap
        EXCLUDE USING gist (
            tenant_id WITH =,
            employee_id WITH =,
            daterange(
                effective_from,
                COALESCE(effective_to, 'infinity'::date),
                '[)'
            ) WITH &&
        )
        """
    )




def downgrade() -> None:
    op.execute(
        """
        ALTER TABLE employee_schedule_assignment
        DROP CONSTRAINT IF EXISTS ex_employee_schedule_assignment_no_overlap
        """
    )

    op.drop_index(
        "ix_employee_schedule_assignment_effective_dates",
        table_name="employee_schedule_assignment",
    )
    op.drop_index(
        "ix_employee_schedule_assignment_employee",
        table_name="employee_schedule_assignment",
    )
    op.drop_index(
        "ix_employee_schedule_assignment_tenant",
        table_name="employee_schedule_assignment",
    )
    op.drop_table("employee_schedule_assignment")

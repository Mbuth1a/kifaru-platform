"""create attendance record table

Revision ID: e0a3d8ad7cdf
Revises: f10569420f9f
Create Date: 2026-10-05 19:07:27.481747

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "e0a3d8ad7cdf"
down_revision: Union[str, Sequence[str], None] = "f10569420f9f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""

    bind = op.get_bind()

    attendance_status = postgresql.ENUM(
        "PRESENT",
        "ABSENT",
        "LATE",
        "HALF_DAY",
        "ON_LEAVE",
        "HOLIDAY",
        name="attendance_status",
    )

    attendance_source = postgresql.ENUM(
        "MANUAL",
        "IMPORT",
        "DEVICE",
        "SYSTEM",
        name="attendance_source",
    )

    attendance_status.create(bind, checkfirst=True)
    attendance_source.create(bind, checkfirst=True)

    op.create_table(
        "attendance_record",
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
            "attendance_date",
            sa.Date(),
            nullable=False,
        ),
        sa.Column(
            "check_in",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "check_out",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "status",
            postgresql.ENUM(
                "PRESENT",
                "ABSENT",
                "LATE",
                "HALF_DAY",
                "ON_LEAVE",
                "HOLIDAY",
                name="attendance_status",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column(
            "source",
            postgresql.ENUM(
                "MANUAL",
                "IMPORT",
                "DEVICE",
                "SYSTEM",
                name="attendance_source",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column(
            "notes",
            sa.String(length=1000),
            nullable=True,
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
            """
            check_out IS NULL
            OR check_in IS NULL
            OR check_out >= check_in
            """,
            name="ck_attendance_record_check_times",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "employee_id"],
            ["employee.tenant_id", "employee.id"],
            name="fk_attendance_record_employee_same_tenant",
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
            "employee_id",
            "attendance_date",
            name="uq_attendance_record_employee_date",
        ),
        sa.UniqueConstraint(
            "tenant_id",
            "id",
            name="uq_attendance_record_tenant_id",
        ),
    )

    op.create_index(
        "ix_attendance_record_date",
        "attendance_record",
        ["tenant_id", "attendance_date"],
        unique=False,
    )

    op.create_index(
        "ix_attendance_record_employee",
        "attendance_record",
        ["tenant_id", "employee_id"],
        unique=False,
    )

    op.create_index(
        "ix_attendance_record_employee_date",
        "attendance_record",
        ["tenant_id", "employee_id", "attendance_date"],
        unique=False,
    )

    op.create_index(
        "ix_attendance_record_status",
        "attendance_record",
        ["tenant_id", "status"],
        unique=False,
    )

    op.create_index(
        "ix_attendance_record_tenant",
        "attendance_record",
        ["tenant_id"],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""

    op.drop_index(
        "ix_attendance_record_tenant",
        table_name="attendance_record",
    )

    op.drop_index(
        "ix_attendance_record_status",
        table_name="attendance_record",
    )

    op.drop_index(
        "ix_attendance_record_employee_date",
        table_name="attendance_record",
    )

    op.drop_index(
        "ix_attendance_record_employee",
        table_name="attendance_record",
    )

    op.drop_index(
        "ix_attendance_record_date",
        table_name="attendance_record",
    )

    op.drop_table("attendance_record")

    bind = op.get_bind()

    attendance_source = postgresql.ENUM(
        "MANUAL",
        "IMPORT",
        "DEVICE",
        "SYSTEM",
        name="attendance_source",
    )

    attendance_status = postgresql.ENUM(
        "PRESENT",
        "ABSENT",
        "LATE",
        "HALF_DAY",
        "ON_LEAVE",
        "HOLIDAY",
        name="attendance_status",
    )

    attendance_source.drop(bind, checkfirst=True)
    attendance_status.drop(bind, checkfirst=True)
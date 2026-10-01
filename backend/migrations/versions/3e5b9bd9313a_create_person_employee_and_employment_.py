"""create person employee and employment assignment tables

Revision ID: 3e5b9bd9313a
Revises: 858e73963589
Create Date: 2026-09-30
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "3e5b9bd9313a"
down_revision: Union[str, Sequence[str], None] = "858e73963589"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""

    # ------------------------------------------------------------------
    # PostgreSQL extensions
    # ------------------------------------------------------------------

    op.execute("CREATE EXTENSION IF NOT EXISTS btree_gist")

    # ------------------------------------------------------------------
    # PostgreSQL enums
    # ------------------------------------------------------------------

    gender = postgresql.ENUM(
        "MALE",
        "FEMALE",
        "OTHER",
        "PREFER_NOT_TO_SAY",
        name="gender",
        create_type=False,
    )

    employment_status = postgresql.ENUM(
        "ACTIVE",
        "ON_LEAVE",
        "SUSPENDED",
        "TERMINATED",
        "RETIRED",
        name="employment_status",
        create_type=False,
    )

    employment_type = postgresql.ENUM(
        "PERMANENT",
        "FIXED_TERM",
        "CONTRACT",
        "CASUAL",
        "INTERN",
        "PART_TIME",
        name="employment_type",
        create_type=False,
    )

    gender.create(
        op.get_bind(),
        checkfirst=True,
    )

    employment_status.create(
        op.get_bind(),
        checkfirst=True,
    )

    employment_type.create(
        op.get_bind(),
        checkfirst=True,
    )

    # ------------------------------------------------------------------
    # Person
    # ------------------------------------------------------------------

    op.create_table(
        "person",

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
            "person_number",
            sa.String(length=50),
            nullable=False,
        ),

        sa.Column(
            "first_name",
            sa.String(length=100),
            nullable=False,
        ),

        sa.Column(
            "middle_name",
            sa.String(length=100),
            nullable=True,
        ),

        sa.Column(
            "last_name",
            sa.String(length=100),
            nullable=False,
        ),

        sa.Column(
            "preferred_name",
            sa.String(length=100),
            nullable=True,
        ),

        sa.Column(
            "date_of_birth",
            sa.Date(),
            nullable=True,
        ),

        sa.Column(
            "gender",
            gender,
            nullable=True,
        ),

        sa.Column(
            "nationality_code",
            sa.String(length=2),
            nullable=True,
        ),

        sa.Column(
            "national_id_number",
            sa.String(length=100),
            nullable=True,
        ),

        sa.Column(
            "tax_identifier",
            sa.String(length=100),
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

        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenant.id"],
            ondelete="RESTRICT",
        ),

        sa.PrimaryKeyConstraint("id"),

        sa.UniqueConstraint(
            "tenant_id",
            "id",
            name="uq_person_tenant_id",
        ),

        sa.UniqueConstraint(
            "tenant_id",
            "person_number",
            name="uq_person_tenant_person_number",
        ),
    )

    op.create_index(
        "ix_person_tenant",
        "person",
        ["tenant_id"],
    )

    op.create_index(
        "ix_person_tenant_national_id",
        "person",
        ["tenant_id", "national_id_number"],
    )

    op.create_index(
        "ix_person_tenant_tax_identifier",
        "person",
        ["tenant_id", "tax_identifier"],
    )

    # ------------------------------------------------------------------
    # Employee
    # ------------------------------------------------------------------

    op.create_table(
        "employee",

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
            "person_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),

        sa.Column(
            "employee_number",
            sa.String(length=50),
            nullable=False,
        ),

        sa.Column(
            "employment_status",
            employment_status,
            nullable=False,
        ),

        sa.Column(
            "employment_type",
            employment_type,
            nullable=False,
        ),

        sa.Column(
            "hire_date",
            sa.Date(),
            nullable=False,
        ),

        sa.Column(
            "termination_date",
            sa.Date(),
            nullable=True,
        ),

        sa.Column(
            "termination_reason",
            sa.String(length=255),
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
            "termination_date IS NULL OR termination_date >= hire_date",
            name="ck_employee_termination_date",
        ),

        sa.ForeignKeyConstraint(
            ["tenant_id", "person_id"],
            [
                "person.tenant_id",
                "person.id",
            ],
            name="fk_employee_person_same_tenant",
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
            name="uq_employee_tenant_id",
        ),

        sa.UniqueConstraint(
            "tenant_id",
            "employee_number",
            name="uq_employee_tenant_employee_number",
        ),
    )

    op.create_index(
        "ix_employee_tenant",
        "employee",
        ["tenant_id"],
    )

    op.create_index(
        "ix_employee_person",
        "employee",
        ["tenant_id", "person_id"],
    )

   

    op.create_index(
        "ix_employee_tenant_status",
        "employee",
        ["tenant_id", "employment_status"],
    )

    # ------------------------------------------------------------------
    # Employment Assignment
    # ------------------------------------------------------------------

    op.create_table(
        "employment_assignment",

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
            "employee_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),

        sa.Column(
            "organization_unit_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),

        sa.Column(
            "job_title",
            sa.String(length=150),
            nullable=False,
        ),

        sa.Column(
            "manager_employee_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
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
            name="ck_employment_assignment_effective_dates",
        ),

        sa.ForeignKeyConstraint(
            ["tenant_id", "employee_id"],
            [
                "employee.tenant_id",
                "employee.id",
            ],
            name="fk_assignment_employee_same_tenant",
            ondelete="RESTRICT",
        ),

        sa.ForeignKeyConstraint(
            ["tenant_id", "organization_unit_id"],
            [
                "organization_unit.tenant_id",
                "organization_unit.id",
            ],
            name="fk_assignment_org_unit_same_tenant",
            ondelete="RESTRICT",
        ),

        sa.ForeignKeyConstraint(
            ["tenant_id", "manager_employee_id"],
            [
                "employee.tenant_id",
                "employee.id",
            ],
            name="fk_assignment_manager_same_tenant",
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
            name="uq_employment_assignment_tenant_id",
        ),
    )

    op.create_index(
        "ix_assignment_tenant",
        "employment_assignment",
        ["tenant_id"],
    )

    op.create_index(
        "ix_assignment_employee",
        "employment_assignment",
        ["tenant_id", "employee_id"],
    )

    op.create_index(
        "ix_assignment_org_unit",
        "employment_assignment",
        ["tenant_id", "organization_unit_id"],
    )

    op.create_index(
        "ix_assignment_manager",
        "employment_assignment",
        ["tenant_id", "manager_employee_id"],
    )

    op.create_index(
        "ix_assignment_effective_dates",
        "employment_assignment",
        [
            "tenant_id",
            "employee_id",
            "effective_from",
            "effective_to",
        ],
    )

    # ------------------------------------------------------------------
    # Prevent overlapping assignments for the same employee
    # ------------------------------------------------------------------

    op.execute(
        """
        ALTER TABLE employment_assignment
        ADD CONSTRAINT ex_employment_assignment_no_overlap
        EXCLUDE USING gist (
            tenant_id WITH =,
            employee_id WITH =,
            tstzrange(
                effective_from,
                COALESCE(
                    effective_to,
                    'infinity'::timestamptz
                ),
                '[)'
            ) WITH &&
        )
        """
    )


def downgrade() -> None:
    """Downgrade schema."""

    # ------------------------------------------------------------------
    # Employment assignment
    # ------------------------------------------------------------------

    op.drop_constraint(
        "ex_employment_assignment_no_overlap",
        "employment_assignment",
        type_="exclude",
    )

    op.drop_index(
        "ix_assignment_effective_dates",
        table_name="employment_assignment",
    )

    op.drop_index(
        "ix_assignment_manager",
        table_name="employment_assignment",
    )

    op.drop_index(
        "ix_assignment_org_unit",
        table_name="employment_assignment",
    )

    op.drop_index(
        "ix_assignment_employee",
        table_name="employment_assignment",
    )

    op.drop_index(
        "ix_assignment_tenant",
        table_name="employment_assignment",
    )

    op.drop_table("employment_assignment")

    # ------------------------------------------------------------------
    # Employee
    # ------------------------------------------------------------------

    op.drop_index(
        "ix_employee_tenant_status",
        table_name="employee",
    )

    op.drop_index(
        "ix_employee_status",
        table_name="employee",
    )

    op.drop_index(
        "ix_employee_person",
        table_name="employee",
    )

    op.drop_index(
        "ix_employee_tenant",
        table_name="employee",
    )

    op.drop_table("employee")

    # ------------------------------------------------------------------
    # Person
    # ------------------------------------------------------------------

    op.drop_index(
        "ix_person_tenant_tax_identifier",
        table_name="person",
    )

    op.drop_index(
        "ix_person_tenant_national_id",
        table_name="person",
    )

    op.drop_index(
        "ix_person_tenant",
        table_name="person",
    )

    op.drop_table("person")

    # ------------------------------------------------------------------
    # PostgreSQL enums
    # ------------------------------------------------------------------

    employment_type = postgresql.ENUM(
        "PERMANENT",
        "FIXED_TERM",
        "CONTRACT",
        "CASUAL",
        "INTERN",
        "PART_TIME",
        name="employment_type",
    )

    employment_status = postgresql.ENUM(
        "ACTIVE",
        "ON_LEAVE",
        "SUSPENDED",
        "TERMINATED",
        "RETIRED",
        name="employment_status",
    )

    gender = postgresql.ENUM(
        "MALE",
        "FEMALE",
        "OTHER",
        "PREFER_NOT_TO_SAY",
        name="gender",
    )

    employment_type.drop(
        op.get_bind(),
        checkfirst=True,
    )

    employment_status.drop(
        op.get_bind(),
        checkfirst=True,
    )

    gender.drop(
        op.get_bind(),
        checkfirst=True,
    )

    # ------------------------------------------------------------------
    # PostgreSQL extension
    # ------------------------------------------------------------------

    op.execute("DROP EXTENSION IF EXISTS btree_gist")
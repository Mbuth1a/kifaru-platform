import uuid

from datetime import date, datetime

from sqlalchemy import (
    Date,
    DateTime,
    Enum,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    String,
    UniqueConstraint,
    CheckConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID, ExcludeConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from .enums import Gender, EmploymentStatus, EmploymentType


class Person(Base):
    __tablename__ = "person"

    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "person_number",
            name="uq_person_tenant_person_number",
        ),
        UniqueConstraint(
            "tenant_id",
            "id",
            name="uq_person_tenant_id",
        ),
        Index(
            "ix_person_tenant",
            "tenant_id",
        ),
        Index(
            "ix_person_tenant_national_id",
            "tenant_id",
            "national_id_number",
        ),
        Index(
            "ix_person_tenant_tax_identifier",
            "tenant_id",
            "tax_identifier",
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

    person_number: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    first_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    middle_name: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    last_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    preferred_name: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    date_of_birth: Mapped[date | None] = mapped_column(
        Date,
        nullable=True,
    )

    gender: Mapped[Gender | None] = mapped_column(
        Enum(
            Gender,
            name="gender",
        ),
        nullable=True,
    )

    nationality_code: Mapped[str | None] = mapped_column(
        String(2),
        nullable=True,
    )

    national_id_number: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    tax_identifier: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
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

    tenant = relationship("Tenant")

    employees = relationship(
        "Employee",
        back_populates="person",
        foreign_keys="Employee.person_id",
    )


class Employee(Base):
    __tablename__ = "employee"

    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "employee_number",
            name="uq_employee_tenant_employee_number",
        ),
        UniqueConstraint(
            "tenant_id",
            "id",
            name="uq_employee_tenant_id",
        ),
        CheckConstraint(
            "termination_date IS NULL OR termination_date >= hire_date",
            name="ck_employee_termination_date",
        ),
        Index(
            "ix_employee_tenant",
            "tenant_id",
        ),
        Index(
            "ix_employee_person",
            "tenant_id",
            "person_id",
        ),
        Index(
            "ix_employee_tenant_status",
            "tenant_id",
            "employment_status",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "person_id"],
            ["person.tenant_id", "person.id"],
            ondelete="RESTRICT",
            name="fk_employee_person_same_tenant",
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

    person_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
    )

    employee_number: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    employment_status: Mapped[EmploymentStatus] = mapped_column(
        Enum(
            EmploymentStatus,
            name="employment_status",
        ),
        nullable=False,
    )

    employment_type: Mapped[EmploymentType] = mapped_column(
        Enum(
            EmploymentType,
            name="employment_type",
        ),
        nullable=False,
    )

    hire_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
    )

    termination_date: Mapped[date | None] = mapped_column(
        Date,
        nullable=True,
    )

    termination_reason: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
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

    tenant = relationship("Tenant")

    person = relationship(
        "Person",
        back_populates="employees",
        foreign_keys=[person_id],
    )

    assignments = relationship(
        "EmploymentAssignment",
        back_populates="employee",
        foreign_keys="EmploymentAssignment.employee_id",
    )

    managed_assignments = relationship(
        "EmploymentAssignment",
        back_populates="manager",
        foreign_keys="EmploymentAssignment.manager_employee_id",
    )


class EmploymentAssignment(Base):
    __tablename__ = "employment_assignment"

    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "id",
            name="uq_employment_assignment_tenant_id",
        ),
        CheckConstraint(
            "effective_to IS NULL OR effective_to > effective_from",
            name="ck_employment_assignment_effective_dates",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "employee_id"],
            ["employee.tenant_id", "employee.id"],
            ondelete="RESTRICT",
            name="fk_assignment_employee_same_tenant",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "manager_employee_id"],
            ["employee.tenant_id", "employee.id"],
            ondelete="RESTRICT",
            name="fk_assignment_manager_same_tenant",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "organization_unit_id"],
            ["organization_unit.tenant_id", "organization_unit.id"],
            ondelete="RESTRICT",
            name="fk_assignment_org_unit_same_tenant",
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
                func.tstzrange(
                    "effective_from",
                    func.coalesce(
                        "effective_to",
                        func.cast("infinity", DateTime(timezone=True)),
                    ),
                    "[)",
                ),
                "&&",
            ),
            name="ex_employment_assignment_no_overlap",
            using="gist",
        ),
        Index(
            "ix_assignment_tenant",
            "tenant_id",
        ),
        Index(
            "ix_assignment_employee",
            "tenant_id",
            "employee_id",
        ),
        Index(
            "ix_assignment_org_unit",
            "tenant_id",
            "organization_unit_id",
        ),
        Index(
            "ix_assignment_manager",
            "tenant_id",
            "manager_employee_id",
        ),
        Index(
            "ix_assignment_effective_dates",
            "tenant_id",
            "employee_id",
            "effective_from",
            "effective_to",
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

    employee_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
    )

    organization_unit_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
    )

    job_title: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
    )

    manager_employee_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
    )

    effective_from: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    effective_to: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
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

    tenant = relationship("Tenant")

    employee = relationship(
        "Employee",
        back_populates="assignments",
        foreign_keys=[employee_id],
    )

    manager = relationship(
        "Employee",
        back_populates="managed_assignments",
        foreign_keys=[manager_employee_id],
    )

    organization_unit = relationship(
        "OrganizationUnit",
        overlaps="tenant",
    )
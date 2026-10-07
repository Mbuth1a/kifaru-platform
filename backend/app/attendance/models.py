from datetime import date, datetime
import uuid

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

from .enums import AttendanceSource, AttendanceStatus


class AttendanceRecord(Base):
    __tablename__ = "attendance_record"

    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "employee_id",
            "attendance_date",
            name="uq_attendance_record_employee_date",
        ),
        UniqueConstraint(
            "tenant_id",
            "id",
            name="uq_attendance_record_tenant_id",
        ),
        CheckConstraint(
            """
            check_out IS NULL
            OR check_in IS NULL
            OR check_out >= check_in
            """,
            name="ck_attendance_record_check_times",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "employee_id"],
            ["employee.tenant_id", "employee.id"],
            ondelete="RESTRICT",
            name="fk_attendance_record_employee_same_tenant",
        ),
        Index(
            "ix_attendance_record_tenant",
            "tenant_id",
        ),
        Index(
            "ix_attendance_record_employee",
            "tenant_id",
            "employee_id",
        ),
        Index(
            "ix_attendance_record_status",
            "tenant_id",
            "status",
        ),
        Index(
            "ix_attendance_record_date",
            "tenant_id",
            "attendance_date",
        ),
        Index(
            "ix_attendance_record_employee_date",
            "tenant_id",
            "employee_id",
            "attendance_date",
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

    attendance_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
    )

    check_in: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    check_out: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    status: Mapped[AttendanceStatus] = mapped_column(
        Enum(
            AttendanceStatus,
            name="attendance_status",
            create_type=False,
        ),
        nullable=False,
    )

    source: Mapped[AttendanceSource] = mapped_column(
        Enum(
            AttendanceSource,
            name="attendance_source",
            create_type=False,
        ),
        nullable=False,
    )

    notes: Mapped[str | None] = mapped_column(
        String(1000),
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

    tenant = relationship(
        "Tenant",
        overlaps="employee",
    )

    employee = relationship(
        "Employee",
        overlaps="tenant",
    )
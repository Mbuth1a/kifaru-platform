from datetime import date, datetime
import uuid

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

from .enums import LeaveRequestStatus


class LeaveType(Base):
    __tablename__ = "leave_type"

    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "code",
            name="uq_leave_type_tenant_code",
        ),
        UniqueConstraint(
            "tenant_id",
            "name",
            name="uq_leave_type_tenant_name",
        ),
        UniqueConstraint(
            "tenant_id",
            "id",
            name="uq_leave_type_tenant_id",
        ),
        Index(
            "ix_leave_type_tenant",
            "tenant_id",
        ),
        Index(
            "ix_leave_type_tenant_active",
            "tenant_id",
            "active",
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

    code: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    description: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
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

    tenant = relationship("Tenant")

    leave_requests = relationship(
    "LeaveRequest",
    back_populates="leave_type",
    overlaps="tenant,employee",)
    


class LeaveRequest(Base):
    __tablename__ = "leave_request"

    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "id",
            name="uq_leave_request_tenant_id",
        ),
        CheckConstraint(
            "end_date >= start_date",
            name="ck_leave_request_date_range",
        ),
        CheckConstraint(
            "requested_days > 0",
            name="ck_leave_request_positive_days",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "employee_id"],
            ["employee.tenant_id", "employee.id"],
            ondelete="RESTRICT",
            name="fk_leave_request_employee_same_tenant",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "leave_type_id"],
            ["leave_type.tenant_id", "leave_type.id"],
            ondelete="RESTRICT",
            name="fk_leave_request_leave_type_same_tenant",
        ),
        Index(
            "ix_leave_request_tenant",
            "tenant_id",
        ),
        Index(
            "ix_leave_request_employee",
            "tenant_id",
            "employee_id",
        ),
        Index(
            "ix_leave_request_leave_type",
            "tenant_id",
            "leave_type_id",
        ),
        Index(
            "ix_leave_request_status",
            "tenant_id",
            "status",
        ),
        Index(
            "ix_leave_request_employee_dates",
            "tenant_id",
            "employee_id",
            "start_date",
            "end_date",
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

    leave_type_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
    )

    start_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
    )

    end_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
    )

    requested_days: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    reason: Mapped[str | None] = mapped_column(
        String(1000),
        nullable=True,
    )

    status: Mapped[LeaveRequestStatus] = mapped_column(
        # PostgreSQL enum creation will be handled by the migration.
        # create_type=False keeps model import/autogeneration predictable.
        __import__("sqlalchemy").Enum(
            LeaveRequestStatus,
            name="leave_request_status",
            create_type=False,
        ),
        nullable=False,
        default=LeaveRequestStatus.PENDING,
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
    overlaps="employee,leave_type,leave_requests",
    )

    employee = relationship(
        "Employee",
        overlaps="tenant,leave_type,leave_requests",
    )

    leave_type = relationship(
        "LeaveType",
        back_populates="leave_requests",
        overlaps="tenant,employee,leave_requests",
    )

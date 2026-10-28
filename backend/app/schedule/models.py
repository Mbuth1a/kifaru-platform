
import uuid
from datetime import date, datetime, time

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Date,
    text,
    Enum as SAEnum,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    String,
    Time,
    UniqueConstraint,
    and_,
    func,
)

from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import ExcludeConstraint, UUID
from app.core.database import Base
from app.schedule.enums import ScheduleDay


class WorkShift(Base):
    __tablename__ = "work_shift"

    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "code",
            name="uq_work_shift_tenant_code",
        ),
        UniqueConstraint(
            "tenant_id",
            "id",
            name="uq_work_shift_tenant_id",
        ),
        CheckConstraint(
            "start_time <> end_time",
            name="ck_work_shift_different_times",
        ),
        Index(
            "ix_work_shift_tenant",
            "tenant_id",
        ),
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

    code: Mapped[str] = mapped_column(String(100), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    start_time: Mapped[time] = mapped_column(Time, nullable=False)
    end_time: Mapped[time] = mapped_column(Time, nullable=False)

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


class WorkSchedule(Base):
    __tablename__ = "work_schedule"

    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "code",
            name="uq_work_schedule_tenant_code",
        ),
        UniqueConstraint(
            "tenant_id",
            "id",
            name="uq_work_schedule_tenant_id",
        ),
        Index(
            "ix_work_schedule_tenant",
            "tenant_id",
        ),
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

    code: Mapped[str] = mapped_column(String(100), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)

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

    days: Mapped[list["WorkScheduleDay"]] = relationship(
        "WorkScheduleDay",
        back_populates="work_schedule",
        cascade="all, delete-orphan",
        foreign_keys="WorkScheduleDay.work_schedule_id",
        order_by="WorkScheduleDay.day",
    )


class WorkScheduleDay(Base):
    __tablename__ = "work_schedule_day"

    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "work_schedule_id",
            "day",
            name="uq_work_schedule_day_tenant_schedule_day",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "work_schedule_id"],
            ["work_schedule.tenant_id", "work_schedule.id"],
            ondelete="CASCADE",
            name="fk_work_schedule_day_schedule_tenant",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "work_shift_id"],
            ["work_shift.tenant_id", "work_shift.id"],
            ondelete="RESTRICT",
            name="fk_work_schedule_day_shift_tenant",
        ),
        Index(
            "ix_work_schedule_day_tenant",
            "tenant_id",
        ),
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

    work_schedule_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
    )

    day: Mapped[ScheduleDay] = mapped_column(
        SAEnum(
            ScheduleDay,
            name="schedule_day",
            values_callable=lambda enum_cls: [
                item.value for item in enum_cls
            ],
        ),
        nullable=False,
    )

    work_shift_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
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

    work_schedule: Mapped["WorkSchedule"] = relationship(
        "WorkSchedule",
        back_populates="days",
        foreign_keys=[tenant_id, work_schedule_id],
        overlaps="tenant",
    )

    work_shift: Mapped["WorkShift"] = relationship(
        "WorkShift",
        primaryjoin=lambda: and_(
            WorkScheduleDay.tenant_id == WorkShift.tenant_id,
            WorkScheduleDay.work_shift_id == WorkShift.id,
        ),
        foreign_keys=[tenant_id, work_shift_id],
        viewonly=True,
    )




class EmployeeScheduleAssignment(Base):
    __tablename__ = "employee_schedule_assignment"

    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "id",
            name="uq_employee_schedule_assignment_tenant_id",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "employee_id"],
            ["employee.tenant_id", "employee.id"],
            ondelete="RESTRICT",
            name="fk_employee_schedule_assignment_employee_tenant",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "work_schedule_id"],
            ["work_schedule.tenant_id", "work_schedule.id"],
            ondelete="RESTRICT",
            name="fk_employee_schedule_assignment_schedule_tenant",
        ),
        CheckConstraint(
            "effective_to IS NULL OR effective_to > effective_from",
            name="ck_employee_schedule_assignment_effective_dates",
        ),
        ExcludeConstraint(
            ("tenant_id", "="),
            ("employee_id", "="),
            (
                func.daterange(
                    "effective_from",
                    func.coalesce(
                        "effective_to",
                        text("'infinity'::date"),
                    ),
                    "[)",
                ),
                "&&",
            ),
            name="ex_employee_schedule_assignment_no_overlap",
        ),
        Index(
            "ix_employee_schedule_assignment_tenant",
            "tenant_id",
        ),
        Index(
            "ix_employee_schedule_assignment_employee",
            "tenant_id",
            "employee_id",
        ),
        Index(
            "ix_employee_schedule_assignment_effective_dates",
            "tenant_id",
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
        ForeignKey("tenant.id", ondelete="RESTRICT"),
        nullable=False,
    )

    employee_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
    )

    work_schedule_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
    )

    effective_from: Mapped[date] = mapped_column(
    Date,
    nullable=False,
    )

    effective_to: Mapped[date | None] = mapped_column(
        Date,
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

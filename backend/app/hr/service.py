from __future__ import annotations

from datetime import date, datetime, timezone
from uuid import UUID

from sqlalchemy.orm import Session
from app.hr.enums import EmploymentStatus
from app.hr.models import (
    Employee,
    EmploymentAssignment,
    EmploymentStatusHistory,
    EmploymentTerm,
    Person,
)
from app.organization.models import OrganizationUnit


class PersonService:
    """
    Application/service layer for Person operations.

    Responsibilities:
    - Enforce tenant isolation
    - Validate person data
    - Create and retrieve persons
    """

    def __init__(self, db: Session):
        self.db = db

    def create_person(
        self,
        *,
        tenant_id: UUID,
        person_number: str,
        first_name: str,
        middle_name: str | None = None,
        last_name: str,
        preferred_name: str | None = None,
        date_of_birth: date | None = None,
        gender=None,
        nationality_code: str | None = None,
        national_id_number: str | None = None,
        tax_identifier: str | None = None,
    ) -> Person:

        existing = (
            self.db.query(Person)
            .filter(
                Person.tenant_id == tenant_id,
                Person.person_number == person_number,
            )
            .first()
        )

        if existing is not None:
            raise ValueError(
                "Person number already exists for this tenant."
            )

        person = Person(
            tenant_id=tenant_id,
            person_number=person_number,
            first_name=first_name,
            middle_name=middle_name,
            last_name=last_name,
            preferred_name=preferred_name,
            date_of_birth=date_of_birth,
            gender=gender,
            nationality_code=nationality_code,
            national_id_number=national_id_number,
            tax_identifier=tax_identifier,
        )

        self.db.add(person)
        self.db.flush()

        return person

    def get_person(
        self,
        *,
        tenant_id: UUID,
        person_id: UUID,
    ) -> Person:

        person = (
            self.db.query(Person)
            .filter(
                Person.id == person_id,
                Person.tenant_id == tenant_id,
            )
            .first()
        )

        if person is None:
            raise ValueError("Person not found.")

        return person


class EmployeeService:
    """
    Application/service layer for Employee operations.

    Responsibilities:
    - Enforce tenant isolation
    - Validate person ownership
    - Validate employment dates
    - Create and retrieve employees
    """

    def __init__(self, db: Session):
        self.db = db

    def _get_person(
        self,
        *,
        tenant_id: UUID,
        person_id: UUID,
    ) -> Person:

        person = (
            self.db.query(Person)
            .filter(
                Person.id == person_id,
                Person.tenant_id == tenant_id,
            )
            .first()
        )

        if person is None:
            raise ValueError(
                "Person not found for this tenant."
            )

        return person

    def _validate_employment_dates(
        self,
        *,
        hire_date: date,
        termination_date: date | None,
        employment_status,
        ) -> None:

        if (
            termination_date is not None
            and termination_date < hire_date
        ):
            raise ValueError(
                "termination_date must be on or after hire_date."
            )

        if (
            employment_status == EmploymentStatus.TERMINATED
            and termination_date is None
        ):
            raise ValueError(
                "termination_date is required for terminated employees."
            )

        if (
            employment_status == EmploymentStatus.TERMINATED
            and termination_date != hire_date
        ):
            raise ValueError(
                "TERMINATED employees must have termination_date equal to hire_date."
            )

        if (
            employment_status != EmploymentStatus.TERMINATED
            and termination_date is not None
        ):
            raise ValueError(
                "termination_date is only allowed for terminated employees."
            )

    def create_employee(
        self,
        *,
        tenant_id: UUID,
        person_id: UUID,
        employee_number: str,
        employment_status,
        employment_type,
        hire_date: date,
        termination_date: date | None = None,
        termination_reason: str | None = None,
    ) -> Employee:

        self._get_person(
            tenant_id=tenant_id,
            person_id=person_id,
        )

        self._validate_employment_dates(
            hire_date=hire_date,
            termination_date=termination_date,
            employment_status=employment_status,
        )

        existing = (
            self.db.query(Employee)
            .filter(
                Employee.tenant_id == tenant_id,
                Employee.employee_number == employee_number,
            )
            .first()
        )

        if existing is not None:
            raise ValueError(
                "Employee number already exists for this tenant."
            )

        employee = Employee(
            tenant_id=tenant_id,
            person_id=person_id,
            employee_number=employee_number,
            employment_status=employment_status,
            employment_type=employment_type,
            hire_date=hire_date,
            termination_date=termination_date,
            termination_reason=termination_reason,
        )

        self.db.add(employee)
        self.db.flush()

        initial_status_effective_from = datetime.combine(
            hire_date,
            datetime.min.time(),
            tzinfo=timezone.utc,
        )

        initial_status = EmploymentStatusHistory(
            tenant_id=tenant_id,
            employee_id=employee.id,
            status=employment_status,
            effective_from=initial_status_effective_from,
            effective_to=None,
            reason="Initial employment status",
        )

        self.db.add(initial_status)
        self.db.flush()

        return employee

    def get_employee(
        self,
        *,
        tenant_id: UUID,
        employee_id: UUID,
    ) -> Employee:

        employee = (
            self.db.query(Employee)
            .filter(
                Employee.id == employee_id,
                Employee.tenant_id == tenant_id,
            )
            .first()
        )

        if employee is None:
            raise ValueError("Employee not found.")

        return employee




class EmploymentStatusHistoryService:
    """
    Application/service layer for employee employment-status lifecycle.

    Responsibilities:
    - Enforce tenant isolation
    - Validate employee ownership
    - Create the initial status history
    - Perform controlled status transitions
    - Keep Employee.employment_status synchronized
    - Provide current/history status queries

    PostgreSQL remains the final authority for preventing
    overlapping status-history intervals.
    """

    def __init__(self, db: Session):
        self.db = db

    def _get_employee(
        self,
        *,
        tenant_id: UUID,
        employee_id: UUID,
    ) -> Employee:

        employee = (
            self.db.query(Employee)
            .filter(
                Employee.id == employee_id,
                Employee.tenant_id == tenant_id,
            )
            .first()
        )

        if employee is None:
            raise ValueError(
                "Employee not found for this tenant."
            )

        return employee

    def _validate_effective_dates(
        self,
        *,
        effective_from: datetime,
        effective_to: datetime | None,
    ) -> None:

        if (
            effective_to is not None
            and effective_to <= effective_from
        ):
            raise ValueError(
                "effective_to must be later than effective_from."
            )

    
    def transition_status(
        self,
        *,
        tenant_id: UUID,
        employee_id: UUID,
        status,
        effective_from: datetime,
        reason: str | None = None,
    ) -> EmploymentStatusHistory:

        employee = self._get_employee(
            tenant_id=tenant_id,
            employee_id=employee_id,
        )

        if employee.employment_status == EmploymentStatus.TERMINATED:
            raise ValueError(
                "Terminated employees cannot undergo further status transitions."
        )

        if effective_from.tzinfo is None:
            raise ValueError(
                "effective_from must be timezone-aware."
            )

        now = datetime.now(timezone.utc)

        if effective_from > now:
            raise ValueError(
                "effective_from cannot be in the future."
            )

        latest_history = (
            self.db.query(EmploymentStatusHistory)
            .filter(
                EmploymentStatusHistory.tenant_id == tenant_id,
                EmploymentStatusHistory.employee_id == employee_id,
            )
            .order_by(
                EmploymentStatusHistory.effective_from.desc()
            )
            .first()
        )

        if latest_history is None:
            raise ValueError(
                "No employment status history exists for this employee."
            )

        if effective_from <= latest_history.effective_from:
            raise ValueError(
                "effective_from must be later than the current status period start."
            )

        current_history = (
            self.db.query(EmploymentStatusHistory)
            .filter(
                EmploymentStatusHistory.tenant_id == tenant_id,
                EmploymentStatusHistory.employee_id == employee_id,
                EmploymentStatusHistory.effective_from <= effective_from,
                (
                    (EmploymentStatusHistory.effective_to.is_(None))
                    | (
                        EmploymentStatusHistory.effective_to
                        > effective_from
                    )
                ),
            )
            .order_by(
                EmploymentStatusHistory.effective_from.desc()
            )
            .first()
        )

        if current_history is None:
            raise ValueError(
                "No employment status history exists for this employee."
            )

        if current_history.status == status:
            raise ValueError(
                "Employee already has this employment status."
            )

        current_history.effective_to = effective_from

        new_history = EmploymentStatusHistory(
            tenant_id=tenant_id,
            employee_id=employee_id,
            status=status,
            effective_from=effective_from,
            effective_to=None,
            reason=reason,
        )

        self.db.add(new_history)

        employee.employment_status = status

        if status == EmploymentStatus.TERMINATED:
            employee.termination_date = effective_from.date()
            employee.termination_reason = reason

        self.db.flush()

        return new_history



    def get_current_status(
        self,
        *,
        tenant_id: UUID,
        employee_id: UUID,
        at: datetime | None = None,
    ) -> EmploymentStatusHistory | None:

        self._get_employee(
            tenant_id=tenant_id,
            employee_id=employee_id,
        )

        current_at = at or datetime.now(timezone.utc)

        return (
            self.db.query(EmploymentStatusHistory)
            .filter(
                EmploymentStatusHistory.tenant_id == tenant_id,
                EmploymentStatusHistory.employee_id == employee_id,
                EmploymentStatusHistory.effective_from <= current_at,
                (
                    (EmploymentStatusHistory.effective_to.is_(None))
                    | (
                        EmploymentStatusHistory.effective_to
                        > current_at
                    )
                ),
            )
            .order_by(
                EmploymentStatusHistory.effective_from.desc()
            )
            .first()
        )

    def get_status_history(
        self,
        *,
        tenant_id: UUID,
        employee_id: UUID,
    ) -> list[EmploymentStatusHistory]:

        self._get_employee(
            tenant_id=tenant_id,
            employee_id=employee_id,
        )

        return (
            self.db.query(EmploymentStatusHistory)
            .filter(
                EmploymentStatusHistory.tenant_id == tenant_id,
                EmploymentStatusHistory.employee_id == employee_id,
            )
            .order_by(
                EmploymentStatusHistory.effective_from.desc()
            )
            .all()
        )





class EmploymentAssignmentService:
    """
    Application/service layer for employment assignments.

    Responsibilities:
    - Enforce tenant isolation
    - Validate employee ownership
    - Validate organization-unit ownership
    - Validate manager ownership
    - Prevent self-management
    - Validate effective dates
    - Provide current/history assignment queries

    PostgreSQL remains the final authority for preventing
    overlapping assignment intervals.
    """

    def __init__(self, db: Session):
        self.db = db

    def _get_employee(
        self,
        *,
        tenant_id: UUID,
        employee_id: UUID,
    ) -> Employee:

        employee = (
            self.db.query(Employee)
            .filter(
                Employee.id == employee_id,
                Employee.tenant_id == tenant_id,
            )
            .first()
        )

        if employee is None:
            raise ValueError(
                "Employee not found for this tenant."
            )

        return employee

    def _get_organization_unit(
        self,
        *,
        tenant_id: UUID,
        organization_unit_id: UUID,
    ) -> OrganizationUnit:

        unit = (
            self.db.query(OrganizationUnit)
            .filter(
                OrganizationUnit.id == organization_unit_id,
                OrganizationUnit.tenant_id == tenant_id,
            )
            .first()
        )

        if unit is None:
            raise ValueError(
                "Organization unit not found for this tenant."
            )

        return unit

    def _validate_effective_dates(
        self,
        *,
        effective_from: datetime,
        effective_to: datetime | None,
    ) -> None:

        if (
            effective_to is not None
            and effective_to <= effective_from
        ):
            raise ValueError(
                "effective_to must be later than effective_from."
            )

    def _validate_manager(
        self,
        *,
        tenant_id: UUID,
        employee_id: UUID,
        manager_employee_id: UUID | None,
    ) -> None:

        if manager_employee_id is None:
            return

        if manager_employee_id == employee_id:
            raise ValueError(
                "An employee cannot be their own manager."
            )

        manager = (
            self.db.query(Employee)
            .filter(
                Employee.id == manager_employee_id,
                Employee.tenant_id == tenant_id,
            )
            .first()
        )

        if manager is None:
            raise ValueError(
                "Manager employee not found for this tenant."
            )

    def create_assignment(
        self,
        *,
        tenant_id: UUID,
        employee_id: UUID,
        organization_unit_id: UUID,
        job_title: str,
        effective_from: datetime,
        effective_to: datetime | None = None,
        manager_employee_id: UUID | None = None,
    ) -> EmploymentAssignment:

        self._get_employee(
            tenant_id=tenant_id,
            employee_id=employee_id,
        )

        self._get_organization_unit(
            tenant_id=tenant_id,
            organization_unit_id=organization_unit_id,
        )

        self._validate_manager(
            tenant_id=tenant_id,
            employee_id=employee_id,
            manager_employee_id=manager_employee_id,
        )

        self._validate_effective_dates(
            effective_from=effective_from,
            effective_to=effective_to,
        )

        assignment = EmploymentAssignment(
            tenant_id=tenant_id,
            employee_id=employee_id,
            organization_unit_id=organization_unit_id,
            job_title=job_title,
            manager_employee_id=manager_employee_id,
            effective_from=effective_from,
            effective_to=effective_to,
        )

        self.db.add(assignment)
        self.db.flush()

        return assignment

    def get_assignment(
        self,
        *,
        tenant_id: UUID,
        assignment_id: UUID,
    ) -> EmploymentAssignment:

        assignment = (
            self.db.query(EmploymentAssignment)
            .filter(
                EmploymentAssignment.id == assignment_id,
                EmploymentAssignment.tenant_id == tenant_id,
            )
            .first()
        )

        if assignment is None:
            raise ValueError(
                "Employment assignment not found."
            )

        return assignment

    def get_current_assignment(
        self,
        *,
        tenant_id: UUID,
        employee_id: UUID,
        at: datetime | None = None,
    ) -> EmploymentAssignment | None:

        self._get_employee(
            tenant_id=tenant_id,
            employee_id=employee_id,
        )

        current_at = at or datetime.now(timezone.utc)

        return (
            self.db.query(EmploymentAssignment)
            .filter(
                EmploymentAssignment.tenant_id == tenant_id,
                EmploymentAssignment.employee_id == employee_id,
                EmploymentAssignment.effective_from <= current_at,
                (
                    (EmploymentAssignment.effective_to.is_(None))
                    | (
                        EmploymentAssignment.effective_to
                        > current_at
                    )
                ),
            )
            .order_by(
                EmploymentAssignment.effective_from.desc()
            )
            .first()
        )

    def get_assignment_history(
        self,
        *,
        tenant_id: UUID,
        employee_id: UUID,
    ) -> list[EmploymentAssignment]:

        self._get_employee(
            tenant_id=tenant_id,
            employee_id=employee_id,
        )

        return (
            self.db.query(EmploymentAssignment)
            .filter(
                EmploymentAssignment.tenant_id == tenant_id,
                EmploymentAssignment.employee_id == employee_id,
            )
            .order_by(
                EmploymentAssignment.effective_from.desc()
            )
            .all()
        )




class EmploymentTermService:
    """
    Application/service layer for employment compensation terms.

    Responsibilities:
    - Enforce tenant isolation
    - Validate employee ownership
    - Validate effective dates
    - Create and retrieve employment terms
    - Provide current/history employment-term queries

    PostgreSQL remains the final authority for preventing
    overlapping employment-term intervals.
    """

    def __init__(self, db: Session):
        self.db = db

    def _get_employee(
        self,
        *,
        tenant_id: UUID,
        employee_id: UUID,
    ) -> Employee:

        employee = (
            self.db.query(Employee)
            .filter(
                Employee.id == employee_id,
                Employee.tenant_id == tenant_id,
            )
            .first()
        )

        if employee is None:
            raise ValueError(
                "Employee not found for this tenant."
            )

        return employee

    def _validate_effective_dates(
        self,
        *,
        effective_from: datetime,
        effective_to: datetime | None,
    ) -> None:

        if (
            effective_to is not None
            and effective_to <= effective_from
        ):
            raise ValueError(
                "effective_to must be later than effective_from."
            )

    def create_term(
        self,
        *,
        tenant_id: UUID,
        employee_id: UUID,
        effective_from: datetime,
        effective_to: datetime | None = None,
        pay_frequency,
        compensation_basis,
        currency_code: str,
        amount,
    ) -> EmploymentTerm:

        self._get_employee(
            tenant_id=tenant_id,
            employee_id=employee_id,
        )

        self._validate_effective_dates(
            effective_from=effective_from,
            effective_to=effective_to,
        )

        if amount <= 0:
            raise ValueError(
                "amount must be greater than zero."
            )

        if len(currency_code) != 3:
            raise ValueError(
                "currency_code must contain exactly 3 characters."
            )

        term = EmploymentTerm(
            tenant_id=tenant_id,
            employee_id=employee_id,
            effective_from=effective_from,
            effective_to=effective_to,
            pay_frequency=pay_frequency,
            compensation_basis=compensation_basis,
            currency_code=currency_code.upper(),
            amount=amount,
        )

        self.db.add(term)
        self.db.flush()

        return term

    def get_term(
        self,
        *,
        tenant_id: UUID,
        term_id: UUID,
    ) -> EmploymentTerm:

        term = (
            self.db.query(EmploymentTerm)
            .filter(
                EmploymentTerm.id == term_id,
                EmploymentTerm.tenant_id == tenant_id,
            )
            .first()
        )

        if term is None:
            raise ValueError(
                "Employment term not found."
            )

        return term

    def get_current_term(
        self,
        *,
        tenant_id: UUID,
        employee_id: UUID,
        at: datetime | None = None,
    ) -> EmploymentTerm | None:

        self._get_employee(
            tenant_id=tenant_id,
            employee_id=employee_id,
        )

        current_at = at or datetime.now(timezone.utc)

        return (
            self.db.query(EmploymentTerm)
            .filter(
                EmploymentTerm.tenant_id == tenant_id,
                EmploymentTerm.employee_id == employee_id,
                EmploymentTerm.effective_from <= current_at,
                (
                    (EmploymentTerm.effective_to.is_(None))
                    | (
                        EmploymentTerm.effective_to
                        > current_at
                    )
                ),
            )
            .order_by(
                EmploymentTerm.effective_from.desc()
            )
            .first()
        )

    def get_term_history(
        self,
        *,
        tenant_id: UUID,
        employee_id: UUID,
    ) -> list[EmploymentTerm]:

        self._get_employee(
            tenant_id=tenant_id,
            employee_id=employee_id,
        )

        return (
            self.db.query(EmploymentTerm)
            .filter(
                EmploymentTerm.tenant_id == tenant_id,
                EmploymentTerm.employee_id == employee_id,
            )
            .order_by(
                EmploymentTerm.effective_from.desc()
            )
            .all()
        )
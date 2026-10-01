from __future__ import annotations

from datetime import date, datetime, timezone
from uuid import UUID

from sqlalchemy.orm import Session

from app.hr.models import Employee, EmploymentAssignment, Person
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
    ) -> None:

        if (
            termination_date is not None
            and termination_date < hire_date
        ):
            raise ValueError(
                "termination_date must be on or after hire_date."
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
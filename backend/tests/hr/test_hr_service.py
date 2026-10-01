from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from uuid import uuid4
from sqlalchemy.exc import IntegrityError
import pytest

from app.hr.enums import (
    CompensationBasis,
    EmploymentStatus,
    EmploymentType,
    Gender,
    PayFrequency,
)


from app.hr.service import (
    EmployeeService,
    EmploymentAssignmentService,
    EmploymentTermService,
    PersonService,
)

from app.organization.models import LegalEntity, OrganizationUnit, Tenant
from app.organization.enums import (
    OrganizationUnitStatus,
    OrganizationUnitType,
    TenantStatus,
)


def create_tenant(db, legal_name: str) -> Tenant:
    tenant = Tenant(
        legal_name=legal_name,
        country_code="KE",
        timezone="Africa/Nairobi",
        currency_code="KES",
        status=TenantStatus.ACTIVE,
    )

    db.add(tenant)
    db.flush()

    return tenant


def create_organization_unit(db, tenant_id):
    unit = OrganizationUnit(
        tenant_id=tenant_id,
        code=f"HR-{uuid4().hex[:8]}",
        name="Human Resources",
        unit_type=OrganizationUnitType.DEPARTMENT,
        status=OrganizationUnitStatus.ACTIVE,
        effective_from=datetime(
            2026,
            1,
            1,
            tzinfo=timezone.utc,
        ),
    )

    db.add(unit)
    db.flush()

    return unit


def test_create_and_get_person(db):
    tenant = create_tenant(db, "Person Test Ltd")

    service = PersonService(db)

    person = service.create_person(
        tenant_id=tenant.id,
        person_number="P-0001",
        first_name="Peter",
        middle_name="John",
        last_name="Mbuthia",
        preferred_name="Peter",
        date_of_birth=date(1995, 1, 1),
        gender=Gender.MALE,
        nationality_code="KE",
        national_id_number="12345678",
        tax_identifier="A123456789X",
    )

    assert person.id is not None
    assert person.tenant_id == tenant.id
    assert person.person_number == "P-0001"

    fetched = service.get_person(
        tenant_id=tenant.id,
        person_id=person.id,
    )

    assert fetched.id == person.id


def test_person_cannot_be_retrieved_from_another_tenant(db):
    tenant_a = create_tenant(db, "Tenant A")
    tenant_b = create_tenant(db, "Tenant B")

    service = PersonService(db)

    person = service.create_person(
        tenant_id=tenant_a.id,
        person_number="P-0001",
        first_name="Alice",
        last_name="Kamau",
    )

    with pytest.raises(ValueError, match="Person not found"):
        service.get_person(
            tenant_id=tenant_b.id,
            person_id=person.id,
        )


def test_create_employee_requires_same_tenant_person(db):
    tenant_a = create_tenant(db, "Employer A")
    tenant_b = create_tenant(db, "Employer B")

    person_service = PersonService(db)
    employee_service = EmployeeService(db)

    person = person_service.create_person(
        tenant_id=tenant_a.id,
        person_number="P-0001",
        first_name="John",
        last_name="Doe",
    )

    with pytest.raises(
        ValueError,
        match="Person not found for this tenant",
    ):
        employee_service.create_employee(
            tenant_id=tenant_b.id,
            person_id=person.id,
            employee_number="EMP-0001",
            employment_status=EmploymentStatus.ACTIVE,
            employment_type=EmploymentType.PERMANENT,
            hire_date=date(2026, 1, 1),
        )


def test_create_employee_and_reject_invalid_termination_date(db):
    tenant = create_tenant(db, "Employee Test Ltd")

    person_service = PersonService(db)
    employee_service = EmployeeService(db)

    person = person_service.create_person(
        tenant_id=tenant.id,
        person_number="P-0001",
        first_name="Mary",
        last_name="Wanjiku",
    )

    with pytest.raises(
        ValueError,
        match="termination_date must be on or after hire_date",
    ):
        employee_service.create_employee(
            tenant_id=tenant.id,
            person_id=person.id,
            employee_number="EMP-0001",
            employment_status=EmploymentStatus.TERMINATED,
            employment_type=EmploymentType.PERMANENT,
            hire_date=date(2026, 6, 1),
            termination_date=date(2026, 5, 1),
        )

    employee = employee_service.create_employee(
        tenant_id=tenant.id,
        person_id=person.id,
        employee_number="EMP-0001",
        employment_status=EmploymentStatus.ACTIVE,
        employment_type=EmploymentType.PERMANENT,
        hire_date=date(2026, 1, 1),
    )

    assert employee.employee_number == "EMP-0001"


def test_assignment_requires_same_tenant_dependencies(db):
    tenant_a = create_tenant(db, "Assignment A")
    tenant_b = create_tenant(db, "Assignment B")

    person_service = PersonService(db)
    employee_service = EmployeeService(db)
    assignment_service = EmploymentAssignmentService(db)

    person = person_service.create_person(
        tenant_id=tenant_a.id,
        person_number="P-0001",
        first_name="John",
        last_name="Kamau",
    )

    employee = employee_service.create_employee(
        tenant_id=tenant_a.id,
        person_id=person.id,
        employee_number="EMP-0001",
        employment_status=EmploymentStatus.ACTIVE,
        employment_type=EmploymentType.PERMANENT,
        hire_date=date(2026, 1, 1),
    )

    foreign_unit = create_organization_unit(
        db,
        tenant_b.id,
    )

    with pytest.raises(
        ValueError,
        match="Organization unit not found for this tenant",
    ):
        assignment_service.create_assignment(
            tenant_id=tenant_a.id,
            employee_id=employee.id,
            organization_unit_id=foreign_unit.id,
            job_title="Systems Administrator",
            effective_from=datetime(
                2026,
                1,
                1,
                tzinfo=timezone.utc,
            ),
        )


def test_assignment_rejects_self_manager(db):
    tenant = create_tenant(db, "Manager Test Ltd")

    person_service = PersonService(db)
    employee_service = EmployeeService(db)
    assignment_service = EmploymentAssignmentService(db)

    person = person_service.create_person(
        tenant_id=tenant.id,
        person_number="P-0001",
        first_name="Jane",
        last_name="Njeri",
    )

    employee = employee_service.create_employee(
        tenant_id=tenant.id,
        person_id=person.id,
        employee_number="EMP-0001",
        employment_status=EmploymentStatus.ACTIVE,
        employment_type=EmploymentType.PERMANENT,
        hire_date=date(2026, 1, 1),
    )

    unit = create_organization_unit(db, tenant.id)

    with pytest.raises(
        ValueError,
        match="cannot be their own manager",
    ):
        assignment_service.create_assignment(
            tenant_id=tenant.id,
            employee_id=employee.id,
            organization_unit_id=unit.id,
            job_title="Systems Administrator",
            manager_employee_id=employee.id,
            effective_from=datetime(
                2026,
                1,
                1,
                tzinfo=timezone.utc,
            ),
        )


def test_current_assignment_and_history(db):
    tenant = create_tenant(db, "Assignment History Ltd")

    person_service = PersonService(db)
    employee_service = EmployeeService(db)
    assignment_service = EmploymentAssignmentService(db)

    person = person_service.create_person(
        tenant_id=tenant.id,
        person_number="P-0001",
        first_name="David",
        last_name="Otieno",
    )

    employee = employee_service.create_employee(
        tenant_id=tenant.id,
        person_id=person.id,
        employee_number="EMP-0001",
        employment_status=EmploymentStatus.ACTIVE,
        employment_type=EmploymentType.PERMANENT,
        hire_date=date(2026, 1, 1),
    )

    unit = create_organization_unit(db, tenant.id)

    first_assignment = assignment_service.create_assignment(
        tenant_id=tenant.id,
        employee_id=employee.id,
        organization_unit_id=unit.id,
        job_title="IT Support Specialist",
        effective_from=datetime(
            2026,
            1,
            1,
            tzinfo=timezone.utc,
        ),
        effective_to=datetime(
            2026,
            6,
            1,
            tzinfo=timezone.utc,
        ),
    )

    second_assignment = assignment_service.create_assignment(
        tenant_id=tenant.id,
        employee_id=employee.id,
        organization_unit_id=unit.id,
        job_title="Infrastructure Engineer",
        effective_from=datetime(
            2026,
            6,
            1,
            tzinfo=timezone.utc,
        ),
    )

    current = assignment_service.get_current_assignment(
        tenant_id=tenant.id,
        employee_id=employee.id,
        at=datetime(
            2026,
            8,
            1,
            tzinfo=timezone.utc,
        ),
    )

    assert current is not None
    assert current.id == second_assignment.id

    history = assignment_service.get_assignment_history(
        tenant_id=tenant.id,
        employee_id=employee.id,
    )

    assert len(history) == 2
    assert history[0].id == second_assignment.id
    assert history[1].id == first_assignment.id


def test_database_rejects_overlapping_assignments(db):
    tenant = create_tenant(db, "Overlap Test Ltd")

    person_service = PersonService(db)
    employee_service = EmployeeService(db)
    assignment_service = EmploymentAssignmentService(db)

    person = person_service.create_person(
        tenant_id=tenant.id,
        person_number="P-0001",
        first_name="Susan",
        last_name="Achieng",
    )

    employee = employee_service.create_employee(
        tenant_id=tenant.id,
        person_id=person.id,
        employee_number="EMP-0001",
        employment_status=EmploymentStatus.ACTIVE,
        employment_type=EmploymentType.PERMANENT,
        hire_date=date(2026, 1, 1),
    )

    unit = create_organization_unit(db, tenant.id)

    assignment_service.create_assignment(
        tenant_id=tenant.id,
        employee_id=employee.id,
        organization_unit_id=unit.id,
        job_title="Network Administrator",
        effective_from=datetime(
            2026,
            1,
            1,
            tzinfo=timezone.utc,
        ),
        effective_to=datetime(
            2026,
            6,
            1,
            tzinfo=timezone.utc,
        ),
    )

    
    with pytest.raises(
        IntegrityError,
        match="ex_employment_assignment_no_overlap",
        ):
        assignment_service.create_assignment(
            tenant_id=tenant.id,
            employee_id=employee.id,
            organization_unit_id=unit.id,
            job_title="Security Engineer",
            effective_from=datetime(
                2026,
                5,
                1,
                tzinfo=timezone.utc,
            ),
            effective_to=datetime(
                2026,
                7,
                1,
                tzinfo=timezone.utc,
            ),
        )



def test_employment_term_requires_same_tenant_employee(db):
    tenant_a = create_tenant(db, "Compensation A")
    tenant_b = create_tenant(db, "Compensation B")

    person_service = PersonService(db)
    employee_service = EmployeeService(db)
    term_service = EmploymentTermService(db)

    person = person_service.create_person(
        tenant_id=tenant_a.id,
        person_number="P-0001",
        first_name="John",
        last_name="Kamau",
    )

    employee = employee_service.create_employee(
        tenant_id=tenant_a.id,
        person_id=person.id,
        employee_number="EMP-0001",
        employment_status=EmploymentStatus.ACTIVE,
        employment_type=EmploymentType.PERMANENT,
        hire_date=date(2026, 1, 1),
    )

    with pytest.raises(
        ValueError,
        match="Employee not found for this tenant",
    ):
        term_service.create_term(
            tenant_id=tenant_b.id,
            employee_id=employee.id,
            effective_from=datetime(
                2026,
                1,
                1,
                tzinfo=timezone.utc,
            ),
            pay_frequency=PayFrequency.MONTHLY,
            compensation_basis=CompensationBasis.SALARY,
            currency_code="KES",
            amount=Decimal("150000.00"),
        )


def test_create_and_get_employment_term(db):
    tenant = create_tenant(db, "Employment Term Ltd")

    person_service = PersonService(db)
    employee_service = EmployeeService(db)
    term_service = EmploymentTermService(db)

    person = person_service.create_person(
        tenant_id=tenant.id,
        person_number="P-0001",
        first_name="Peter",
        last_name="Mbuthia",
    )

    employee = employee_service.create_employee(
        tenant_id=tenant.id,
        person_id=person.id,
        employee_number="EMP-0001",
        employment_status=EmploymentStatus.ACTIVE,
        employment_type=EmploymentType.PERMANENT,
        hire_date=date(2026, 1, 1),
    )

    term = term_service.create_term(
        tenant_id=tenant.id,
        employee_id=employee.id,
        effective_from=datetime(
            2026,
            1,
            1,
            tzinfo=timezone.utc,
        ),
        pay_frequency=PayFrequency.MONTHLY,
        compensation_basis=CompensationBasis.SALARY,
        currency_code="KES",
        amount=Decimal("150000.00"),
    )

    assert term.id is not None
    assert term.tenant_id == tenant.id
    assert term.employee_id == employee.id
    assert term.pay_frequency == PayFrequency.MONTHLY
    assert term.compensation_basis == CompensationBasis.SALARY
    assert term.currency_code == "KES"
    assert term.amount == Decimal("150000.00")

    fetched = term_service.get_term(
        tenant_id=tenant.id,
        term_id=term.id,
    )

    assert fetched.id == term.id


def test_employment_term_rejects_invalid_effective_dates(db):
    tenant = create_tenant(db, "Term Dates Ltd")

    person_service = PersonService(db)
    employee_service = EmployeeService(db)
    term_service = EmploymentTermService(db)

    person = person_service.create_person(
        tenant_id=tenant.id,
        person_number="P-0001",
        first_name="Mary",
        last_name="Wanjiku",
    )

    employee = employee_service.create_employee(
        tenant_id=tenant.id,
        person_id=person.id,
        employee_number="EMP-0001",
        employment_status=EmploymentStatus.ACTIVE,
        employment_type=EmploymentType.PERMANENT,
        hire_date=date(2026, 1, 1),
    )

    with pytest.raises(
        ValueError,
        match="effective_to must be later than effective_from",
    ):
        term_service.create_term(
            tenant_id=tenant.id,
            employee_id=employee.id,
            effective_from=datetime(
                2026,
                6,
                1,
                tzinfo=timezone.utc,
            ),
            effective_to=datetime(
                2026,
                5,
                1,
                tzinfo=timezone.utc,
            ),
            pay_frequency=PayFrequency.MONTHLY,
            compensation_basis=CompensationBasis.SALARY,
            currency_code="KES",
            amount=Decimal("150000.00"),
        )


def test_employment_term_rejects_non_positive_amount(db):
    tenant = create_tenant(db, "Term Amount Ltd")

    person_service = PersonService(db)
    employee_service = EmployeeService(db)
    term_service = EmploymentTermService(db)

    person = person_service.create_person(
        tenant_id=tenant.id,
        person_number="P-0001",
        first_name="David",
        last_name="Otieno",
    )

    employee = employee_service.create_employee(
        tenant_id=tenant.id,
        person_id=person.id,
        employee_number="EMP-0001",
        employment_status=EmploymentStatus.ACTIVE,
        employment_type=EmploymentType.PERMANENT,
        hire_date=date(2026, 1, 1),
    )

    with pytest.raises(
        ValueError,
        match="amount must be greater than zero",
    ):
        term_service.create_term(
            tenant_id=tenant.id,
            employee_id=employee.id,
            effective_from=datetime(
                2026,
                1,
                1,
                tzinfo=timezone.utc,
            ),
            pay_frequency=PayFrequency.MONTHLY,
            compensation_basis=CompensationBasis.SALARY,
            currency_code="KES",
            amount=Decimal("0.00"),
        )


def test_current_employment_term_and_history(db):
    tenant = create_tenant(db, "Term History Ltd")

    person_service = PersonService(db)
    employee_service = EmployeeService(db)
    term_service = EmploymentTermService(db)

    person = person_service.create_person(
        tenant_id=tenant.id,
        person_number="P-0001",
        first_name="Susan",
        last_name="Achieng",
    )

    employee = employee_service.create_employee(
        tenant_id=tenant.id,
        person_id=person.id,
        employee_number="EMP-0001",
        employment_status=EmploymentStatus.ACTIVE,
        employment_type=EmploymentType.PERMANENT,
        hire_date=date(2026, 1, 1),
    )

    first_term = term_service.create_term(
        tenant_id=tenant.id,
        employee_id=employee.id,
        effective_from=datetime(
            2026,
            1,
            1,
            tzinfo=timezone.utc,
        ),
        effective_to=datetime(
            2026,
            6,
            1,
            tzinfo=timezone.utc,
        ),
        pay_frequency=PayFrequency.MONTHLY,
        compensation_basis=CompensationBasis.SALARY,
        currency_code="KES",
        amount=Decimal("120000.00"),
    )

    second_term = term_service.create_term(
        tenant_id=tenant.id,
        employee_id=employee.id,
        effective_from=datetime(
            2026,
            6,
            1,
            tzinfo=timezone.utc,
        ),
        pay_frequency=PayFrequency.MONTHLY,
        compensation_basis=CompensationBasis.SALARY,
        currency_code="KES",
        amount=Decimal("150000.00"),
    )

    current = term_service.get_current_term(
        tenant_id=tenant.id,
        employee_id=employee.id,
        at=datetime(
            2026,
            8,
            1,
            tzinfo=timezone.utc,
        ),
    )

    assert current is not None
    assert current.id == second_term.id
    assert current.amount == Decimal("150000.00")

    history = term_service.get_term_history(
        tenant_id=tenant.id,
        employee_id=employee.id,
    )

    assert len(history) == 2
    assert history[0].id == second_term.id
    assert history[1].id == first_term.id
    assert history[0].effective_from > history[1].effective_from


def test_database_rejects_overlapping_employment_terms(db):
    tenant = create_tenant(db, "Term Overlap Ltd")

    person_service = PersonService(db)
    employee_service = EmployeeService(db)
    term_service = EmploymentTermService(db)

    person = person_service.create_person(
        tenant_id=tenant.id,
        person_number="P-0001",
        first_name="Alice",
        last_name="Njeri",
    )

    employee = employee_service.create_employee(
        tenant_id=tenant.id,
        person_id=person.id,
        employee_number="EMP-0001",
        employment_status=EmploymentStatus.ACTIVE,
        employment_type=EmploymentType.PERMANENT,
        hire_date=date(2026, 1, 1),
    )

    term_service.create_term(
        tenant_id=tenant.id,
        employee_id=employee.id,
        effective_from=datetime(
            2026,
            1,
            1,
            tzinfo=timezone.utc,
        ),
        effective_to=datetime(
            2026,
            6,
            1,
            tzinfo=timezone.utc,
        ),
        pay_frequency=PayFrequency.MONTHLY,
        compensation_basis=CompensationBasis.SALARY,
        currency_code="KES",
        amount=Decimal("120000.00"),
    )

    with pytest.raises(
        IntegrityError,
        match="ex_employment_term_no_overlap",
    ):
        term_service.create_term(
            tenant_id=tenant.id,
            employee_id=employee.id,
            effective_from=datetime(
                2026,
                5,
                1,
                tzinfo=timezone.utc,
            ),
            effective_to=datetime(
                2026,
                7,
                1,
                tzinfo=timezone.utc,
            ),
            pay_frequency=PayFrequency.MONTHLY,
            compensation_basis=CompensationBasis.SALARY,
            currency_code="KES",
            amount=Decimal("150000.00"),
        )
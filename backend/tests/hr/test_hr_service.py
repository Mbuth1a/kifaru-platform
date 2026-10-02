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
    EmploymentStatusHistoryService,
)

from app.hr.models import EmploymentStatusHistory
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



def test_create_employee_creates_initial_status_history(db):
    tenant = create_tenant(db, "Status History Initial Ltd")

    person_service = PersonService(db)
    person = person_service.create_person(
        tenant_id=tenant.id,
        person_number="P-001",
        first_name="John",
        last_name="Doe",
    )

    employee_service = EmployeeService(db)

    employee = employee_service.create_employee(
        tenant_id=tenant.id,
        person_id=person.id,
        employee_number="EMP-001",
        employment_status=EmploymentStatus.ACTIVE,
        employment_type=EmploymentType.PERMANENT,
        hire_date=date(2026, 1, 15),
    )

    history_service = EmploymentStatusHistoryService(db)

    history = history_service.get_status_history(
        tenant_id=tenant.id,
        employee_id=employee.id,
    )

    assert len(history) == 1
    assert history[0].status == EmploymentStatus.ACTIVE
    assert history[0].effective_from == datetime(
        2026,
        1,
        15,
        tzinfo=timezone.utc,
    )
    assert history[0].effective_to is None
    assert history[0].reason == "Initial employment status"


def test_employee_status_transition_updates_projection_and_history(db):
    tenant = create_tenant(db, "Status Transition Ltd")

    person_service = PersonService(db)
    person = person_service.create_person(
        tenant_id=tenant.id,
        person_number="P-002",
        first_name="Jane",
        last_name="Doe",
    )

    employee_service = EmployeeService(db)

    employee = employee_service.create_employee(
        tenant_id=tenant.id,
        person_id=person.id,
        employee_number="EMP-002",
        employment_status=EmploymentStatus.ACTIVE,
        employment_type=EmploymentType.PERMANENT,
        hire_date=date(2026, 1, 1),
    )

    history_service = EmploymentStatusHistoryService(db)

    effective_from = datetime(
        2026,
        6,
        1,
        tzinfo=timezone.utc,
    )

    new_history = history_service.transition_status(
        tenant_id=tenant.id,
        employee_id=employee.id,
        status=EmploymentStatus.ON_LEAVE,
        effective_from=effective_from,
        reason="Approved leave",
    )

    db.refresh(employee)

    assert employee.employment_status == EmploymentStatus.ON_LEAVE

    assert new_history.status == EmploymentStatus.ON_LEAVE
    assert new_history.effective_from == effective_from
    assert new_history.effective_to is None

    history = history_service.get_status_history(
        tenant_id=tenant.id,
        employee_id=employee.id,
    )

    assert len(history) == 2

    current_history = history[0]
    previous_history = history[1]

    assert current_history.status == EmploymentStatus.ON_LEAVE
    assert previous_history.status == EmploymentStatus.ACTIVE
    assert previous_history.effective_to == effective_from


def test_current_employment_status(db):
    tenant = create_tenant(db, "Current Status Ltd")

    person_service = PersonService(db)
    person = person_service.create_person(
        tenant_id=tenant.id,
        person_number="P-003",
        first_name="Mary",
        last_name="Wanjiku",
    )

    employee_service = EmployeeService(db)

    employee = employee_service.create_employee(
        tenant_id=tenant.id,
        person_id=person.id,
        employee_number="EMP-003",
        employment_status=EmploymentStatus.ACTIVE,
        employment_type=EmploymentType.PERMANENT,
        hire_date=date(2026, 1, 1),
    )

    history_service = EmploymentStatusHistoryService(db)

    effective_from = datetime(
        2026,
        5,
        1,
        tzinfo=timezone.utc,
    )

    history_service.transition_status(
        tenant_id=tenant.id,
        employee_id=employee.id,
        status=EmploymentStatus.SUSPENDED,
        effective_from=effective_from,
        reason="Administrative suspension",
    )

    current = history_service.get_current_status(
        tenant_id=tenant.id,
        employee_id=employee.id,
        at=datetime(
            2026,
            6,
            1,
            tzinfo=timezone.utc,
        ),
    )

    assert current is not None
    assert current.status == EmploymentStatus.SUSPENDED


def test_status_transition_rejects_future_effective_date(db):
    tenant = create_tenant(db, "Future Status Ltd")

    person_service = PersonService(db)
    person = person_service.create_person(
        tenant_id=tenant.id,
        person_number="P-004",
        first_name="David",
        last_name="Kamau",
    )

    employee_service = EmployeeService(db)

    employee = employee_service.create_employee(
        tenant_id=tenant.id,
        person_id=person.id,
        employee_number="EMP-004",
        employment_status=EmploymentStatus.ACTIVE,
        employment_type=EmploymentType.PERMANENT,
        hire_date=date(2026, 1, 1),
    )

    history_service = EmploymentStatusHistoryService(db)

    future_date = datetime(
        2030,
        1,
        1,
        tzinfo=timezone.utc,
    )

    with pytest.raises(
        ValueError,
        match="effective_from cannot be in the future.",
    ):
        history_service.transition_status(
            tenant_id=tenant.id,
            employee_id=employee.id,
            status=EmploymentStatus.ON_LEAVE,
            effective_from=future_date,
        )


def test_status_transition_rejects_same_status(db):
    tenant = create_tenant(db, "Same Status Ltd")

    person_service = PersonService(db)
    person = person_service.create_person(
        tenant_id=tenant.id,
        person_number="P-005",
        first_name="Susan",
        last_name="Achieng",
    )

    employee_service = EmployeeService(db)

    employee = employee_service.create_employee(
        tenant_id=tenant.id,
        person_id=person.id,
        employee_number="EMP-005",
        employment_status=EmploymentStatus.ACTIVE,
        employment_type=EmploymentType.PERMANENT,
        hire_date=date(2026, 1, 1),
    )

    history_service = EmploymentStatusHistoryService(db)

    with pytest.raises(
        ValueError,
        match="Employee already has this employment status.",
    ):
        history_service.transition_status(
            tenant_id=tenant.id,
            employee_id=employee.id,
            status=EmploymentStatus.ACTIVE,
            effective_from=datetime(
                2026,
                6,
                1,
                tzinfo=timezone.utc,
            ),
        )





def test_status_transition_rejects_retroactive_change(
    db,
):
    tenant = create_tenant(
        db,
        "Retroactive Status Tenant",
    )

    person_service = PersonService(db)

    person = person_service.create_person(
        tenant_id=tenant.id,
        person_number="P-RETRO-001",
        first_name="Retro",
        last_name="Status",
    )

    employee_service = EmployeeService(db)

    employee = employee_service.create_employee(
        tenant_id=tenant.id,
        person_id=person.id,
        employee_number="EMP-RETRO-001",
        employment_status=EmploymentStatus.ACTIVE,
        employment_type=EmploymentType.PERMANENT,
        hire_date=date(2026, 1, 1),
    )

    status_service = EmploymentStatusHistoryService(db)

    status_service.transition_status(
        tenant_id=tenant.id,
        employee_id=employee.id,
        status=EmploymentStatus.ON_LEAVE,
        effective_from=datetime(
            2026,
            6,
            1,
            tzinfo=timezone.utc,
        ),
        reason="Approved leave",
    )

    with pytest.raises(
        ValueError,
        match="effective_from must be later than the current status period start.",
    ):
        status_service.transition_status(
            tenant_id=tenant.id,
            employee_id=employee.id,
            status=EmploymentStatus.SUSPENDED,
            effective_from=datetime(
                2026,
                5,
                1,
                tzinfo=timezone.utc,
            ),
            reason="Retroactive suspension",
        )




def test_create_employee_rejects_terminated_without_termination_date(
    db,
):
    tenant = create_tenant(
        db,
        "Termination Validation Tenant",
    )

    person_service = PersonService(db)

    person = person_service.create_person(
        tenant_id=tenant.id,
        person_number="P-TERM-001",
        first_name="Termination",
        last_name="Test",
    )

    employee_service = EmployeeService(db)

    with pytest.raises(
        ValueError,
        match="termination_date is required",
    ):
        employee_service.create_employee(
            tenant_id=tenant.id,
            person_id=person.id,
            employee_number="EMP-TERM-001",
            employment_status=EmploymentStatus.TERMINATED,
            employment_type=EmploymentType.PERMANENT,
            hire_date=date(2026, 1, 1),
        )






def test_create_employee_rejects_active_with_termination_date(
    db,
):
    tenant = create_tenant(
        db,
        "Active Termination Validation Tenant",
    )

    person_service = PersonService(db)

    person = person_service.create_person(
        tenant_id=tenant.id,
        person_number="P-ACTIVE-TERM-001",
        first_name="Active",
        last_name="Test",
    )

    employee_service = EmployeeService(db)

    with pytest.raises(
        ValueError,
        match="termination_date is only allowed for terminated employees",
    ):
        employee_service.create_employee(
            tenant_id=tenant.id,
            person_id=person.id,
            employee_number="EMP-ACTIVE-TERM-001",
            employment_status=EmploymentStatus.ACTIVE,
            employment_type=EmploymentType.PERMANENT,
            hire_date=date(2026, 1, 1),
            termination_date=date(2026, 8, 1),
        )



def test_status_transition_rejects_transition_from_terminated_employee(
    db,
):
    tenant = create_tenant(
        db,
        "Terminated Transition Tenant",
    )

    person_service = PersonService(db)

    person = person_service.create_person(
        tenant_id=tenant.id,
        person_number="P-TERM-STATUS-001",
        first_name="Terminated",
        last_name="Employee",
    )

    employee_service = EmployeeService(db)

    employee = employee_service.create_employee(
        tenant_id=tenant.id,
        person_id=person.id,
        employee_number="EMP-TERM-STATUS-001",
        employment_status=EmploymentStatus.ACTIVE,
        employment_type=EmploymentType.PERMANENT,
        hire_date=date(2026, 1, 1),
    )

    status_service = EmploymentStatusHistoryService(db)

    status_service.transition_status(
        tenant_id=tenant.id,
        employee_id=employee.id,
        status=EmploymentStatus.TERMINATED,
        effective_from=datetime(
            2026,
            6,
            1,
            tzinfo=timezone.utc,
        ),
        reason="Employment ended",
    )

    with pytest.raises(
        ValueError,
        match="Terminated employees cannot undergo further status transitions",
    ):
        status_service.transition_status(
            tenant_id=tenant.id,
            employee_id=employee.id,
            status=EmploymentStatus.ON_LEAVE,
            effective_from=datetime(
                2026,
            7,
            1,
            tzinfo=timezone.utc,
            ),
            reason="Invalid post-termination transition",
        )



def test_status_transition_to_terminated_is_allowed(
    db,
):
    tenant = create_tenant(
        db,
        "Termination Transition Tenant",
    )

    person_service = PersonService(db)

    person = person_service.create_person(
        tenant_id=tenant.id,
        person_number="P-TERM-TRANS-001",
        first_name="Termination",
        last_name="Transition",
    )

    employee_service = EmployeeService(db)

    employee = employee_service.create_employee(
        tenant_id=tenant.id,
        person_id=person.id,
        employee_number="EMP-TERM-TRANS-001",
        employment_status=EmploymentStatus.ACTIVE,
        employment_type=EmploymentType.PERMANENT,
        hire_date=date(2026, 1, 1),
    )

    status_service = EmploymentStatusHistoryService(db)

    effective_from = datetime(
        2026,
        6,
        1,
        tzinfo=timezone.utc,
    )

    history = status_service.transition_status(
        tenant_id=tenant.id,
        employee_id=employee.id,
        status=EmploymentStatus.TERMINATED,
        effective_from=effective_from,
        reason="Employment ended",
    )

    db.refresh(employee)

    assert employee.employment_status == EmploymentStatus.TERMINATED
    assert history.status == EmploymentStatus.TERMINATED
    assert history.effective_from == effective_from
    assert history.effective_to is None



def test_create_employee_rejects_terminated_with_later_termination_date(db):
    tenant = create_tenant(
        db,
        "Invalid Initial Termination Tenant",
    )

    person_service = PersonService(db)

    person = person_service.create_person(
        tenant_id=tenant.id,
        person_number="P-TERM-LATER-001",
        first_name="Invalid",
        last_name="Termination",
    )

    employee_service = EmployeeService(db)

    with pytest.raises(
        ValueError,
        match="TERMINATED employees must have termination_date equal to hire_date",
    ):
        employee_service.create_employee(
            tenant_id=tenant.id,
            person_id=person.id,
            employee_number="EMP-TERM-LATER-001",
            employment_status=EmploymentStatus.TERMINATED,
            employment_type=EmploymentType.PERMANENT,
            hire_date=date(2026, 1, 1),
            termination_date=date(2026, 6, 1),
            termination_reason="Employment ended",
        )





def test_create_employee_allows_terminated_on_hire_date(db):
    tenant = create_tenant(
        db,
        "Valid Initial Termination Tenant",
    )

    person_service = PersonService(db)

    person = person_service.create_person(
        tenant_id=tenant.id,
        person_number="P-TERM-SAME-001",
        first_name="Valid",
        last_name="Termination",
    )

    employee_service = EmployeeService(db)

    employee = employee_service.create_employee(
        tenant_id=tenant.id,
        person_id=person.id,
        employee_number="EMP-TERM-SAME-001",
        employment_status=EmploymentStatus.TERMINATED,
        employment_type=EmploymentType.PERMANENT,
        hire_date=date(2026, 6, 1),
        termination_date=date(2026, 6, 1),
        termination_reason="Employment ended on hire date",
    )

    assert employee.employment_status == EmploymentStatus.TERMINATED
    assert employee.hire_date == date(2026, 6, 1)
    assert employee.termination_date == date(2026, 6, 1)
    assert employee.termination_reason == "Employment ended on hire date"




def test_create_terminated_employee_creates_matching_status_history(db):
    tenant = create_tenant(
        db,
        "Initial Termination History Tenant",
    )

    person_service = PersonService(db)

    person = person_service.create_person(
        tenant_id=tenant.id,
        person_number="P-TERM-HISTORY-001",
        first_name="History",
        last_name="Termination",
    )

    employee_service = EmployeeService(db)

    employee = employee_service.create_employee(
        tenant_id=tenant.id,
        person_id=person.id,
        employee_number="EMP-TERM-HISTORY-001",
        employment_status=EmploymentStatus.TERMINATED,
        employment_type=EmploymentType.PERMANENT,
        hire_date=date(2026, 6, 1),
        termination_date=date(2026, 6, 1),
        termination_reason="Employment ended on hire date",
    )

    history = (
        db.query(EmploymentStatusHistory)
        .filter(
            EmploymentStatusHistory.tenant_id == tenant.id,
            EmploymentStatusHistory.employee_id == employee.id,
        )
        .one()
    )

    assert history.status == EmploymentStatus.TERMINATED
    assert history.effective_from == datetime(
        2026,
        6,
        1,
        tzinfo=timezone.utc,
    )
    assert history.effective_to is None
    assert history.reason == "Initial employment status"





def test_status_transition_to_terminated_updates_employee_termination_fields(db):
    tenant = create_tenant(
        db,
        "Termination Projection Tenant",
    )

    person_service = PersonService(db)

    person = person_service.create_person(
        tenant_id=tenant.id,
        person_number="P-TERM-PROJECTION-001",
        first_name="Projection",
        last_name="Termination",
    )

    employee_service = EmployeeService(db)

    employee = employee_service.create_employee(
        tenant_id=tenant.id,
        person_id=person.id,
        employee_number="EMP-TERM-PROJECTION-001",
        employment_status=EmploymentStatus.ACTIVE,
        employment_type=EmploymentType.PERMANENT,
        hire_date=date(2026, 1, 1),
    )

    status_service = EmploymentStatusHistoryService(db)

    effective_from = datetime(
        2026,
        6,
        15,
        14,
        30,
        tzinfo=timezone.utc,
    )

    status_service.transition_status(
        tenant_id=tenant.id,
        employee_id=employee.id,
        status=EmploymentStatus.TERMINATED,
        effective_from=effective_from,
        reason="Employment ended",
    )

    db.refresh(employee)

    assert employee.employment_status == EmploymentStatus.TERMINATED
    assert employee.termination_date == date(2026, 6, 15)
    assert employee.termination_reason == "Employment ended"



def test_status_transition_to_non_terminated_does_not_set_termination_fields(db):
    tenant = create_tenant(
        db,
        "Non Termination Projection Tenant",
    )

    person_service = PersonService(db)

    person = person_service.create_person(
        tenant_id=tenant.id,
        person_number="P-NON-TERM-001",
        first_name="Non",
        last_name="Termination",
    )

    employee_service = EmployeeService(db)

    employee = employee_service.create_employee(
        tenant_id=tenant.id,
        person_id=person.id,
        employee_number="EMP-NON-TERM-001",
        employment_status=EmploymentStatus.ACTIVE,
        employment_type=EmploymentType.PERMANENT,
        hire_date=date(2026, 1, 1),
    )

    status_service = EmploymentStatusHistoryService(db)

    status_service.transition_status(
        tenant_id=tenant.id,
        employee_id=employee.id,
        status=EmploymentStatus.ON_LEAVE,
        effective_from=datetime(
            2026,
            6,
            15,
            14,
            30,
            tzinfo=timezone.utc,
        ),
        reason="Employee went on leave",
    )

    db.refresh(employee)

    assert employee.employment_status == EmploymentStatus.ON_LEAVE
    assert employee.termination_date is None
    assert employee.termination_reason is None




def test_terminated_employee_projection_remains_unchanged_after_rejected_transition(db):
    tenant = create_tenant(
        db,
        "Termination Projection Integrity Tenant",
    )

    person_service = PersonService(db)

    person = person_service.create_person(
        tenant_id=tenant.id,
        person_number="P-TERM-INTEGRITY-001",
        first_name="Termination",
        last_name="Integrity",
    )

    employee_service = EmployeeService(db)

    employee = employee_service.create_employee(
        tenant_id=tenant.id,
        person_id=person.id,
        employee_number="EMP-TERM-INTEGRITY-001",
        employment_status=EmploymentStatus.ACTIVE,
        employment_type=EmploymentType.PERMANENT,
        hire_date=date(2026, 1, 1),
    )

    status_service = EmploymentStatusHistoryService(db)

    termination_date = datetime(
        2026,
        6,
        15,
        14,
        30,
        tzinfo=timezone.utc,
    )

    status_service.transition_status(
        tenant_id=tenant.id,
        employee_id=employee.id,
        status=EmploymentStatus.TERMINATED,
        effective_from=termination_date,
        reason="Employment ended",
    )

    db.refresh(employee)

    with pytest.raises(
        ValueError,
        match="Terminated employees cannot undergo further status transitions",
    ):
        status_service.transition_status(
            tenant_id=tenant.id,
            employee_id=employee.id,
            status=EmploymentStatus.ON_LEAVE,
            effective_from=datetime(
                2026,
                7,
                1,
                tzinfo=timezone.utc,
            ),
            reason="Invalid post-termination transition",
        )

    db.refresh(employee)

    assert employee.employment_status == EmploymentStatus.TERMINATED
    assert employee.termination_date == date(2026, 6, 15)
    assert employee.termination_reason == "Employment ended"


def test_status_transition_keeps_employee_projection_in_sync_with_latest_history(db):
    tenant = create_tenant(
        db,
        "Status Projection Sync Tenant",
    )

    person_service = PersonService(db)

    person = person_service.create_person(
        tenant_id=tenant.id,
        person_number="P-STATUS-SYNC-001",
        first_name="Status",
        last_name="Sync",
    )

    employee_service = EmployeeService(db)

    employee = employee_service.create_employee(
        tenant_id=tenant.id,
        person_id=person.id,
        employee_number="EMP-STATUS-SYNC-001",
        employment_status=EmploymentStatus.ACTIVE,
        employment_type=EmploymentType.PERMANENT,
        hire_date=date(2026, 1, 1),
    )

    status_service = EmploymentStatusHistoryService(db)

    effective_from = datetime(
        2026,
        6,
        15,
        14,
        30,
        tzinfo=timezone.utc,
    )

    status_service.transition_status(
        tenant_id=tenant.id,
        employee_id=employee.id,
        status=EmploymentStatus.ON_LEAVE,
        effective_from=effective_from,
        reason="Employee went on leave",
    )

    db.refresh(employee)

    latest_history = (
        db.query(EmploymentStatusHistory)
        .filter(
            EmploymentStatusHistory.tenant_id == tenant.id,
            EmploymentStatusHistory.employee_id == employee.id,
        )
        .order_by(
            EmploymentStatusHistory.effective_from.desc()
        )
        .first()
    )

    assert latest_history is not None
    assert employee.employment_status == latest_history.status


def test_multiple_status_transitions_keep_projection_in_sync(db):
    tenant = create_tenant(
        db,
        "Multiple Status Transition Tenant",
    )

    person_service = PersonService(db)

    person = person_service.create_person(
        tenant_id=tenant.id,
        person_number="P-MULTI-STATUS-001",
        first_name="Multiple",
        last_name="Status",
    )

    employee_service = EmployeeService(db)

    employee = employee_service.create_employee(
        tenant_id=tenant.id,
        person_id=person.id,
        employee_number="EMP-MULTI-STATUS-001",
        employment_status=EmploymentStatus.ACTIVE,
        employment_type=EmploymentType.PERMANENT,
        hire_date=date(2026, 1, 1),
    )

    status_service = EmploymentStatusHistoryService(db)

    transitions = [
        (
            EmploymentStatus.ON_LEAVE,
            datetime(2026, 3, 1, 9, 0, tzinfo=timezone.utc),
        ),
        (
            EmploymentStatus.ACTIVE,
            datetime(2026, 4, 1, 9, 0, tzinfo=timezone.utc),
        ),
        (
            EmploymentStatus.SUSPENDED,
            datetime(2026, 5, 1, 9, 0, tzinfo=timezone.utc),
        ),
    ]

    for status, effective_from in transitions:
        status_service.transition_status(
            tenant_id=tenant.id,
            employee_id=employee.id,
            status=status,
            effective_from=effective_from,
            reason=f"Transition to {status.value}",
        )

        db.refresh(employee)

        latest_history = (
            db.query(EmploymentStatusHistory)
            .filter(
                EmploymentStatusHistory.tenant_id == tenant.id,
                EmploymentStatusHistory.employee_id == employee.id,
            )
            .order_by(
                EmploymentStatusHistory.effective_from.desc()
            )
            .first()
        )

        assert latest_history is not None
        assert employee.employment_status == latest_history.status
        assert employee.employment_status == status

    assert employee.employment_status == EmploymentStatus.SUSPENDED



def test_multiple_status_transitions_close_previous_periods_correctly(db):
    tenant = create_tenant(
        db,
        "Status Period Boundary Tenant",
    )

    person_service = PersonService(db)

    person = person_service.create_person(
        tenant_id=tenant.id,
        person_number="P-STATUS-PERIOD-001",
        first_name="Period",
        last_name="Boundary",
    )

    employee_service = EmployeeService(db)

    employee = employee_service.create_employee(
        tenant_id=tenant.id,
        person_id=person.id,
        employee_number="EMP-STATUS-PERIOD-001",
        employment_status=EmploymentStatus.ACTIVE,
        employment_type=EmploymentType.PERMANENT,
        hire_date=date(2026, 1, 1),
    )

    status_service = EmploymentStatusHistoryService(db)

    transitions = [
        (
            EmploymentStatus.ON_LEAVE,
            datetime(2026, 3, 1, 9, 0, tzinfo=timezone.utc),
        ),
        (
            EmploymentStatus.ACTIVE,
            datetime(2026, 4, 1, 9, 0, tzinfo=timezone.utc),
        ),
        (
            EmploymentStatus.SUSPENDED,
            datetime(2026, 5, 1, 9, 0, tzinfo=timezone.utc),
        ),
    ]

    for status, effective_from in transitions:
        status_service.transition_status(
            tenant_id=tenant.id,
            employee_id=employee.id,
            status=status,
            effective_from=effective_from,
            reason=f"Transition to {status.value}",
        )

    history = (
        db.query(EmploymentStatusHistory)
        .filter(
            EmploymentStatusHistory.tenant_id == tenant.id,
            EmploymentStatusHistory.employee_id == employee.id,
        )
        .order_by(
            EmploymentStatusHistory.effective_from.asc()
        )
        .all()
    )

    assert len(history) == 4

    assert history[0].status == EmploymentStatus.ACTIVE
    assert history[0].effective_to == datetime(
        2026,
        3,
        1,
        9,
        0,
        tzinfo=timezone.utc,
    )

    assert history[1].status == EmploymentStatus.ON_LEAVE
    assert history[1].effective_from == datetime(
        2026,
        3,
        1,
        9,
        0,
        tzinfo=timezone.utc,
    )
    assert history[1].effective_to == datetime(
        2026,
        4,
        1,
        9,
        0,
        tzinfo=timezone.utc,
    )

    assert history[2].status == EmploymentStatus.ACTIVE
    assert history[2].effective_from == datetime(
        2026,
        4,
        1,
        9,
        0,
        tzinfo=timezone.utc,
    )
    assert history[2].effective_to == datetime(
        2026,
        5,
        1,
        9,
        0,
        tzinfo=timezone.utc,
    )

    assert history[3].status == EmploymentStatus.SUSPENDED
    assert history[3].effective_from == datetime(
        2026,
        5,
        1,
        9,
        0,
        tzinfo=timezone.utc,
    )
    assert history[3].effective_to is None



def test_rejected_status_transition_does_not_modify_existing_state(db):
    tenant = create_tenant(
        db,
        "Status Transition Atomicity Tenant",
    )

    person_service = PersonService(db)

    person = person_service.create_person(
        tenant_id=tenant.id,
        person_number="P-STATUS-ATOMIC-001",
        first_name="Atomicity",
        last_name="Test",
    )

    employee_service = EmployeeService(db)

    employee = employee_service.create_employee(
        tenant_id=tenant.id,
        person_id=person.id,
        employee_number="EMP-STATUS-ATOMIC-001",
        employment_status=EmploymentStatus.ACTIVE,
        employment_type=EmploymentType.PERMANENT,
        hire_date=date(2026, 1, 1),
    )

    status_service = EmploymentStatusHistoryService(db)

    valid_transition = datetime(
        2026,
        3,
        1,
        9,
        0,
        tzinfo=timezone.utc,
    )

    status_service.transition_status(
        tenant_id=tenant.id,
        employee_id=employee.id,
        status=EmploymentStatus.ON_LEAVE,
        effective_from=valid_transition,
        reason="Employee went on leave",
    )

    db.refresh(employee)

    history_before = (
        db.query(EmploymentStatusHistory)
        .filter(
            EmploymentStatusHistory.tenant_id == tenant.id,
            EmploymentStatusHistory.employee_id == employee.id,
        )
        .order_by(
            EmploymentStatusHistory.effective_from.asc()
        )
        .all()
    )

    assert employee.employment_status == EmploymentStatus.ON_LEAVE
    assert len(history_before) == 2

    with pytest.raises(
        ValueError,
        match="effective_from must be later than the current status period start",
    ):
        status_service.transition_status(
            tenant_id=tenant.id,
            employee_id=employee.id,
            status=EmploymentStatus.ACTIVE,
            effective_from=datetime(
                2026,
                2,
                1,
                9,
                0,
                tzinfo=timezone.utc,
            ),
            reason="Invalid retroactive transition",
        )

    db.refresh(employee)

    history_after = (
        db.query(EmploymentStatusHistory)
        .filter(
            EmploymentStatusHistory.tenant_id == tenant.id,
            EmploymentStatusHistory.employee_id == employee.id,
        )
        .order_by(
            EmploymentStatusHistory.effective_from.asc()
        )
        .all()
    )

    # Employee projection must remain unchanged.
    assert employee.employment_status == EmploymentStatus.ON_LEAVE

    # History count must remain unchanged.
    assert len(history_after) == 2

    # Original history periods must remain unchanged.
    assert history_after[0].status == EmploymentStatus.ACTIVE
    assert history_after[0].effective_to == valid_transition

    assert history_after[1].status == EmploymentStatus.ON_LEAVE
    assert history_after[1].effective_from == valid_transition
    assert history_after[1].effective_to is None




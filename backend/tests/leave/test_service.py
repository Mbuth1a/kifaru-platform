from datetime import date
from uuid import uuid4

import pytest

from app.hr.enums import EmploymentStatus, EmploymentType
from app.hr.models import Employee, Person
from app.leave.enums import LeaveRequestStatus
from app.leave.models import LeaveRequest, LeaveType
from app.leave.service import LeaveService
from app.organization.models import Tenant


def create_tenant(db, name):
    tenant = Tenant(
        id=uuid4(),
        legal_name=name,
        country_code="KE",
        timezone="Africa/Nairobi",
        currency_code="KES",
    )

    db.add(tenant)
    db.flush()

    return tenant


def create_employee(
    db,
    tenant,
    *,
    status=EmploymentStatus.ACTIVE,
):
    person = Person(
        id=uuid4(),
        tenant_id=tenant.id,
        person_number=f"P-{uuid4().hex[:8]}",
        first_name="Test",
        last_name="Employee",
    )

    db.add(person)
    db.flush()

    employee = Employee(
        id=uuid4(),
        tenant_id=tenant.id,
        person_id=person.id,
        employee_number=f"E-{uuid4().hex[:8]}",
        employment_status=status,
        employment_type=EmploymentType.PERMANENT,
        hire_date=date(2025, 1, 1),
    )

    db.add(employee)
    db.flush()

    return employee


def create_leave_type(
    db,
    tenant,
    *,
    active=True,
):
    leave_type = LeaveType(
        id=uuid4(),
        tenant_id=tenant.id,
        code=f"ANNUAL-{uuid4().hex[:6]}",
        name=f"Annual Leave {uuid4().hex[:6]}",
        active=active,
    )

    db.add(leave_type)
    db.flush()

    return leave_type



def test_create_leave_request_creates_pending_request(db):
    tenant = create_tenant(db, "Leave Test Ltd")
    employee = create_employee(db, tenant)
    leave_type = create_leave_type(db, tenant)

    service = LeaveService(db)

    request = service.create_leave_request(
        tenant_id=tenant.id,
        employee_id=employee.id,
        leave_type_id=leave_type.id,
        start_date=date(2026, 10, 10),
        end_date=date(2026, 10, 12),
        reason="Annual leave",
    )

    assert request.id is not None
    assert request.tenant_id == tenant.id
    assert request.employee_id == employee.id
    assert request.leave_type_id == leave_type.id
    assert request.start_date == date(2026, 10, 10)
    assert request.end_date == date(2026, 10, 12)

    # Inclusive calendar days: 10, 11, 12 = 3
    assert request.requested_days == 3

    assert request.status == LeaveRequestStatus.PENDING
    assert request.reason == "Annual leave"



def test_create_leave_request_rejects_invalid_date_range(db):
    tenant = create_tenant(db, "Invalid Dates Ltd")
    employee = create_employee(db, tenant)
    leave_type = create_leave_type(db, tenant)

    service = LeaveService(db)

    with pytest.raises(
        ValueError,
        match="end_date must be on or after start_date",
    ):
        service.create_leave_request(
            tenant_id=tenant.id,
            employee_id=employee.id,
            leave_type_id=leave_type.id,
            start_date=date(2026, 10, 12),
            end_date=date(2026, 10, 10),
        )


def test_create_leave_request_rejects_terminated_employee(db):
    tenant = create_tenant(db, "Terminated Employee Ltd")

    employee = create_employee(
        db,
        tenant,
        status=EmploymentStatus.TERMINATED,
    )

    leave_type = create_leave_type(db, tenant)

    service = LeaveService(db)

    with pytest.raises(
        ValueError,
        match="Terminated employees cannot create new leave requests",
    ):
        service.create_leave_request(
            tenant_id=tenant.id,
            employee_id=employee.id,
            leave_type_id=leave_type.id,
            start_date=date(2026, 10, 10),
            end_date=date(2026, 10, 12),
        )


def test_create_leave_request_rejects_employee_from_another_tenant(db):
    tenant_a = create_tenant(db, "Tenant A")
    tenant_b = create_tenant(db, "Tenant B")

    employee_b = create_employee(db, tenant_b)
    leave_type_a = create_leave_type(db, tenant_a)

    service = LeaveService(db)

    with pytest.raises(
        ValueError,
        match="Employee not found for this tenant",
    ):
        service.create_leave_request(
            tenant_id=tenant_a.id,
            employee_id=employee_b.id,
            leave_type_id=leave_type_a.id,
            start_date=date(2026, 10, 10),
            end_date=date(2026, 10, 12),
        )


def test_create_leave_request_rejects_leave_type_from_another_tenant(db):
    tenant_a = create_tenant(db, "Tenant A")
    tenant_b = create_tenant(db, "Tenant B")

    employee_a = create_employee(db, tenant_a)
    leave_type_b = create_leave_type(db, tenant_b)

    service = LeaveService(db)

    with pytest.raises(
        ValueError,
        match="Leave type not found for this tenant",
    ):
        service.create_leave_request(
            tenant_id=tenant_a.id,
            employee_id=employee_a.id,
            leave_type_id=leave_type_b.id,
            start_date=date(2026, 10, 10),
            end_date=date(2026, 10, 12),
        )


def test_create_leave_request_rejects_inactive_leave_type(db):
    tenant = create_tenant(db, "Inactive Leave Type Ltd")
    employee = create_employee(db, tenant)

    leave_type = create_leave_type(
        db,
        tenant,
        active=False,
    )

    service = LeaveService(db)

    with pytest.raises(
        ValueError,
        match="Leave type is inactive",
    ):
        service.create_leave_request(
            tenant_id=tenant.id,
            employee_id=employee.id,
            leave_type_id=leave_type.id,
            start_date=date(2026, 10, 10),
            end_date=date(2026, 10, 12),
        )



def create_existing_leave_request(
    db,
    tenant,
    employee,
    leave_type,
    *,
    start_date,
    end_date,
    status,
):
    request = LeaveRequest(
        id=uuid4(),
        tenant_id=tenant.id,
        employee_id=employee.id,
        leave_type_id=leave_type.id,
        start_date=start_date,
        end_date=end_date,
        requested_days=(end_date - start_date).days + 1,
        status=status,
    )

    db.add(request)
    db.flush()

    return request


def test_create_leave_request_rejects_overlap_with_pending_request(db):
    tenant = create_tenant(db, "Pending Overlap Ltd")
    employee = create_employee(db, tenant)
    leave_type = create_leave_type(db, tenant)

    create_existing_leave_request(
        db,
        tenant,
        employee,
        leave_type,
        start_date=date(2026, 10, 10),
        end_date=date(2026, 10, 12),
        status=LeaveRequestStatus.PENDING,
    )

    service = LeaveService(db)

    with pytest.raises(
        ValueError,
        match="overlaps an existing pending or approved leave request",
    ):
        service.create_leave_request(
            tenant_id=tenant.id,
            employee_id=employee.id,
            leave_type_id=leave_type.id,
            start_date=date(2026, 10, 12),
            end_date=date(2026, 10, 14),
        )


def test_create_leave_request_rejects_overlap_with_approved_request(db):
    tenant = create_tenant(db, "Approved Overlap Ltd")
    employee = create_employee(db, tenant)
    leave_type = create_leave_type(db, tenant)

    create_existing_leave_request(
        db,
        tenant,
        employee,
        leave_type,
        start_date=date(2026, 10, 10),
        end_date=date(2026, 10, 12),
        status=LeaveRequestStatus.APPROVED,
    )

    service = LeaveService(db)

    with pytest.raises(
        ValueError,
        match="overlaps an existing pending or approved leave request",
    ):
        service.create_leave_request(
            tenant_id=tenant.id,
            employee_id=employee.id,
            leave_type_id=leave_type.id,
            start_date=date(2026, 10, 12),
            end_date=date(2026, 10, 14),
        )


def test_create_leave_request_allows_overlap_with_rejected_request(db):
    tenant = create_tenant(db, "Rejected Overlap Ltd")
    employee = create_employee(db, tenant)
    leave_type = create_leave_type(db, tenant)

    create_existing_leave_request(
        db,
        tenant,
        employee,
        leave_type,
        start_date=date(2026, 10, 10),
        end_date=date(2026, 10, 12),
        status=LeaveRequestStatus.REJECTED,
    )

    service = LeaveService(db)

    request = service.create_leave_request(
        tenant_id=tenant.id,
        employee_id=employee.id,
        leave_type_id=leave_type.id,
        start_date=date(2026, 10, 12),
        end_date=date(2026, 10, 14),
    )

    assert request.status == LeaveRequestStatus.PENDING
    assert request.requested_days == 3


def test_create_leave_request_allows_overlap_with_cancelled_request(db):
    tenant = create_tenant(db, "Cancelled Overlap Ltd")
    employee = create_employee(db, tenant)
    leave_type = create_leave_type(db, tenant)

    create_existing_leave_request(
        db,
        tenant,
        employee,
        leave_type,
        start_date=date(2026, 10, 10),
        end_date=date(2026, 10, 12),
        status=LeaveRequestStatus.CANCELLED,
    )

    service = LeaveService(db)

    request = service.create_leave_request(
        tenant_id=tenant.id,
        employee_id=employee.id,
        leave_type_id=leave_type.id,
        start_date=date(2026, 10, 12),
        end_date=date(2026, 10, 14),
    )

    assert request.status == LeaveRequestStatus.PENDING
    assert request.requested_days == 3




def test_pending_leave_request_can_be_approved(db):
    tenant = create_tenant(db, "Approve Leave Ltd")
    employee = create_employee(db, tenant)
    leave_type = create_leave_type(db, tenant)

    service = LeaveService(db)

    request = service.create_leave_request(
        tenant_id=tenant.id,
        employee_id=employee.id,
        leave_type_id=leave_type.id,
        start_date=date(2026, 10, 10),
        end_date=date(2026, 10, 12),
    )

    updated = service.transition_leave_request(
        tenant_id=tenant.id,
        leave_request_id=request.id,
        new_status=LeaveRequestStatus.APPROVED,
    )

    assert updated.status == LeaveRequestStatus.APPROVED


def test_pending_leave_request_can_be_rejected(db):
    tenant = create_tenant(db, "Reject Leave Ltd")
    employee = create_employee(db, tenant)
    leave_type = create_leave_type(db, tenant)

    service = LeaveService(db)

    request = service.create_leave_request(
        tenant_id=tenant.id,
        employee_id=employee.id,
        leave_type_id=leave_type.id,
        start_date=date(2026, 10, 10),
        end_date=date(2026, 10, 12),
    )

    updated = service.transition_leave_request(
        tenant_id=tenant.id,
        leave_request_id=request.id,
        new_status=LeaveRequestStatus.REJECTED,
    )

    assert updated.status == LeaveRequestStatus.REJECTED


def test_pending_leave_request_can_be_cancelled(db):
    tenant = create_tenant(db, "Cancel Pending Leave Ltd")
    employee = create_employee(db, tenant)
    leave_type = create_leave_type(db, tenant)

    service = LeaveService(db)

    request = service.create_leave_request(
        tenant_id=tenant.id,
        employee_id=employee.id,
        leave_type_id=leave_type.id,
        start_date=date(2026, 10, 10),
        end_date=date(2026, 10, 12),
    )

    updated = service.transition_leave_request(
        tenant_id=tenant.id,
        leave_request_id=request.id,
        new_status=LeaveRequestStatus.CANCELLED,
    )

    assert updated.status == LeaveRequestStatus.CANCELLED


def test_approved_leave_request_can_be_cancelled(db):
    tenant = create_tenant(db, "Cancel Approved Leave Ltd")
    employee = create_employee(db, tenant)
    leave_type = create_leave_type(db, tenant)

    service = LeaveService(db)

    request = create_existing_leave_request(
        db,
        tenant,
        employee,
        leave_type,
        start_date=date(2026, 10, 10),
        end_date=date(2026, 10, 12),
        status=LeaveRequestStatus.APPROVED,
    )

    updated = service.transition_leave_request(
        tenant_id=tenant.id,
        leave_request_id=request.id,
        new_status=LeaveRequestStatus.CANCELLED,
    )

    assert updated.status == LeaveRequestStatus.CANCELLED


@pytest.mark.parametrize(
    "current_status,new_status",
    [
        (
            LeaveRequestStatus.PENDING,
            LeaveRequestStatus.PENDING,
        ),
        (
            LeaveRequestStatus.REJECTED,
            LeaveRequestStatus.APPROVED,
        ),
        (
            LeaveRequestStatus.REJECTED,
            LeaveRequestStatus.CANCELLED,
        ),
        (
            LeaveRequestStatus.CANCELLED,
            LeaveRequestStatus.APPROVED,
        ),
        (
            LeaveRequestStatus.CANCELLED,
            LeaveRequestStatus.REJECTED,
        ),
        (
            LeaveRequestStatus.APPROVED,
            LeaveRequestStatus.REJECTED,
        ),
        (
            LeaveRequestStatus.APPROVED,
            LeaveRequestStatus.APPROVED,
        ),
    ],
)
def test_invalid_leave_status_transitions_are_rejected(
    db,
    current_status,
    new_status,
):
    tenant = create_tenant(db, "Invalid Transition Ltd")
    employee = create_employee(db, tenant)
    leave_type = create_leave_type(db, tenant)

    request = create_existing_leave_request(
        db,
        tenant,
        employee,
        leave_type,
        start_date=date(2026, 10, 10),
        end_date=date(2026, 10, 12),
        status=current_status,
    )

    service = LeaveService(db)

    with pytest.raises(
        ValueError,
        match="Invalid leave request status transition",
    ):
        service.transition_leave_request(
            tenant_id=tenant.id,
            leave_request_id=request.id,
            new_status=new_status,
        )


def test_leave_request_transition_rejects_cross_tenant_access(db):
    tenant_a = create_tenant(db, "Transition Tenant A")
    tenant_b = create_tenant(db, "Transition Tenant B")

    employee_b = create_employee(db, tenant_b)
    leave_type_b = create_leave_type(db, tenant_b)

    request_b = create_existing_leave_request(
        db,
        tenant_b,
        employee_b,
        leave_type_b,
        start_date=date(2026, 10, 10),
        end_date=date(2026, 10, 12),
        status=LeaveRequestStatus.PENDING,
    )

    service = LeaveService(db)

    with pytest.raises(
        ValueError,
        match="Leave request not found for this tenant",
    ):
        service.transition_leave_request(
            tenant_id=tenant_a.id,
            leave_request_id=request_b.id,
            new_status=LeaveRequestStatus.APPROVED,
        )



def test_create_leave_type_creates_type(db):
    tenant = create_tenant(db, "Create Leave Type Ltd")

    service = LeaveService(db)

    leave_type = service.create_leave_type(
        tenant_id=tenant.id,
        code="ANNUAL",
        name="Annual Leave",
        description="Annual employee leave",
        active=True,
    )

    assert leave_type.id is not None
    assert leave_type.tenant_id == tenant.id
    assert leave_type.code == "ANNUAL"
    assert leave_type.name == "Annual Leave"
    assert leave_type.description == "Annual employee leave"
    assert leave_type.active is True


def test_create_leave_type_rejects_duplicate_code_within_tenant(db):
    tenant = create_tenant(db, "Duplicate Leave Code Ltd")

    service = LeaveService(db)

    service.create_leave_type(
        tenant_id=tenant.id,
        code="ANNUAL",
        name="Annual Leave",
    )

    with pytest.raises(
        ValueError,
        match="Leave type code already exists for this tenant",
    ):
        service.create_leave_type(
            tenant_id=tenant.id,
            code="ANNUAL",
            name="Another Leave",
        )


def test_create_leave_type_rejects_duplicate_name_within_tenant(db):
    tenant = create_tenant(db, "Duplicate Leave Name Ltd")

    service = LeaveService(db)

    service.create_leave_type(
        tenant_id=tenant.id,
        code="ANNUAL",
        name="Annual Leave",
    )

    with pytest.raises(
        ValueError,
        match="Leave type name already exists for this tenant",
    ):
        service.create_leave_type(
            tenant_id=tenant.id,
            code="ANNUAL-2",
            name="Annual Leave",
        )


def test_create_leave_type_allows_same_code_and_name_across_tenants(db):
    tenant_a = create_tenant(db, "Leave Tenant A")
    tenant_b = create_tenant(db, "Leave Tenant B")

    service = LeaveService(db)

    leave_type_a = service.create_leave_type(
        tenant_id=tenant_a.id,
        code="ANNUAL",
        name="Annual Leave",
    )

    leave_type_b = service.create_leave_type(
        tenant_id=tenant_b.id,
        code="ANNUAL",
        name="Annual Leave",
    )

    assert leave_type_a.id != leave_type_b.id
    assert leave_type_a.tenant_id == tenant_a.id
    assert leave_type_b.tenant_id == tenant_b.id


def test_get_leave_type_returns_inactive_type(db):
    tenant = create_tenant(db, "Inactive Retrieval Ltd")

    leave_type = create_leave_type(
        db,
        tenant,
        active=False,
    )

    service = LeaveService(db)

    result = service.get_leave_type(
        tenant_id=tenant.id,
        leave_type_id=leave_type.id,
    )

    assert result.id == leave_type.id
    assert result.tenant_id == tenant.id
    assert result.active is False


def test_get_leave_type_rejects_cross_tenant_access(db):
    tenant_a = create_tenant(db, "Get Type Tenant A")
    tenant_b = create_tenant(db, "Get Type Tenant B")

    leave_type_b = create_leave_type(db, tenant_b)

    service = LeaveService(db)

    with pytest.raises(
        ValueError,
        match="Leave type not found for this tenant",
    ):
        service.get_leave_type(
            tenant_id=tenant_a.id,
            leave_type_id=leave_type_b.id,
        )


def test_get_leave_request_returns_request(db):
    tenant = create_tenant(db, "Get Request Ltd")
    employee = create_employee(db, tenant)
    leave_type = create_leave_type(db, tenant)

    request = create_existing_leave_request(
        db,
        tenant,
        employee,
        leave_type,
        start_date=date(2026, 10, 10),
        end_date=date(2026, 10, 12),
        status=LeaveRequestStatus.PENDING,
    )

    service = LeaveService(db)

    result = service.get_leave_request(
        tenant_id=tenant.id,
        leave_request_id=request.id,
    )

    assert result.id == request.id
    assert result.tenant_id == tenant.id
    assert result.employee_id == employee.id
    assert result.leave_type_id == leave_type.id
    assert result.status == LeaveRequestStatus.PENDING


def test_get_leave_request_rejects_cross_tenant_access(db):
    tenant_a = create_tenant(db, "Request Tenant A")
    tenant_b = create_tenant(db, "Request Tenant B")

    employee_b = create_employee(db, tenant_b)
    leave_type_b = create_leave_type(db, tenant_b)

    request_b = create_existing_leave_request(
        db,
        tenant_b,
        employee_b,
        leave_type_b,
        start_date=date(2026, 10, 10),
        end_date=date(2026, 10, 12),
        status=LeaveRequestStatus.PENDING,
    )

    service = LeaveService(db)

    with pytest.raises(
        ValueError,
        match="Leave request not found for this tenant",
    ):
        service.get_leave_request(
            tenant_id=tenant_a.id,
            leave_request_id=request_b.id,
        )
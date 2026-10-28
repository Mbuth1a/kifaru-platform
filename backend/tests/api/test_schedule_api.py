
from datetime import time
from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import app
from app.organization.models import Tenant


client = TestClient(app)


def create_tenant(db, name="Schedule Test Tenant"):
    tenant = Tenant(
        legal_name=name,
        country_code="KE",
        timezone="Africa/Nairobi",
        currency_code="KES",
    )
    db.add(tenant)
    db.flush()

    return tenant


def create_work_shift(
    tenant_id,
    *,
    code="DAY",
    name="Day Shift",
    start_time="08:00:00",
    end_time="17:00:00",
):
    return client.post(
        "/schedule/work-shifts",
        headers={"X-Tenant-ID": str(tenant_id)},
        json={
            "code": code,
            "name": name,
            "start_time": start_time,
            "end_time": end_time,
        },
    )


def test_create_work_shift(db):
    tenant = create_tenant(db)

    response = create_work_shift(tenant.id)

    assert response.status_code == 201

    data = response.json()
    assert data["tenant_id"] == str(tenant.id)
    assert data["code"] == "DAY"
    assert data["name"] == "Day Shift"
    assert data["start_time"] == "08:00:00"
    assert data["end_time"] == "17:00:00"
    assert data["id"] is not None
    assert data["created_at"] is not None
    assert data["updated_at"] is not None


def test_create_work_shift_rejects_duplicate_code_for_same_tenant(db):
    tenant = create_tenant(db)

    first_response = create_work_shift(tenant.id)
    assert first_response.status_code == 201

    second_response = create_work_shift(
        tenant.id,
        name="Alternative Day Shift",
    )

    assert second_response.status_code == 400
    assert "already exists" in second_response.json()["detail"].lower()


def test_same_work_shift_code_is_allowed_for_different_tenants(db):
    tenant_a = create_tenant(db, "Schedule Tenant A")
    tenant_b = create_tenant(db, "Schedule Tenant B")

    response_a = create_work_shift(tenant_a.id)
    response_b = create_work_shift(tenant_b.id)

    assert response_a.status_code == 201
    assert response_b.status_code == 201

    assert response_a.json()["tenant_id"] == str(tenant_a.id)
    assert response_b.json()["tenant_id"] == str(tenant_b.id)


def test_create_work_shift_rejects_identical_start_and_end_times(db):
    tenant = create_tenant(db)

    response = create_work_shift(
        tenant.id,
        start_time="08:00:00",
        end_time="08:00:00",
    )

    assert response.status_code == 400
    assert "must differ" in response.json()["detail"].lower()


def test_create_work_shift_rejects_blank_code(db):
    tenant = create_tenant(db)

    response = create_work_shift(
        tenant.id,
        code="   ",
    )

    assert response.status_code == 400
    assert "code cannot be blank" in response.json()["detail"].lower()


def test_create_work_shift_rejects_blank_name(db):
    tenant = create_tenant(db)

    response = create_work_shift(
        tenant.id,
        name="   ",
    )

    assert response.status_code == 400
    assert "name cannot be blank" in response.json()["detail"].lower()


def test_list_work_shifts(db):
    tenant = create_tenant(db)

    first = create_work_shift(
        tenant.id,
        code="NIGHT",
        name="Night Shift",
        start_time="20:00:00",
        end_time="05:00:00",
    )
    second = create_work_shift(
        tenant.id,
        code="DAY",
        name="Day Shift",
    )

    assert first.status_code == 201
    assert second.status_code == 201

    response = client.get(
        "/schedule/work-shifts",
        headers={"X-Tenant-ID": str(tenant.id)},
    )

    assert response.status_code == 200

    data = response.json()
    assert len(data) == 2
    assert [item["code"] for item in data] == ["DAY", "NIGHT"]


def test_list_work_shifts_is_tenant_scoped(db):
    tenant_a = create_tenant(db, "Schedule List Tenant A")
    tenant_b = create_tenant(db, "Schedule List Tenant B")

    response_a = create_work_shift(
        tenant_a.id,
        code="DAY-A",
        name="Tenant A Day Shift",
    )
    response_b = create_work_shift(
        tenant_b.id,
        code="DAY-B",
        name="Tenant B Day Shift",
    )

    assert response_a.status_code == 201
    assert response_b.status_code == 201

    response = client.get(
        "/schedule/work-shifts",
        headers={"X-Tenant-ID": str(tenant_a.id)},
    )

    assert response.status_code == 200

    data = response.json()
    assert len(data) == 1
    assert data[0]["tenant_id"] == str(tenant_a.id)
    assert data[0]["code"] == "DAY-A"


def test_get_work_shift(db):
    tenant = create_tenant(db)

    create_response = create_work_shift(tenant.id)
    assert create_response.status_code == 201

    shift_id = create_response.json()["id"]

    response = client.get(
        f"/schedule/work-shifts/{shift_id}",
        headers={"X-Tenant-ID": str(tenant.id)},
    )

    assert response.status_code == 200
    assert response.json()["id"] == shift_id
    assert response.json()["code"] == "DAY"


def test_get_work_shift_returns_404_for_missing_shift(db):
    tenant = create_tenant(db)

    response = client.get(
        f"/schedule/work-shifts/{uuid4()}",
        headers={"X-Tenant-ID": str(tenant.id)},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Work shift not found."


def test_get_work_shift_rejects_cross_tenant_access(db):
    tenant_a = create_tenant(db, "Schedule Detail Tenant A")
    tenant_b = create_tenant(db, "Schedule Detail Tenant B")

    create_response = create_work_shift(tenant_a.id)
    assert create_response.status_code == 201

    shift_id = create_response.json()["id"]

    response = client.get(
        f"/schedule/work-shifts/{shift_id}",
        headers={"X-Tenant-ID": str(tenant_b.id)},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Work shift not found."


def create_work_schedule(
    tenant_id,
    *,
    code="STANDARD",
    name="Standard Work Schedule",
    days=None,
):
    if days is None:
        days = [
            {
                "day": "MONDAY",
                "work_shift_id": None,
            }
        ]

    return client.post(
        "/schedule/work-schedules",
        headers={"X-Tenant-ID": str(tenant_id)},
        json={
            "code": code,
            "name": name,
            "days": days,
        },
    )


def test_create_work_schedule_with_weekday_mappings(db):
    tenant = create_tenant(db)

    shift_response = create_work_shift(tenant.id)
    assert shift_response.status_code == 201
    shift_id = shift_response.json()["id"]

    response = create_work_schedule(
        tenant.id,
        days=[
            {"day": "MONDAY", "work_shift_id": shift_id},
            {"day": "TUESDAY", "work_shift_id": shift_id},
            {"day": "WEDNESDAY", "work_shift_id": shift_id},
        ],
    )

    assert response.status_code == 201, response.text

    data = response.json()
    assert data["tenant_id"] == str(tenant.id)
    assert data["code"] == "STANDARD"
    assert data["name"] == "Standard Work Schedule"
    assert len(data["days"]) == 3
    assert {item["day"] for item in data["days"]} == {
        "MONDAY",
        "TUESDAY",
        "WEDNESDAY",
    }
    assert all(item["work_shift_id"] == shift_id for item in data["days"])


def test_create_work_schedule_rejects_duplicate_code(db):
    tenant = create_tenant(db)

    shift_response = create_work_shift(tenant.id)
    assert shift_response.status_code == 201
    shift_id = shift_response.json()["id"]

    days = [{"day": "MONDAY", "work_shift_id": shift_id}]

    first = create_work_schedule(tenant.id, days=days)
    second = create_work_schedule(
        tenant.id,
        name="Another Schedule",
        days=days,
    )

    assert first.status_code == 201, first.text
    assert second.status_code == 400
    assert "already exists" in second.json()["detail"].lower()


def test_same_work_schedule_code_allowed_for_different_tenants(db):
    tenant_a = create_tenant(db, "Work Schedule Tenant A")
    tenant_b = create_tenant(db, "Work Schedule Tenant B")

    shift_a = create_work_shift(tenant_a.id, code="DAY-A")
    shift_b = create_work_shift(tenant_b.id, code="DAY-B")

    assert shift_a.status_code == 201
    assert shift_b.status_code == 201

    response_a = create_work_schedule(
        tenant_a.id,
        days=[
            {
                "day": "MONDAY",
                "work_shift_id": shift_a.json()["id"],
            }
        ],
    )
    response_b = create_work_schedule(
        tenant_b.id,
        days=[
            {
                "day": "MONDAY",
                "work_shift_id": shift_b.json()["id"],
            }
        ],
    )

    assert response_a.status_code == 201, response_a.text
    assert response_b.status_code == 201, response_b.text
    assert response_a.json()["tenant_id"] == str(tenant_a.id)
    assert response_b.json()["tenant_id"] == str(tenant_b.id)


def test_create_work_schedule_rejects_duplicate_days(db):
    tenant = create_tenant(db)

    shift_response = create_work_shift(tenant.id)
    assert shift_response.status_code == 201
    shift_id = shift_response.json()["id"]

    response = create_work_schedule(
        tenant.id,
        days=[
            {"day": "MONDAY", "work_shift_id": shift_id},
            {"day": "MONDAY", "work_shift_id": shift_id},
        ],
    )

    assert response.status_code == 400
    assert "appears more than once" in response.json()["detail"].lower()


def test_create_work_schedule_rejects_shift_from_another_tenant(db):
    tenant_a = create_tenant(db, "Shift Owner Tenant")
    tenant_b = create_tenant(db, "Schedule Owner Tenant")

    shift_response = create_work_shift(tenant_a.id)
    assert shift_response.status_code == 201

    response = create_work_schedule(
        tenant_b.id,
        days=[
            {
                "day": "MONDAY",
                "work_shift_id": shift_response.json()["id"],
            }
        ],
    )

    assert response.status_code == 400
    assert "not found for this tenant" in response.json()["detail"].lower()


def test_list_work_schedules_is_tenant_scoped(db):
    tenant_a = create_tenant(db, "Schedule List Tenant A")
    tenant_b = create_tenant(db, "Schedule List Tenant B")

    shift_a = create_work_shift(tenant_a.id, code="DAY-A")
    shift_b = create_work_shift(tenant_b.id, code="DAY-B")

    assert shift_a.status_code == 201
    assert shift_b.status_code == 201

    schedule_a = create_work_schedule(
        tenant_a.id,
        code="A",
        days=[
            {"day": "MONDAY", "work_shift_id": shift_a.json()["id"]}
        ],
    )
    schedule_b = create_work_schedule(
        tenant_b.id,
        code="B",
        days=[
            {"day": "TUESDAY", "work_shift_id": shift_b.json()["id"]}
        ],
    )

    assert schedule_a.status_code == 201, schedule_a.text
    assert schedule_b.status_code == 201, schedule_b.text

    response = client.get(
        "/schedule/work-schedules",
        headers={"X-Tenant-ID": str(tenant_a.id)},
    )

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["tenant_id"] == str(tenant_a.id)
    assert data[0]["code"] == "A"


def test_get_work_schedule_returns_schedule_days(db):
    tenant = create_tenant(db)

    shift_response = create_work_shift(tenant.id)
    assert shift_response.status_code == 201
    shift_id = shift_response.json()["id"]

    create_response = create_work_schedule(
        tenant.id,
        days=[
            {"day": "MONDAY", "work_shift_id": shift_id},
            {"day": "FRIDAY", "work_shift_id": shift_id},
        ],
    )
    assert create_response.status_code == 201, create_response.text

    schedule_id = create_response.json()["id"]

    response = client.get(
        f"/schedule/work-schedules/{schedule_id}",
        headers={"X-Tenant-ID": str(tenant.id)},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == schedule_id
    assert {item["day"] for item in data["days"]} == {"MONDAY", "FRIDAY"}


def test_get_work_schedule_returns_404_for_missing_schedule(db):
    tenant = create_tenant(db)

    response = client.get(
        f"/schedule/work-schedules/{uuid4()}",
        headers={"X-Tenant-ID": str(tenant.id)},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Work schedule not found."


def test_get_work_schedule_rejects_cross_tenant_access(db):
    tenant_a = create_tenant(db, "Schedule Detail Tenant A")
    tenant_b = create_tenant(db, "Schedule Detail Tenant B")

    shift_response = create_work_shift(tenant_a.id)
    assert shift_response.status_code == 201

    schedule_response = create_work_schedule(
        tenant_a.id,
        days=[
            {
                "day": "MONDAY",
                "work_shift_id": shift_response.json()["id"],
            }
        ],
    )
    assert schedule_response.status_code == 201, schedule_response.text

    schedule_id = schedule_response.json()["id"]

    response = client.get(
        f"/schedule/work-schedules/{schedule_id}",
        headers={"X-Tenant-ID": str(tenant_b.id)},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Work schedule not found."

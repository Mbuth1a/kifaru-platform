from app.organization.models import Tenant
from app.organization.enums import TenantStatus


def test_create_tenant(db):

    tenant = Tenant(
        legal_name="Kifaru Technologies Ltd",
        country_code="KE",
        currency_code="KES",
        timezone="Africa/Nairobi",
    )

    db.add(tenant)
    db.commit()
    db.refresh(tenant)

    assert tenant.id is not None
    assert tenant.status == TenantStatus.PROVISIONING
    assert tenant.legal_name == "Kifaru Technologies Ltd"


def test_default_metadata(db):

    tenant = Tenant(
        legal_name="Demo Company",
        country_code="KE",
        currency_code="KES",
        timezone="Africa/Nairobi",
    )

    db.add(tenant)
    db.commit()
    db.refresh(tenant)

    assert tenant.metadata_json == {}
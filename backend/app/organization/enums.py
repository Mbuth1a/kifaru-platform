from enum import Enum


class TenantStatus(str, Enum):
    PROVISIONING = "PROVISIONING"
    ACTIVE = "ACTIVE"
    SUSPENDED = "SUSPENDED"
    DEACTIVATED = "DEACTIVATED"


class LegalEntityStatus(str, Enum):
    ACTIVE = "ACTIVE"
    SUSPENDED = "SUSPENDED"
    DEACTIVATED = "DEACTIVATED"



class OrganizationUnitStatus(str, Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    DEACTIVATED = "DEACTIVATED"


class OrganizationUnitType(str, Enum):
    COMPANY = "COMPANY"
    DIVISION = "DIVISION"
    DEPARTMENT = "DEPARTMENT"
    TEAM = "TEAM"
    BUSINESS_UNIT = "BUSINESS_UNIT"
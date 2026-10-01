from enum import Enum


class Gender(str, Enum):
    MALE = "MALE"
    FEMALE = "FEMALE"
    OTHER = "OTHER"
    PREFER_NOT_TO_SAY = "PREFER_NOT_TO_SAY"


class EmploymentStatus(str, Enum):
    ACTIVE = "ACTIVE"
    ON_LEAVE = "ON_LEAVE"
    SUSPENDED = "SUSPENDED"
    TERMINATED = "TERMINATED"
    RETIRED = "RETIRED"


class EmploymentType(str, Enum):
    PERMANENT = "PERMANENT"
    FIXED_TERM = "FIXED_TERM"
    CONTRACT = "CONTRACT"
    CASUAL = "CASUAL"
    INTERN = "INTERN"
    PART_TIME = "PART_TIME"



class PayFrequency(str, Enum):
    MONTHLY = "MONTHLY"
    BIWEEKLY = "BIWEEKLY"
    WEEKLY = "WEEKLY"
    DAILY = "DAILY"
    HOURLY = "HOURLY"


class CompensationBasis(str, Enum):
    SALARY = "SALARY"
    WAGE = "WAGE"

from enum import Enum


class AttendanceStatus(str, Enum):
    PRESENT = "PRESENT"
    ABSENT = "ABSENT"
    LATE = "LATE"
    HALF_DAY = "HALF_DAY"
    ON_LEAVE = "ON_LEAVE"
    HOLIDAY = "HOLIDAY"


class AttendanceSource(str, Enum):
    MANUAL = "MANUAL"
    IMPORT = "IMPORT"
    DEVICE = "DEVICE"
    SYSTEM = "SYSTEM"
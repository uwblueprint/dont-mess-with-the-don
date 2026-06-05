from enum import Enum


class EntityEnum(str, Enum):
    A = "A"
    B = "B"
    C = "C"
    D = "D"


class SimpleEntityEnum(str, Enum):
    A = "A"
    B = "B"
    C = "C"
    D = "D"


class RegistrationStatusEnum(str, Enum):
    WAITLIST = "waitlist"
    ACCEPTED = "accepted"
    CANCELLED = "cancelled"

from enum import Enum


class UserProfileType(str, Enum):
    CHILD = "child"
    GUEST = "guest"
    DEFAULT = "default"


class UserProvider(str, Enum):
    MICROSOFT = "microsoft"
    GOOGLE = "google"


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

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
    ACCEPTED = "accepted"
    CANCELLED = "cancelled"
    WAITLIST = "waitlist"


class EventFormatEnum(str, Enum):
    SIGNUP = "signup"
    DROPIN = "dropin"


class EventRegistrationTypeEnum(str, Enum):
    LOTTERY = "lottery"
    AUTO_APPROVE = "auto_approve"
    MANUAL_APPROVE = "manual_approve"

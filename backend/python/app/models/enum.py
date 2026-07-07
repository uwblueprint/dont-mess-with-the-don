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


class QuestionTypeEnum(str, Enum):
    SHORT_ANSWER = "short_answer"
    PARAGRAPH = "paragraph"
    MULTIPLE_CHOICE = "multiple_choice"
    CHECKBOXES = "checkboxes"
    DATE = "date"
    TIME = "time"
    EMAIL = "email"

"""Validation for R2 object keys stored in the database."""

import re
from typing import Annotated

from pydantic import AfterValidator

MAX_OBJECT_KEY_LENGTH = 512

# One or more `/`-separated segments of URL-safe characters. Anything else (spaces, `?`,
# `#`, `%`, `:` ...) would need encoding in the public URL, so it is rejected instead.
_SEGMENT = r"[A-Za-z0-9._-]+"
_OBJECT_KEY_RE = re.compile(rf"{_SEGMENT}(/{_SEGMENT})*")


def validate_object_key(v: str) -> str:
    """
    Ensure a value is a relative object key (e.g. `events/<id>/<uuid>.jpg`), not a URL.

    Allows only letters, digits, `.`, `_`, `-` and `/` between non-empty segments, so URLs,
    empty keys, leading/trailing/double slashes and characters that would break a URL are
    all rejected. Also rejects `.` / `..` segments and over-long keys.
    """
    if not _OBJECT_KEY_RE.fullmatch(v):
        raise ValueError(
            "must be an object key like 'events/<id>/<uuid>.jpg' "
            "(letters, digits, '.', '_', '-' and '/' only; not a URL)"
        )
    if any(segment in (".", "..") for segment in v.split("/")):
        raise ValueError("must not contain '.' or '..' segments")
    if len(v) > MAX_OBJECT_KEY_LENGTH:
        raise ValueError(f"must be at most {MAX_OBJECT_KEY_LENGTH} characters")
    return v


# Use as a field type. Validation then runs on every model that has the field.
ObjectKey = Annotated[str, AfterValidator(validate_object_key)]
ObjectKeys = list[ObjectKey]

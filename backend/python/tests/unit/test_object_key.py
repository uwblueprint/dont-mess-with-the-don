import pytest
from pydantic import TypeAdapter, ValidationError

from app.models.object_key import ObjectKeys, validate_object_key


@pytest.mark.parametrize(
    "key",
    [
        "a.jpg",
        "events/123/abc.jpg",
        "event-images/beach.png",
        "events/1f0e/7c9b4d2e-1a2b-4c3d-8e9f-0a1b2c3d4e5f.jpg",
        "waivers_signed/v1.2.pdf",
    ],
)
def test_valid_keys(key):
    assert validate_object_key(key) == key


@pytest.mark.parametrize(
    "key",
    [
        "https://example.com/a.jpg",
        "/leading/slash.jpg",
        "trailing/",
        "double//slash.jpg",
        "events/../secret.jpg",
        "events/./a.jpg",
        "",
        "has space.jpg",
        "query?.jpg",
        "frag#ment.jpg",
        "pct%20encoded.jpg",
        "back\\slash.jpg",
        "a/" * 300 + "a",
    ],
)
def test_invalid_keys(key):
    with pytest.raises(ValueError):
        validate_object_key(key)


def test_key_lists_reject_empty_entries():
    with pytest.raises(ValidationError):
        TypeAdapter(ObjectKeys).validate_python(["events/1/a.jpg", ""])

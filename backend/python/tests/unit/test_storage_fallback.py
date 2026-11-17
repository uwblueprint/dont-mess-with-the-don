import io
import logging
from typing import Any

import pytest

from app.config import Settings
from app.dependencies.services import build_storage_service
from app.models.enum import BucketVisibility
from app.services.implementations.storage_service import R2StorageService
from app.services.implementations.unconfigured_storage_service import UnconfiguredStorageService

LOGGER = logging.getLogger("test")

R2_SETTINGS = {
    "r2_access_key_id": "testing",
    "r2_secret_access_key": "testing",
    "r2_public_bucket_name": "dmwtd-public-test",
    "r2_private_bucket_name": "dmwtd-private-test",
    "r2_public_base_url": "https://cdn.example.org",
    "r2_endpoint_url": "https://example.r2.cloudflarestorage.com",
}
NO_R2_SETTINGS = {name: "" for name in R2_SETTINGS}


def make_settings(app_env: str, r2: dict[str, str]) -> Settings:
    # _env_file=None so a developer's local .env never leaks into these tests
    values: dict[str, Any] = {"_env_file": None, "app_env": app_env, **r2}
    return Settings(**values)


@pytest.mark.parametrize("app_env", ["development", "testing"])
def test_no_r2_settings_outside_production_gives_stub(app_env):
    storage = build_storage_service(LOGGER, make_settings(app_env, NO_R2_SETTINGS))
    assert isinstance(storage, UnconfiguredStorageService)


def test_no_r2_settings_in_production_fails():
    with pytest.raises(ValueError):
        build_storage_service(LOGGER, make_settings("production", NO_R2_SETTINGS))


def test_partial_r2_settings_fail_even_in_development():
    partial = {**NO_R2_SETTINGS, "r2_public_bucket_name": "dmwtd-public-dev"}
    with pytest.raises(ValueError):
        build_storage_service(LOGGER, make_settings("development", partial))


def test_full_r2_settings_give_r2():
    storage = build_storage_service(LOGGER, make_settings("development", R2_SETTINGS))
    assert isinstance(storage, R2StorageService)


def test_stub_urls_are_placeholders():
    storage = UnconfiguredStorageService()
    assert (
        storage.url_for("event-images/h.jpg", BucketVisibility.PUBLIC)
        == "https://r2-not-configured.invalid/public/event-images/h.jpg"
    )
    assert (
        storage.url_for("events/e1/a.jpg", BucketVisibility.PRIVATE, expires_in=300)
        == "https://r2-not-configured.invalid/private/events/e1/a.jpg"
    )


async def test_stub_uploads_and_deletes_raise():
    storage = UnconfiguredStorageService()
    with pytest.raises(RuntimeError):
        await storage.upload_file(io.BytesIO(b"x"), "a/b.jpg", BucketVisibility.PUBLIC)
    with pytest.raises(RuntimeError):
        await storage.delete_file("a/b.jpg", BucketVisibility.PRIVATE)

import io
import logging
from types import SimpleNamespace
from uuid import UUID

import boto3
import pytest
from botocore.exceptions import ClientError
from moto import mock_aws

from app.models.enum import BucketVisibility
from app.services.implementations.storage_service import R2StorageService

PUBLIC_BUCKET = "dmwtd-public-test"
PRIVATE_BUCKET = "dmwtd-private-test"


def make_settings(**overrides):
    values = {
        "r2_access_key_id": "testing",
        "r2_secret_access_key": "testing",
        "r2_public_bucket_name": PUBLIC_BUCKET,
        "r2_private_bucket_name": PRIVATE_BUCKET,
        "r2_public_base_url": "https://cdn.example.org/",
        "r2_key_prefix": "dev/",
        # moto only intercepts AWS hostnames, so tests use one instead of the R2 URL
        "r2_endpoint_url": "https://s3.us-east-1.amazonaws.com",
        "signed_url_ttl_media_seconds": 3600,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


@pytest.fixture
def s3():
    with mock_aws():
        client = boto3.client("s3", region_name="us-east-1")
        client.create_bucket(Bucket=PUBLIC_BUCKET)
        client.create_bucket(Bucket=PRIVATE_BUCKET)
        yield client


@pytest.mark.parametrize(
    "missing",
    [
        "r2_public_bucket_name",
        "r2_private_bucket_name",
        "r2_public_base_url",
        "r2_endpoint_url",
        "r2_access_key_id",
        "r2_secret_access_key",
    ],
)
def test_requires_config(missing):
    with pytest.raises(ValueError):
        R2StorageService(logging.getLogger(), make_settings(**{missing: ""}))


async def test_upload_goes_to_bucket_for_visibility_and_applies_prefix(s3):
    service = R2StorageService(logging.getLogger(), make_settings())

    public_key = await service.upload_file(
        io.BytesIO(b"pub"), "events/1/a.jpg", BucketVisibility.PUBLIC, "image/jpeg"
    )
    private_key = await service.upload_file(
        io.BytesIO(b"priv"), "users/1/b.jpg", BucketVisibility.PRIVATE
    )

    # the returned key is relative, so it is the same in every environment
    assert public_key == "events/1/a.jpg"
    assert private_key == "users/1/b.jpg"
    obj = s3.get_object(Bucket=PUBLIC_BUCKET, Key="dev/events/1/a.jpg")
    assert obj["Body"].read() == b"pub"
    assert obj["ContentType"] == "image/jpeg"
    assert s3.get_object(Bucket=PRIVATE_BUCKET, Key="dev/users/1/b.jpg")["Body"].read() == b"priv"
    assert "Contents" not in s3.list_objects_v2(Bucket=PUBLIC_BUCKET, Prefix="dev/users")


async def test_delete_removes_object_from_matching_bucket(s3):
    service = R2StorageService(logging.getLogger(), make_settings())
    await service.upload_file(io.BytesIO(b"x"), "a.txt", BucketVisibility.PRIVATE)

    await service.delete_file("a.txt", BucketVisibility.PRIVATE)

    assert "Contents" not in s3.list_objects_v2(Bucket=PRIVATE_BUCKET, Prefix="dev/a.txt")


async def test_upload_error_is_logged_and_reraised(s3, caplog):
    service = R2StorageService(
        logging.getLogger(), make_settings(r2_private_bucket_name="missing-bucket")
    )

    with caplog.at_level(logging.ERROR), pytest.raises(ClientError):
        await service.upload_file(io.BytesIO(b"x"), "a.txt", BucketVisibility.PRIVATE)

    assert "Failed to upload" in caplog.text


def test_public_url_uses_base_url_and_prefix_without_signing(monkeypatch):
    service = R2StorageService(logging.getLogger(), make_settings())

    def fail(*args, **kwargs):
        raise AssertionError("public URLs must not go through the S3 client")

    monkeypatch.setattr(service.client, "generate_presigned_url", fail)

    url = service.url_for("events/1/a.jpg", BucketVisibility.PUBLIC)

    assert url == "https://cdn.example.org/dev/events/1/a.jpg"


@pytest.mark.parametrize(("expires_in", "expected_ttl"), [(None, 3600), (300, 300)])
def test_private_url_is_signed_on_private_bucket(expires_in, expected_ttl):
    service = R2StorageService(logging.getLogger(), make_settings())

    url = service.url_for("users/1/b.jpg", BucketVisibility.PRIVATE, expires_in=expires_in)

    assert PRIVATE_BUCKET in url
    assert "dev/users/1/b.jpg" in url
    assert f"X-Amz-Expires={expected_ttl}" in url
    assert "X-Amz-Signature=" in url


def test_build_key_is_uuid_based_and_ignores_user_filename():
    service = R2StorageService(logging.getLogger(), make_settings())

    key = service.build_key("events/abc/", ".JPG")

    prefix, filename = key.rsplit("/", 1)
    assert prefix == "events/abc"
    stem, ext = filename.split(".")
    assert ext == "jpg"
    assert str(UUID(stem)) == stem


def test_client_signs_with_sigv4():
    service = R2StorageService(logging.getLogger(), make_settings())
    assert service.client.meta.config.signature_version == "s3v4"

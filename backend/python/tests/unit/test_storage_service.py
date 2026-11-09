import io
import logging
from types import SimpleNamespace

import boto3
import pytest
from botocore.exceptions import ClientError
from moto import mock_aws

from app.services.implementations.storage_service import R2StorageService

BUCKET = "dmwtd-test"


def make_settings(**overrides):
    values = {
        "r2_access_key_id": "testing",
        "r2_secret_access_key": "testing",
        "r2_bucket_name": BUCKET,
        "r2_key_prefix": "dev/",
        # moto only intercepts AWS hostnames, so tests use one instead of the R2 URL
        "r2_endpoint_url": "https://s3.us-east-1.amazonaws.com",
    }
    values.update(overrides)
    return SimpleNamespace(**values)


@pytest.fixture
def s3():
    with mock_aws():
        client = boto3.client("s3", region_name="us-east-1")
        client.create_bucket(Bucket=BUCKET)
        yield client


def test_requires_bucket():
    with pytest.raises(ValueError):
        R2StorageService(logging.getLogger(), make_settings(r2_bucket_name=""))


def test_requires_endpoint():
    with pytest.raises(ValueError):
        R2StorageService(logging.getLogger(), make_settings(r2_endpoint_url=""))


async def test_upload_applies_prefix_and_content_type(s3):
    service = R2StorageService(logging.getLogger(), make_settings())

    key = await service.upload_file(io.BytesIO(b"hello"), "waivers/a.pdf", "application/pdf")

    assert key == "dev/waivers/a.pdf"
    obj = s3.get_object(Bucket=BUCKET, Key=key)
    assert obj["Body"].read() == b"hello"
    assert obj["ContentType"] == "application/pdf"


async def test_delete_removes_object(s3):
    service = R2StorageService(logging.getLogger(), make_settings())
    key = await service.upload_file(io.BytesIO(b"x"), "a.txt")

    await service.delete_file("a.txt")

    assert "Contents" not in s3.list_objects_v2(Bucket=BUCKET, Prefix=key)


async def test_upload_error_is_logged_and_reraised(s3, caplog):
    service = R2StorageService(logging.getLogger(), make_settings(r2_bucket_name="missing-bucket"))

    with caplog.at_level(logging.ERROR), pytest.raises(ClientError):
        await service.upload_file(io.BytesIO(b"x"), "a.txt")

    assert "Failed to upload" in caplog.text

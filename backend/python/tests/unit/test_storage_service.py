import io
import logging
from types import SimpleNamespace

import boto3
import pytest
from botocore.exceptions import ClientError
from moto import mock_aws

from app.services.implementations.storage_service import S3StorageService

BUCKET = "dmwtd-test"


def make_settings(**overrides):
    values = {
        "aws_access_key_id": "testing",
        "aws_secret_access_key": "testing",
        "aws_region": "us-east-1",
        "s3_bucket_name": BUCKET,
        "s3_key_prefix": "dev/",
        "s3_endpoint_url": "",
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
        S3StorageService(logging.getLogger(), make_settings(s3_bucket_name=""))


def test_upload_applies_prefix_and_content_type(s3):
    service = S3StorageService(logging.getLogger(), make_settings())

    key = service.upload_file(io.BytesIO(b"hello"), "waivers/a.pdf", "application/pdf")

    assert key == "dev/waivers/a.pdf"
    obj = s3.get_object(Bucket=BUCKET, Key=key)
    assert obj["Body"].read() == b"hello"
    assert obj["ContentType"] == "application/pdf"


def test_delete_removes_object(s3):
    service = S3StorageService(logging.getLogger(), make_settings())
    key = service.upload_file(io.BytesIO(b"x"), "a.txt")

    service.delete_file("a.txt")

    assert "Contents" not in s3.list_objects_v2(Bucket=BUCKET, Prefix=key)


def test_upload_error_is_logged_and_reraised(s3, caplog):
    service = S3StorageService(logging.getLogger(), make_settings(s3_bucket_name="missing-bucket"))

    with caplog.at_level(logging.ERROR), pytest.raises(ClientError):
        service.upload_file(io.BytesIO(b"x"), "a.txt")

    assert "Failed to upload" in caplog.text

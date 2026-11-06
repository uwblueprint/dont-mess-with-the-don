from typing import BinaryIO

import boto3
from botocore.exceptions import ClientError

from app.config import Settings

from ..interfaces.storage_service import IStorageService


class S3StorageService(IStorageService):
    """
    StorageService implementation backed by AWS S3
    """

    def __init__(self, logger, settings: Settings):
        """
        Create an instance of S3StorageService

        :param logger: application's logger instance
        :param settings: application settings holding the S3 bucket/credentials
        :raises ValueError: if no bucket is configured
        """
        if not settings.s3_bucket_name:
            raise ValueError("S3_BUCKET_NAME is not configured")

        self.logger = logger
        self.bucket = settings.s3_bucket_name
        self.prefix = settings.s3_key_prefix

        client_kwargs: dict[str, str] = {}
        if settings.aws_region:
            client_kwargs["region_name"] = settings.aws_region
        if settings.aws_access_key_id and settings.aws_secret_access_key:
            client_kwargs["aws_access_key_id"] = settings.aws_access_key_id
            client_kwargs["aws_secret_access_key"] = settings.aws_secret_access_key
        if settings.s3_endpoint_url:
            client_kwargs["endpoint_url"] = settings.s3_endpoint_url
        self.client = boto3.client("s3", **client_kwargs)

    def _full_key(self, key: str) -> str:
        return f"{self.prefix}{key.lstrip('/')}"

    def upload_file(self, file_obj: BinaryIO, key: str, content_type: str | None = None) -> str:
        full_key = self._full_key(key)
        extra_args = {"ContentType": content_type} if content_type else None
        try:
            self.client.upload_fileobj(file_obj, self.bucket, full_key, ExtraArgs=extra_args)
        except ClientError as e:
            self.logger.error(f"Failed to upload {full_key} to S3. Reason = {e}")
            raise e
        return full_key

    def delete_file(self, key: str) -> None:
        full_key = self._full_key(key)
        try:
            self.client.delete_object(Bucket=self.bucket, Key=full_key)
        except ClientError as e:
            self.logger.error(f"Failed to delete {full_key} from S3. Reason = {e}")
            raise e

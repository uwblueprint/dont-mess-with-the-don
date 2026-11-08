import asyncio
from typing import BinaryIO

import boto3
from botocore.exceptions import ClientError

from app.config import Settings

from ..interfaces.storage_service import IStorageService


class R2StorageService(IStorageService):
    """
    StorageService implementation backed by Cloudflare R2
    """

    def __init__(self, logger, settings: Settings):
        """
        Create an instance of R2StorageService

        :param logger: application's logger instance
        :param settings: application settings holding the R2 bucket, endpoint and API token
        :raises ValueError: if no bucket or endpoint is configured
        """
        if not settings.r2_bucket_name:
            raise ValueError("R2_BUCKET_NAME is not configured")
        if not settings.r2_endpoint_url:
            raise ValueError(
                "R2_ENDPOINT_URL is not configured "
                "(expected https://<ACCOUNT_ID>.r2.cloudflarestorage.com)"
            )

        self.logger = logger
        self.bucket = settings.r2_bucket_name
        self.prefix = settings.r2_key_prefix

        client_kwargs: dict[str, str] = {"region_name": "auto"}
        if settings.r2_access_key_id and settings.r2_secret_access_key:
            client_kwargs["aws_access_key_id"] = settings.r2_access_key_id
            client_kwargs["aws_secret_access_key"] = settings.r2_secret_access_key
        if settings.r2_endpoint_url:
            client_kwargs["endpoint_url"] = settings.r2_endpoint_url
        self.client = boto3.client("s3", **client_kwargs)

    def _full_key(self, key: str) -> str:
        return f"{self.prefix}{key.lstrip('/')}"

    async def upload_file(
        self, file_obj: BinaryIO, key: str, content_type: str | None = None
    ) -> str:
        full_key = self._full_key(key)
        extra_args = {"ContentType": content_type} if content_type else None
        try:
            await asyncio.to_thread(
                self.client.upload_fileobj, file_obj, self.bucket, full_key, ExtraArgs=extra_args
            )
        except ClientError as e:
            self.logger.error(f"Failed to upload {full_key} to R2. Reason = {e}")
            raise e
        return full_key

    async def delete_file(self, key: str) -> None:
        full_key = self._full_key(key)
        try:
            await asyncio.to_thread(self.client.delete_object, Bucket=self.bucket, Key=full_key)
        except ClientError as e:
            self.logger.error(f"Failed to delete {full_key} from R2. Reason = {e}")
            raise e

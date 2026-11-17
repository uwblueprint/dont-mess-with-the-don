import asyncio
from typing import BinaryIO
from uuid import uuid4

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

from app.config import Settings
from app.models.enum import BucketVisibility

from ..interfaces.storage_service import IStorageService


def build_object_key(prefix: str, extension: str) -> str:
    return f"{prefix.strip('/')}/{uuid4()}.{extension.lstrip('.').lower()}"


class R2StorageService(IStorageService):
    """
    StorageService implementation backed by Cloudflare R2
    """

    def __init__(self, logger, settings: Settings):
        """
        Create an instance of R2StorageService

        :param logger: application's logger instance
        :param settings: application settings holding the R2 buckets, endpoint and API token
        :raises ValueError: if a bucket, the public base URL, the endpoint or the API
            credentials are not configured
        """
        if not settings.r2_access_key_id or not settings.r2_secret_access_key:
            # Without them every upload fails and signed URLs cannot be built
            raise ValueError("R2_ACCESS_KEY_ID and R2_SECRET_ACCESS_KEY must both be configured")
        if not settings.r2_public_bucket_name:
            raise ValueError("R2_PUBLIC_BUCKET_NAME is not configured")
        if not settings.r2_private_bucket_name:
            raise ValueError("R2_PRIVATE_BUCKET_NAME is not configured")
        if not settings.r2_public_base_url:
            raise ValueError("R2_PUBLIC_BASE_URL is not configured")
        if not settings.r2_endpoint_url:
            raise ValueError(
                "R2_ENDPOINT_URL is not configured "
                "(expected https://<ACCOUNT_ID>.r2.cloudflarestorage.com)"
            )

        self.logger = logger
        self.buckets = {
            BucketVisibility.PUBLIC: settings.r2_public_bucket_name,
            BucketVisibility.PRIVATE: settings.r2_private_bucket_name,
        }
        self.public_base_url = settings.r2_public_base_url.rstrip("/")
        self.default_signed_ttl = settings.signed_url_ttl_media_seconds
        self.prefix = settings.r2_key_prefix

        self.client = boto3.client(
            "s3",
            region_name="auto",
            endpoint_url=settings.r2_endpoint_url,
            aws_access_key_id=settings.r2_access_key_id,
            aws_secret_access_key=settings.r2_secret_access_key,
            # R2 only accepts SigV4; pin it rather than rely on boto3's default
            config=Config(signature_version="s3v4"),
        )

    def _full_key(self, key: str) -> str:
        return f"{self.prefix}{key.lstrip('/')}"

    async def upload_file(
        self,
        file_obj: BinaryIO,
        key: str,
        visibility: BucketVisibility,
        content_type: str | None = None,
    ) -> str:
        full_key = self._full_key(key)
        extra_args = {"ContentType": content_type} if content_type else None
        try:
            await asyncio.to_thread(
                self.client.upload_fileobj,
                file_obj,
                self.buckets[visibility],
                full_key,
                ExtraArgs=extra_args,
            )
        except ClientError as e:
            self.logger.error(f"Failed to upload {full_key} to R2. Reason = {e}")
            raise e
        return key.lstrip("/")

    async def delete_file(self, key: str, visibility: BucketVisibility) -> None:
        full_key = self._full_key(key)
        try:
            await asyncio.to_thread(
                self.client.delete_object, Bucket=self.buckets[visibility], Key=full_key
            )
        except ClientError as e:
            self.logger.error(f"Failed to delete {full_key} from R2. Reason = {e}")
            raise e

    def url_for(
        self, key: str, visibility: BucketVisibility, *, expires_in: int | None = None
    ) -> str:
        if visibility == BucketVisibility.PUBLIC:
            return f"{self.public_base_url}/{self._full_key(key)}"
        return self.client.generate_presigned_url(
            "get_object",
            Params={"Bucket": self.buckets[BucketVisibility.PRIVATE], "Key": self._full_key(key)},
            ExpiresIn=expires_in or self.default_signed_ttl,
        )

    def build_key(self, prefix: str, extension: str) -> str:
        return build_object_key(prefix, extension)

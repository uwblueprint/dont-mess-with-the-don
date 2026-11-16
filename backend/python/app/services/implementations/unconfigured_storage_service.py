from typing import BinaryIO

from app.models.enum import BucketVisibility

from ..interfaces.storage_service import IStorageService
from .storage_service import build_object_key

PLACEHOLDER_BASE_URL = "https://r2-not-configured.invalid"


class UnconfiguredStorageService(IStorageService):
    """
    Stand-in used in development and testing when no R2 settings are set, so read
    routes still work locally. URLs are placeholders that never resolve; uploads and
    deletes raise. Never used in production.
    """

    async def upload_file(
        self,
        file_obj: BinaryIO,
        key: str,
        visibility: BucketVisibility,
        content_type: str | None = None,
    ) -> str:
        raise RuntimeError("R2 is not configured; set the R2_* settings to upload files")

    async def delete_file(self, key: str, visibility: BucketVisibility) -> None:
        raise RuntimeError("R2 is not configured; set the R2_* settings to delete files")

    def url_for(
        self, key: str, visibility: BucketVisibility, *, expires_in: int | None = None
    ) -> str:
        return f"{PLACEHOLDER_BASE_URL}/{visibility.value}/{key.lstrip('/')}"

    def build_key(self, prefix: str, extension: str) -> str:
        return build_object_key(prefix, extension)

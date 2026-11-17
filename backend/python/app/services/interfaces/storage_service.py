from abc import ABC, abstractmethod
from typing import BinaryIO

from app.models.enum import BucketVisibility


class IStorageService(ABC):
    """
    StorageService interface for object storage (Cloudflare R2).

    Keys exclude the environment prefix. Public objects get permanent URLs; private
    objects are reachable only through signed URLs.
    """

    @abstractmethod
    async def upload_file(
        self,
        file_obj: BinaryIO,
        key: str,
        visibility: BucketVisibility,
        content_type: str | None = None,
    ) -> str:
        """
        Uploads a file to the bucket matching `visibility`

        :param file_obj: binary file-like object to upload
        :param key: object key, relative to the environment's key prefix
        :param visibility: public or private bucket
        :param content_type: MIME type to store with the object, defaults to None
        :return: the stored key (relative, safe to persist in the database)
        :raises Exception: if the upload fails
        """
        pass

    @abstractmethod
    async def delete_file(self, key: str, visibility: BucketVisibility) -> None:
        """
        Deletes a file from the object store.
        Deleting a missing key is not an error.

        :param key: object key, relative to the environment's key prefix
        :param visibility: public or private bucket
        :raises Exception: if the delete fails
        """
        pass

    @abstractmethod
    def url_for(
        self, key: str, visibility: BucketVisibility, *, expires_in: int | None = None
    ) -> str:
        """
        Builds the URL an API response returns for an object. No network call.

        Public objects get a permanent URL from the public base URL. Private objects
        get a signed URL, which must never be persisted.

        :param key: object key, relative to the environment's key prefix
        :param visibility: which bucket the object is in
        :param expires_in: signed URL lifetime in seconds (private only); defaults to
            SIGNED_URL_TTL_MEDIA_SECONDS
        """
        pass

    @abstractmethod
    def build_key(self, prefix: str, extension: str) -> str:
        """
        Builds a UUID-based object key such as `events/{event_id}/{uuid}.jpg`.
        Never derived from a user-supplied filename.

        :param prefix: key "folder", e.g. `events/<event_id>`
        :param extension: file extension without the dot
        """
        pass

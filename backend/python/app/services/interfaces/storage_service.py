from abc import ABC, abstractmethod
from typing import BinaryIO


class IStorageService(ABC):
    """
    StorageService interface for handling object storage (file upload/delete)
    """

    @abstractmethod
    def upload_file(self, file_obj: BinaryIO, key: str, content_type: str | None = None) -> str:
        """
        Uploads a file to the object store

        :param file_obj: binary file-like object to upload
        :param key: object key, relative to the environment's key prefix
        :param content_type: MIME type to store with the object, defaults to None
        :return: the full stored key (including the environment prefix)
        :raises Exception: if the upload fails
        """
        pass

    @abstractmethod
    def delete_file(self, key: str) -> None:
        """
        Deletes a file from the object store. Deleting a missing key is not an error.

        :param key: object key, relative to the environment's key prefix
        :raises Exception: if the delete fails
        """
        pass

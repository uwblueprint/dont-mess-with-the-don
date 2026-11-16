from app.models.enum import BucketVisibility
from app.models.user import User, UserRead
from app.services.interfaces.storage_service import IStorageService


def user_read(user: User, storage: IStorageService) -> UserRead:
    pic = (
        storage.url_for(user.profile_pic_key, BucketVisibility.PRIVATE)
        if user.profile_pic_key
        else None
    )
    return UserRead.model_validate({**user.model_dump(), "profile_pic_url": pic})

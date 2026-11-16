from app.models.enum import BucketVisibility
from app.models.event import Event, EventRead
from app.services.interfaces.storage_service import IStorageService


def event_read(
    event: Event, storage: IStorageService, *, include_photos: bool = False
) -> EventRead:
    """`include_photos`: True only when the caller may see post-event photos."""
    photos = (
        [storage.url_for(key, BucketVisibility.PRIVATE) for key in event.post_event_photo_keys]
        if include_photos
        else []
    )
    return EventRead.model_validate(
        {
            **event.model_dump(),
            "headline_image_url": storage.url_for(
                event.headline_image_key, BucketVisibility.PUBLIC
            ),
            "post_event_photo_urls": photos,
        }
    )

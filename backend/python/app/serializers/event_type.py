from app.models.enum import BucketVisibility
from app.models.event_type import EventType, EventTypeRead
from app.services.interfaces.storage_service import IStorageService


def event_type_read(event_type: EventType, storage: IStorageService) -> EventTypeRead:
    return EventTypeRead.model_validate(
        {
            **event_type.model_dump(),
            "headline_image_url": storage.url_for(
                event_type.headline_image_key, BucketVisibility.PUBLIC
            ),
        }
    )

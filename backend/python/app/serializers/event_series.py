from app.models.enum import BucketVisibility
from app.models.event_series import EventSeries, EventSeriesRead
from app.services.interfaces.storage_service import IStorageService


def event_series_read(series: EventSeries, storage: IStorageService) -> EventSeriesRead:
    return EventSeriesRead.model_validate(
        {
            **series.model_dump(),
            "headline_image_url": storage.url_for(
                series.headline_image_key, BucketVisibility.PUBLIC
            ),
        }
    )

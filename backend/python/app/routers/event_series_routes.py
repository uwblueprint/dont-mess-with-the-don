from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies.services import get_event_series_service
from app.models import get_session
from app.models.event_series import EventSeriesCreate, EventSeriesRead, EventSeriesUpdate
from app.services.implementations.event_series_service import EventSeriesService

router = APIRouter(prefix="/event-series", tags=["event-series"])


@router.get("/", response_model=list[EventSeriesRead])
async def get_event_series_list(
    session: AsyncSession = Depends(get_session),
    event_series_service: EventSeriesService = Depends(get_event_series_service),
) -> list[EventSeriesRead]:
    try:
        event_series_list = await event_series_service.get_event_series_list(session)
        return [EventSeriesRead.model_validate(event_series) for event_series in event_series_list]
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred",
        ) from e


@router.get("/{event_series_id}", response_model=EventSeriesRead)
async def get_event_series(
    event_series_id: UUID,
    session: AsyncSession = Depends(get_session),
    event_series_service: EventSeriesService = Depends(get_event_series_service),
) -> EventSeriesRead:
    try:
        event_series = await event_series_service.get_event_series(session, event_series_id)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred",
        ) from e
    if not event_series:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Event series with id {event_series_id} not found",
        )
    return EventSeriesRead.model_validate(event_series)


@router.post("/", response_model=EventSeriesRead, status_code=status.HTTP_201_CREATED)
async def create_event_series(
    event_series: EventSeriesCreate,
    session: AsyncSession = Depends(get_session),
    event_series_service: EventSeriesService = Depends(get_event_series_service),
) -> EventSeriesRead:
    try:
        created_event_series = await event_series_service.create_event_series(session, event_series)
        return EventSeriesRead.model_validate(created_event_series)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred",
        ) from e


@router.patch("/{event_series_id}", response_model=EventSeriesRead)
async def update_event_series(
    event_series_id: UUID,
    event_series: EventSeriesUpdate,
    session: AsyncSession = Depends(get_session),
    event_series_service: EventSeriesService = Depends(get_event_series_service),
) -> EventSeriesRead:
    try:
        updated_event_series = await event_series_service.update_event_series(
            session, event_series_id, event_series
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred",
        ) from e
    if not updated_event_series:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Event series with id {event_series_id} not found",
        )
    return EventSeriesRead.model_validate(updated_event_series)


@router.delete("/{event_series_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_event_series(
    event_series_id: UUID,
    session: AsyncSession = Depends(get_session),
    event_series_service: EventSeriesService = Depends(get_event_series_service),
) -> None:
    try:
        success = await event_series_service.delete_event_series(session, event_series_id)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred",
        ) from e
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Event series with id {event_series_id} not found",
        )

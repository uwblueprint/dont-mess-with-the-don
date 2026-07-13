from datetime import date, datetime, time
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from fastapi import status as http_status
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies.services import get_event_service
from app.models import get_session
from app.models.event import EventCreate, EventRead, EventUpdate
from app.services.implementations.event_service import EventService

router = APIRouter(prefix="/events", tags=["events"])


@router.get("", response_model=list[EventRead])
async def get_events(
    status: str | None = None,
    event_type: UUID | None = None,
    location: str | None = None,
    starts_after: date | None = None,
    starts_before: date | None = None,
    recurrence: str | None = None,
    session: AsyncSession = Depends(get_session),
    event_service: EventService = Depends(get_event_service),
) -> list[EventRead]:
    """Retrieve all events"""
    try:
        starts_after_datetime = (
            datetime.combine(starts_after, time.min) if starts_after is not None else None
        )
        starts_before_datetime = (
            datetime.combine(starts_before, time.max) if starts_before is not None else None
        )
        events = await event_service.get_events(
            session,
            status=status,
            event_type=event_type,
            location=location,
            starts_after=starts_after_datetime,
            starts_before=starts_before_datetime,
            recurrence=recurrence,
        )
        return [EventRead.model_validate(event) for event in events]
    except Exception as e:
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        ) from e


@router.post("", response_model=EventRead, status_code=http_status.HTTP_201_CREATED)
async def create_event(
    event: EventCreate,
    session: AsyncSession = Depends(get_session),
    event_service: EventService = Depends(get_event_service),
) -> EventRead:
    """Create a new event"""
    try:
        created_event = await event_service.create_event(session, event)
        return EventRead.model_validate(created_event)
    except Exception as e:
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        ) from e


@router.get("/{event_id}", response_model=EventRead)
async def get_event(
    event_id: UUID,
    session: AsyncSession = Depends(get_session),
    event_service: EventService = Depends(get_event_service),
) -> EventRead:
    """Get a single event by ID"""
    event = await event_service.get_event(session, event_id)
    if not event:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=f"Event with id {event_id} not found",
        )
    return EventRead.model_validate(event)


@router.patch("/{event_id}", response_model=EventRead)
async def update_event(
    event_id: UUID,
    event: EventUpdate,
    session: AsyncSession = Depends(get_session),
    event_service: EventService = Depends(get_event_service),
) -> EventRead:
    """Update an existing event"""
    updated_event = await event_service.update_event(session, event_id, event)
    if not updated_event:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=f"Event with id {event_id} not found",
        )
    return EventRead.model_validate(updated_event)


@router.delete("/{event_id}", status_code=http_status.HTTP_204_NO_CONTENT)
async def delete_event(
    event_id: UUID,
    session: AsyncSession = Depends(get_session),
    event_service: EventService = Depends(get_event_service),
) -> None:
    """Delete an event"""
    success = await event_service.delete_event(session, event_id)
    if not success:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=f"Event with id {event_id} not found",
        )

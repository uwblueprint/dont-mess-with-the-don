from datetime import date, datetime, time
from urllib.parse import urlencode
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from fastapi import status as http_status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.dependencies.auth import get_optional_user, require_admin
from app.dependencies.services import (
    get_event_service,
    get_form_submission_service,
    get_storage_service,
)
from app.models import get_session
from app.models.event import EventCheckInLink, EventCreate, EventRead, EventUpdate
from app.models.form_submission import FormSubmissionRead
from app.models.user import User
from app.serializers.event import event_read
from app.services.implementations.event_service import EventService
from app.services.implementations.form_submission_service import FormSubmissionService
from app.services.interfaces.storage_service import IStorageService
from app.utilities.photo_access import get_event_ids_with_visible_photos

router = APIRouter(prefix="/events", tags=["events"])


@router.get("", response_model=list[EventRead])
async def get_events(
    status: str | None = None,
    event_type: UUID | None = None,
    location: str | None = None,
    starts_after: date | None = None,
    starts_before: date | None = None,
    session: AsyncSession = Depends(get_session),
    event_service: EventService = Depends(get_event_service),
    storage: IStorageService = Depends(get_storage_service),
    current_user: User | None = Depends(get_optional_user),
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
        )
        # Post-event photos only for admins and each event's attendees
        visible_photo_event_ids = await get_event_ids_with_visible_photos(
            session, current_user, [e.id for e in events]
        )
        return [
            event_read(e, storage, include_photos=e.id in visible_photo_event_ids) for e in events
        ]
    except Exception as e:
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        ) from e


@router.post(
    "",
    response_model=EventRead,
    status_code=http_status.HTTP_201_CREATED,
    dependencies=[Depends(require_admin)],
)
async def create_event(
    event: EventCreate,
    session: AsyncSession = Depends(get_session),
    event_service: EventService = Depends(get_event_service),
    storage: IStorageService = Depends(get_storage_service),
) -> EventRead:
    """Create a new event"""
    try:
        created_event = await event_service.create_event(session, event)
        return event_read(created_event, storage, include_photos=True)
    except Exception as e:
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        ) from e


@router.get("/{event_id}", response_model=EventRead)
async def get_event(
    event_id: UUID,
    session: AsyncSession = Depends(get_session),
    event_service: EventService = Depends(get_event_service),
    storage: IStorageService = Depends(get_storage_service),
    current_user: User | None = Depends(get_optional_user),
) -> EventRead:
    """Get a single event by ID"""
    event = await event_service.get_event(session, event_id)
    if not event:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=f"Event with id {event_id} not found",
        )
    visible_photo_event_ids = await get_event_ids_with_visible_photos(
        session, current_user, [event.id]
    )
    return event_read(event, storage, include_photos=event.id in visible_photo_event_ids)


@router.get(
    "/{event_id}/feedback",
    response_model=list[FormSubmissionRead],
    dependencies=[Depends(require_admin)],
)
async def get_event_feedback(
    event_id: UUID,
    session: AsyncSession = Depends(get_session),
    form_submission_service: FormSubmissionService = Depends(get_form_submission_service),
) -> list[FormSubmissionRead]:
    """Get all feedback submitted for an event"""
    try:
        feedback = await form_submission_service.get_event_feedback(session, event_id)
    except Exception as e:
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        ) from e
    if feedback is None:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=f"Event with id {event_id} not found",
        )
    return [FormSubmissionRead.model_validate(submission) for submission in feedback]


@router.get(
    "/{event_id}/check-in-link",
    response_model=EventCheckInLink,
    dependencies=[Depends(require_admin)],
)
async def get_event_check_in_link(
    event_id: UUID,
    session: AsyncSession = Depends(get_session),
    event_service: EventService = Depends(get_event_service),
) -> EventCheckInLink:
    """Get the frontend check-in link for an event (the URL its QR code encodes)"""
    event = await event_service.get_event(session, event_id)
    if not event:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=f"Event with id {event_id} not found",
        )
    query = urlencode({"event": str(event.id), "token": event.check_in_token})
    return EventCheckInLink(url=f"{settings.frontend_url.rstrip('/')}/check-in?{query}")


@router.patch("/{event_id}", response_model=EventRead, dependencies=[Depends(require_admin)])
async def update_event(
    event_id: UUID,
    event: EventUpdate,
    session: AsyncSession = Depends(get_session),
    event_service: EventService = Depends(get_event_service),
    storage: IStorageService = Depends(get_storage_service),
) -> EventRead:
    """Update an existing event"""
    updated_event = await event_service.update_event(session, event_id, event)
    if not updated_event:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=f"Event with id {event_id} not found",
        )
    return event_read(updated_event, storage, include_photos=True)


@router.delete(
    "/{event_id}",
    status_code=http_status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_admin)],
)
async def delete_event(
    event_id: UUID,
    session: AsyncSession = Depends(get_session),
    event_service: EventService = Depends(get_event_service),
) -> None:
    """Delete an event"""
    try:
        success = await event_service.delete_event(session, event_id)
    except IntegrityError as e:
        # e.g. signed waivers (legal records) or registrations still point at this event
        raise HTTPException(
            status_code=http_status.HTTP_409_CONFLICT,
            detail="Event has records that must be kept (such as signed waivers)",
        ) from e
    if not success:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=f"Event with id {event_id} not found",
        )

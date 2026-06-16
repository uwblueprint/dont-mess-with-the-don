from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies.services import get_event_type_service
from app.models import get_session
from app.models.event_type import EventTypeCreate, EventTypeRead, EventTypeUpdate
from app.services.implementations.event_type_service import EventTypeService

router = APIRouter(prefix="/event-types", tags=["event-types"])


@router.get("/", response_model=list[EventTypeRead])
async def get_event_types(
    session: AsyncSession = Depends(get_session),
    event_type_service: EventTypeService = Depends(get_event_type_service),
) -> list[EventTypeRead]:
    """Retrieve all event types"""
    event_types = await event_type_service.get_event_types(session)
    return [EventTypeRead.model_validate(event_type) for event_type in event_types]


@router.get("/{event_type_id}", response_model=EventTypeRead)
async def get_event_type(
    event_type_id: UUID,
    session: AsyncSession = Depends(get_session),
    event_type_service: EventTypeService = Depends(get_event_type_service),
) -> EventTypeRead:
    """Get a single event type by ID"""
    event_type = await event_type_service.get_event_type(session, event_type_id)
    if not event_type:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"EventType with id {event_type_id} not found",
        )
    return EventTypeRead.model_validate(event_type)


@router.post("/", response_model=EventTypeRead, status_code=status.HTTP_201_CREATED)
async def create_event_type(
    event_type_data: EventTypeCreate,
    session: AsyncSession = Depends(get_session),
    event_type_service: EventTypeService = Depends(get_event_type_service),
) -> EventTypeRead:
    """Create a new event type"""
    try:
        created_event_type = await event_type_service.create_event_type(session, event_type_data)
        return EventTypeRead.model_validate(created_event_type)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)) from e


@router.put("/{event_type_id}", response_model=EventTypeRead)
async def update_event_type(
    event_type_id: UUID,
    event_type_data: EventTypeUpdate,
    session: AsyncSession = Depends(get_session),
    event_type_service: EventTypeService = Depends(get_event_type_service),
) -> EventTypeRead:
    """Update an existing event type"""
    try:
        updated_event_type = await event_type_service.update_event_type(
            session, event_type_id, event_type_data
        )
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)) from e

    if not updated_event_type:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"EventType with id {event_type_id} not found",
        )
    return EventTypeRead.model_validate(updated_event_type)


@router.delete("/{event_type_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_event_type(
    event_type_id: UUID,
    session: AsyncSession = Depends(get_session),
    event_type_service: EventTypeService = Depends(get_event_type_service),
) -> None:
    """Delete an event type by ID"""
    try:
        deleted = await event_type_service.delete_event_type(session, event_type_id)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)) from e

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"EventType with id {event_type_id} not found",
        )

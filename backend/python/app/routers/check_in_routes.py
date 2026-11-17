from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies.auth import get_current_user
from app.dependencies.services import get_check_in_service
from app.models import get_session
from app.models.check_in import CheckInStatusRead
from app.models.event import Event
from app.models.user import User
from app.services.implementations.check_in_service import (
    CheckInService,
    EventNotFoundError,
    InvalidCheckInTokenError,
    toronto_now,
)

# Token-gated check-in for any logged-in user (the token comes from the event's QR code)
router = APIRouter(prefix="/events", tags=["check-in"])


async def _get_event_or_raise(
    check_in_service: CheckInService, session: AsyncSession, event_id: UUID, token: str
) -> Event:
    try:
        return await check_in_service.get_event_for_check_in(session, event_id, token)
    except EventNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e
    except InvalidCheckInTokenError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e)) from e


@router.get("/{event_id}/check-in", response_model=CheckInStatusRead)
async def get_check_in_status(
    event_id: UUID,
    token: str,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
    check_in_service: CheckInService = Depends(get_check_in_service),
) -> CheckInStatusRead:
    """The event, whether check-in is open, and who the caller can check in"""
    event = await _get_event_or_raise(check_in_service, session, event_id, token)
    return await check_in_service.get_check_in_status(session, event, current_user, toronto_now())

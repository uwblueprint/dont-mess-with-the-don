from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies.auth import ensure_can_act_for, get_current_user
from app.dependencies.services import get_check_in_service
from app.models import get_session
from app.models.check_in import (
    CheckInPersonResult,
    CheckInRequest,
    CheckInResponse,
    CheckInStatusRead,
    CheckInWindowState,
)
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


@router.post("/{event_id}/check-in", response_model=CheckInResponse)
async def check_in(
    event_id: UUID,
    body: CheckInRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
    check_in_service: CheckInService = Depends(get_check_in_service),
) -> CheckInResponse:
    """Check in the caller, or the given people (the caller and/or their children)"""
    assert current_user.id is not None
    if body.user_ids is not None and not body.user_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="user_ids must not be empty; leave it out to check yourself in",
        )
    user_ids = list(dict.fromkeys(body.user_ids or [current_user.id]))

    event = await _get_event_or_raise(check_in_service, session, event_id, body.token)

    now = toronto_now()
    window = check_in_service.get_window(event, now)
    if window.state == CheckInWindowState.NOT_OPEN:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Check-in opens at {window.opens_at.isoformat()}",
        )
    if window.state == CheckInWindowState.CLOSED:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Check-in has closed")

    # Check everyone before writing anything, so a 403 leaves no partial check-in
    for user_id in user_ids:
        await ensure_can_act_for(session, current_user, user_id)

    results = []
    for user_id in user_ids:
        result = await check_in_service.check_in_person(session, event.id, user_id, now)
        results.append(CheckInPersonResult(user_id=user_id, result=result))
    return CheckInResponse(results=results)

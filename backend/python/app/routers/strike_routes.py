from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies.auth import require_admin
from app.dependencies.services import get_strike_service
from app.models import get_session
from app.models.strike import StrikeCreate, StrikeRead, StrikeRevoke
from app.models.user import User
from app.services.implementations.check_in_service import toronto_now
from app.services.implementations.strike_service import (
    StrikeAlreadyRevokedError,
    StrikeNotFoundError,
    StrikeService,
    StrikeTargetNotFoundError,
)

router = APIRouter(tags=["strikes"])


@router.get("/strikes", response_model=list[StrikeRead], dependencies=[Depends(require_admin)])
async def list_strikes(
    user_id: int | None = None,
    event_id: UUID | None = None,
    session: AsyncSession = Depends(get_session),
    strike_service: StrikeService = Depends(get_strike_service),
) -> list[StrikeRead]:
    """All strikes, newest first, optionally filtered by user and/or event (admin)"""
    strikes = await strike_service.list_strikes(session, user_id=user_id, event_id=event_id)
    now = toronto_now()
    return [StrikeRead.from_strike(strike, now) for strike in strikes]


@router.post("/strikes", response_model=StrikeRead, status_code=status.HTTP_201_CREATED)
async def create_manual_strike(
    data: StrikeCreate,
    admin: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
    strike_service: StrikeService = Depends(get_strike_service),
) -> StrikeRead:
    """Give someone a strike by hand (admin). A note explaining why is required."""
    assert admin.id is not None
    try:
        strike = await strike_service.create_manual_strike(session, data, issued_by=admin.id)
    except StrikeTargetNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
    return StrikeRead.from_strike(strike, toronto_now())


@router.post("/strikes/{strike_id}/revoke", response_model=StrikeRead)
async def revoke_strike(
    strike_id: UUID,
    data: StrikeRevoke,
    admin: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
    strike_service: StrikeService = Depends(get_strike_service),
) -> StrikeRead:
    """Revoke a strike so it no longer counts (admin). A reason is required."""
    assert admin.id is not None
    try:
        strike = await strike_service.revoke_strike(
            session, strike_id, reason=data.reason, revoked_by=admin.id
        )
    except StrikeNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e
    except StrikeAlreadyRevokedError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e)) from e
    return StrikeRead.from_strike(strike, toronto_now())

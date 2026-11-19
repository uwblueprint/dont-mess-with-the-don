from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies.auth import require_admin
from app.dependencies.services import get_strike_service
from app.models import get_session
from app.models.strike import StrikeCreate, StrikeRead
from app.models.user import User
from app.services.implementations.check_in_service import toronto_now
from app.services.implementations.strike_service import (
    StrikeService,
    StrikeTargetNotFoundError,
)

router = APIRouter(tags=["strikes"])


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

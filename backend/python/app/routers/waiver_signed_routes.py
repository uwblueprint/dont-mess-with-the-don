from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.dependencies.auth import ensure_can_act_for, get_current_user
from app.dependencies.services import get_storage_service
from app.models import get_session
from app.models.enum import BucketVisibility
from app.models.user import User
from app.models.waiver_signed import WaiverSigned, WaiverSignedUrl
from app.services.interfaces.storage_service import IStorageService

router = APIRouter(prefix="/waiver-signed", tags=["waiver-signed"])


@router.get("/{waiver_signed_id}/url", response_model=WaiverSignedUrl)
async def get_waiver_signed_url(
    waiver_signed_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
    storage: IStorageService = Depends(get_storage_service),
) -> WaiverSignedUrl:
    """Short-lived URL for a completed waiver.

    Only the waiver's owner, their guardian or an admin can get one. The URL is signed
    per request and never stored.
    """
    waiver = await session.get(WaiverSigned, waiver_signed_id)
    if waiver is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Signed waiver with id {waiver_signed_id} not found",
        )
    await ensure_can_act_for(session, current_user, waiver.user_id)
    return WaiverSignedUrl(
        url=storage.url_for(
            waiver.document_key,
            BucketVisibility.PRIVATE,
            expires_in=settings.signed_url_ttl_waiver_signed_seconds,
        ),
        expires_in=settings.signed_url_ttl_waiver_signed_seconds,
    )

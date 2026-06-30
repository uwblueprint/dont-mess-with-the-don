from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies.services import get_confirmation_request_service
from app.models import get_session
from app.models.confirmation_requests import (
    ConfirmationRequestCreate,
    ConfirmationRequestRead,
    ConfirmationRequestUpdate,
)
from app.services.implementations.confirmation_request_service import ConfirmationRequestService

router = APIRouter(prefix="/confirmation_requests", tags=["confirmation_requests"])


@router.get("/", response_model=list[ConfirmationRequestRead])
async def get_confirmation_requests(
    session: AsyncSession = Depends(get_session),
    confirmation_request_service: ConfirmationRequestService = Depends(
        get_confirmation_request_service
    ),
) -> list[ConfirmationRequestRead]:
    try:
        requests = await confirmation_request_service.get_confirmation_requests(session)
        return [ConfirmationRequestRead.model_validate(r) for r in requests]
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred",
        ) from e


@router.get("/event/{event_id}", response_model=list[ConfirmationRequestRead])
async def get_confirmation_requests_by_event(
    event_id: UUID,
    session: AsyncSession = Depends(get_session),
    confirmation_request_service: ConfirmationRequestService = Depends(
        get_confirmation_request_service
    ),
) -> list[ConfirmationRequestRead]:
    try:
        requests = await confirmation_request_service.get_confirmation_requests_by_event(
            session, event_id
        )
        return [ConfirmationRequestRead.model_validate(r) for r in requests]
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred",
        ) from e


@router.get("/{request_id}", response_model=ConfirmationRequestRead)
async def get_confirmation_request(
    request_id: UUID,
    session: AsyncSession = Depends(get_session),
    confirmation_request_service: ConfirmationRequestService = Depends(
        get_confirmation_request_service
    ),
) -> ConfirmationRequestRead:
    try:
        confirmation_request = await confirmation_request_service.get_confirmation_request(
            session, request_id
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred",
        ) from e
    if not confirmation_request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Confirmation request with id {request_id} not found",
        )
    return ConfirmationRequestRead.model_validate(confirmation_request)


@router.post("/", response_model=ConfirmationRequestRead, status_code=status.HTTP_201_CREATED)
async def create_confirmation_request(
    data: ConfirmationRequestCreate,
    session: AsyncSession = Depends(get_session),
    confirmation_request_service: ConfirmationRequestService = Depends(
        get_confirmation_request_service
    ),
) -> ConfirmationRequestRead:
    try:
        created = await confirmation_request_service.create_confirmation_request(session, data)
        return ConfirmationRequestRead.model_validate(created)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred",
        ) from e


@router.patch("/{request_id}", response_model=ConfirmationRequestRead)
async def update_confirmation_request(
    request_id: UUID,
    data: ConfirmationRequestUpdate,
    session: AsyncSession = Depends(get_session),
    confirmation_request_service: ConfirmationRequestService = Depends(
        get_confirmation_request_service
    ),
) -> ConfirmationRequestRead:
    try:
        updated = await confirmation_request_service.update_confirmation_request(
            session, request_id, data
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred",
        ) from e
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Confirmation request with id {request_id} not found",
        )
    return ConfirmationRequestRead.model_validate(updated)


@router.delete("/{request_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_confirmation_request(
    request_id: UUID,
    session: AsyncSession = Depends(get_session),
    confirmation_request_service: ConfirmationRequestService = Depends(
        get_confirmation_request_service
    ),
) -> None:
    try:
        success = await confirmation_request_service.delete_confirmation_request(
            session, request_id
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred",
        ) from e
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Confirmation request with id {request_id} not found",
        )

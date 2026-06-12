from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies.services import get_registration_service
from app.models import get_session
from app.models.registration import RegistrationCreate, RegistrationRead, RegistrationUpdate
from app.services.implementations.registration_service import RegistrationService

router = APIRouter(prefix="/registrations", tags=["registrations"])


@router.get("/", response_model=list[RegistrationRead])
async def get_registrations(
    session: AsyncSession = Depends(get_session),
    registration_service: RegistrationService = Depends(get_registration_service),
) -> list[RegistrationRead]:
    """Retrieve all registrations"""
    try:
        registrations = await registration_service.get_registrations(session)
        return [RegistrationRead.model_validate(reg) for reg in registrations]
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        ) from e


@router.get("/{registration_id}", response_model=RegistrationRead)
async def get_registration(
    registration_id: int,
    session: AsyncSession = Depends(get_session),
    registration_service: RegistrationService = Depends(get_registration_service),
) -> RegistrationRead:
    """Get a single registration by ID"""
    try:
        registration = await registration_service.get_registration(session, registration_id)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        ) from e

    if not registration:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Registration with id {registration_id} not found",
        )
    return RegistrationRead.model_validate(registration)


@router.post("/", response_model=RegistrationRead, status_code=status.HTTP_201_CREATED)
async def create_registration(
    registration: RegistrationCreate,
    session: AsyncSession = Depends(get_session),
    registration_service: RegistrationService = Depends(get_registration_service),
) -> RegistrationRead:
    """Create a new registration"""
    try:
        created_registration = await registration_service.create_registration(session, registration)
        return RegistrationRead.model_validate(created_registration)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        ) from e


@router.put("/{registration_id}", response_model=RegistrationRead)
async def update_registration(
    registration_id: int,
    registration: RegistrationUpdate,
    session: AsyncSession = Depends(get_session),
    registration_service: RegistrationService = Depends(get_registration_service),
) -> RegistrationRead:
    """Update an existing registration"""
    try:
        updated_registration = await registration_service.update_registration(
            session, registration_id, registration
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        ) from e

    if not updated_registration:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Registration with id {registration_id} not found",
        )
    return RegistrationRead.model_validate(updated_registration)

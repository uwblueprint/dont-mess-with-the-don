from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies.services import get_user_service
from app.models import get_session
from app.models.user import UserCreate, UserRead, UserUpdate
from app.services.implementations.user_service import UserService

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/", response_model=list[UserRead])
async def get_users(
    session: AsyncSession = Depends(get_session),
    user_service: UserService = Depends(get_user_service),
) -> list[UserRead]:
    try:
        users = await user_service.get_users(session)
        return [UserRead.model_validate(user) for user in users]
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred",
        ) from e


@router.get("/{user_id}", response_model=UserRead)
async def get_user(
    user_id: int,
    session: AsyncSession = Depends(get_session),
    user_service: UserService = Depends(get_user_service),
) -> UserRead:
    try:
        user = await user_service.get_user(session, user_id)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred",
        ) from e
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with id {user_id} not found",
        )
    return UserRead.model_validate(user)


@router.get("/{user_id}/children", response_model=list[UserRead])
async def get_user_children(
    user_id: int,
    session: AsyncSession = Depends(get_session),
    user_service: UserService = Depends(get_user_service),
) -> list[UserRead]:
    try:
        children = await user_service.get_user_children(session, user_id)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred",
        ) from e
    if children is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with id {user_id} not found",
        )
    return [UserRead.model_validate(child) for child in children]


@router.post("/", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def create_user(
    user: UserCreate,
    session: AsyncSession = Depends(get_session),
    user_service: UserService = Depends(get_user_service),
) -> UserRead:
    try:
        created_user = await user_service.create_user(session, user)
        return UserRead.model_validate(created_user)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred",
        ) from e


@router.patch("/{user_id}", response_model=UserRead)
async def update_user(
    user_id: int,
    user: UserUpdate,
    session: AsyncSession = Depends(get_session),
    user_service: UserService = Depends(get_user_service),
) -> UserRead:
    try:
        updated_user = await user_service.update_user(session, user_id, user)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred",
        ) from e
    if not updated_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with id {user_id} not found",
        )
    return UserRead.model_validate(updated_user)


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: int,
    session: AsyncSession = Depends(get_session),
    user_service: UserService = Depends(get_user_service),
) -> None:
    try:
        success = await user_service.delete_user(session, user_id)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred",
        ) from e
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with id {user_id} not found",
        )

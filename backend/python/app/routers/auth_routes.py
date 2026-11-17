from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies.auth import get_current_user, get_token_claims
from app.dependencies.services import get_user_service
from app.models import get_session
from app.models.user import User, UserRead, UserRegister, UserSelfUpdate, UserUpdate
from app.services.implementations.user_service import UserService

# Must be included before user_routes, or GET /users/me matches /users/{user_id}
router = APIRouter(tags=["auth"])


@router.post("/auth/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def register(
    user: UserRegister,
    claims: dict[str, Any] = Depends(get_token_claims),
    session: AsyncSession = Depends(get_session),
    user_service: UserService = Depends(get_user_service),
) -> UserRead:
    """Create the logged-in Firebase account's profile, once, right after sign-up"""
    email = claims.get("email")
    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This sign-in account has no email address",
        )
    try:
        created_user = await user_service.register_user(session, claims["uid"], email, user)
        return UserRead.model_validate(created_user)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred",
        ) from e


@router.get("/users/me", response_model=UserRead)
async def get_me(current_user: User = Depends(get_current_user)) -> UserRead:
    return UserRead.model_validate(current_user)


@router.patch("/users/me", response_model=UserRead)
async def update_me(
    user: UserSelfUpdate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
    user_service: UserService = Depends(get_user_service),
) -> UserRead:
    assert current_user.id is not None
    try:
        updated_user = await user_service.update_user(
            session, current_user.id, UserUpdate(**user.model_dump(exclude_unset=True))
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred",
        ) from e
    return UserRead.model_validate(updated_user)

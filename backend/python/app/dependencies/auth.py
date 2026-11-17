from functools import lru_cache
from typing import Any

import firebase_admin
from fastapi import Depends, HTTPException, status
from fastapi.concurrency import run_in_threadpool
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from firebase_admin import auth as firebase_auth
from google.auth.credentials import AnonymousCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.dependencies.services import get_user_service
from app.models import get_session
from app.models.enum import UserRole
from app.models.user import User
from app.services.implementations.user_service import UserService

# auto_error=False so a missing token reaches get_token_claims and gets its 401
bearer_scheme = HTTPBearer(auto_error=False)


@lru_cache
def get_firebase_app() -> firebase_admin.App:
    """Firebase app used only to check ID tokens.

    Checking a token only needs Google's public keys, so no service-account key is
    used. AnonymousCredentials stops the SDK from looking for Google Cloud credentials.
    """
    return firebase_admin.initialize_app(
        AnonymousCredentials(), options={"projectId": settings.firebase_project_id}
    )


async def get_token_claims(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> dict[str, Any]:
    """Check the Firebase ID token in the Authorization header and return its claims"""
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        # verify_id_token is blocking (it may fetch Google's public keys)
        claims: dict[str, Any] = await run_in_threadpool(
            firebase_auth.verify_id_token, credentials.credentials, app=get_firebase_app()
        )
    except (ValueError, firebase_auth.InvalidIdTokenError) as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from e
    return claims


async def get_current_user(
    claims: dict[str, Any] = Depends(get_token_claims),
    session: AsyncSession = Depends(get_session),
    user_service: UserService = Depends(get_user_service),
) -> User:
    """The logged-in user's profile. 403 if they haven't called POST /auth/register yet"""
    user = await user_service.get_user_by_firebase_uid(session, claims["uid"])
    if not user:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No profile for this account yet, call POST /auth/register first",
        )
    return user


async def require_admin(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return current_user


async def ensure_can_act_for(session: AsyncSession, current_user: User, user_id: int) -> None:
    """403 unless current_user is an admin, is user_id, or is user_id's guardian"""
    if current_user.role == UserRole.ADMIN or current_user.id == user_id:
        return
    user = await session.get(User, user_id)
    if user is None or user.guardian_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only do this for yourself or your children",
        )

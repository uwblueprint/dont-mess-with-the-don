from types import SimpleNamespace

import pytest
from fastapi import HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials

from app.dependencies import auth
from app.models.user import User

TOKEN = HTTPAuthorizationCredentials(scheme="Bearer", credentials="token")
USER = User(id=1, email="u@example.com")


class FakeUserService:
    async def get_user_by_firebase_uid(self, session, uid):
        return USER if uid == "uid-1" else None


def claims_raising(code):
    async def fake(credentials):
        raise HTTPException(status_code=code, detail="nope")

    return fake


async def test_no_token_is_anonymous():
    assert await auth.get_optional_user(None, SimpleNamespace(), FakeUserService()) is None


async def test_invalid_or_expired_token_is_anonymous(monkeypatch):
    monkeypatch.setattr(auth, "get_token_claims", claims_raising(status.HTTP_401_UNAUTHORIZED))
    assert await auth.get_optional_user(TOKEN, SimpleNamespace(), FakeUserService()) is None


async def test_other_errors_are_not_swallowed(monkeypatch):
    monkeypatch.setattr(auth, "get_token_claims", claims_raising(500))
    with pytest.raises(HTTPException):
        await auth.get_optional_user(TOKEN, SimpleNamespace(), FakeUserService())


async def test_valid_token_returns_profile(monkeypatch):
    async def fake(credentials):
        return {"uid": "uid-1"}

    monkeypatch.setattr(auth, "get_token_claims", fake)
    assert await auth.get_optional_user(TOKEN, SimpleNamespace(), FakeUserService()) is USER

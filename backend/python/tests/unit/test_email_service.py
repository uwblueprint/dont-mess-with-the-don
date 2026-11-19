import json
import logging
from typing import Any

import httpx
import pytest

from app.config import Settings
from app.dependencies.services import build_email_service
from app.services.implementations.email_service import RESEND_API_URL, ResendEmailService
from app.services.implementations.logging_email_service import LoggingEmailService
from app.services.interfaces.email_service import EmailSendError

LOGGER = logging.getLogger("test")
SENDER = "Don't Mess With The Don <noreply@example.org>"


def resend_service(handler) -> ResendEmailService:
    """A ResendEmailService whose HTTP calls go to `handler` instead of the network"""
    return ResendEmailService(LOGGER, "re_test_key", SENDER, transport=httpx.MockTransport(handler))


async def test_send_email_posts_to_resend_and_returns_the_id():
    seen: dict[str, Any] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        seen["auth"] = request.headers["Authorization"]
        seen["idempotency"] = request.headers.get("Idempotency-Key")
        seen["body"] = json.loads(request.content)
        return httpx.Response(200, json={"id": "email-123"})

    email_id = await resend_service(handler).send_email(
        "sam@example.com",
        "See you Saturday",
        "<p>Bring water</p>",
        text="Bring water",
        idempotency_key="reminder/42",
    )

    assert email_id == "email-123"
    assert seen["url"] == RESEND_API_URL
    assert seen["auth"] == "Bearer re_test_key"
    assert seen["idempotency"] == "reminder/42"
    assert seen["body"] == {
        "from": SENDER,
        "to": ["sam@example.com"],
        "subject": "See you Saturday",
        "html": "<p>Bring water</p>",
        "text": "Bring water",
    }


async def test_send_email_to_several_people_without_optional_fields():
    seen: dict[str, Any] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["idempotency"] = request.headers.get("Idempotency-Key")
        seen["body"] = json.loads(request.content)
        return httpx.Response(200, json={"id": "email-456"})

    await resend_service(handler).send_email(["a@example.com", "b@example.com"], "Hi", "<p>Hi</p>")

    assert seen["body"]["to"] == ["a@example.com", "b@example.com"]
    assert "text" not in seen["body"]
    assert seen["idempotency"] is None


@pytest.mark.parametrize("status_code", [403, 422, 429, 500])
async def test_send_email_raises_with_resends_status_and_message(status_code):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status_code, json={"name": "error", "message": "nope"})

    with pytest.raises(EmailSendError, match="nope") as excinfo:
        await resend_service(handler).send_email("sam@example.com", "Hi", "<p>Hi</p>")

    assert excinfo.value.status_code == status_code


async def test_send_email_raises_when_resend_cant_be_reached():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused")

    with pytest.raises(EmailSendError, match="Could not reach Resend") as excinfo:
        await resend_service(handler).send_email("sam@example.com", "Hi", "<p>Hi</p>")

    assert excinfo.value.status_code is None


@pytest.mark.parametrize(("api_key", "sender"), [("", SENDER), ("re_test_key", "")])
def test_resend_service_needs_a_key_and_a_sender(api_key, sender):
    with pytest.raises(ValueError):
        ResendEmailService(LOGGER, api_key, sender)


async def test_logging_service_records_instead_of_sending():
    service = LoggingEmailService(LOGGER)

    email_id = await service.send_email("sam@example.com", "Hi", "<p>Hi</p>")

    assert email_id.startswith("not-sent-")
    assert service.sent == [
        {
            "id": email_id,
            "to": ["sam@example.com"],
            "subject": "Hi",
            "html": "<p>Hi</p>",
            "text": None,
            "idempotency_key": None,
        }
    ]


def make_settings(app_env: str, **email: str) -> Settings:
    # _env_file=None so a developer's local .env never leaks into these tests
    values: dict[str, Any] = {"_env_file": None, "app_env": app_env, **email}
    return Settings(**values)


@pytest.mark.parametrize("app_env", ["development", "testing"])
def test_no_api_key_outside_production_logs_emails(app_env):
    service = build_email_service(LOGGER, make_settings(app_env))
    assert isinstance(service, LoggingEmailService)


def test_api_key_gives_resend():
    service = build_email_service(
        LOGGER, make_settings("development", resend_api_key="re_test_key", email_from=SENDER)
    )
    assert isinstance(service, ResendEmailService)


@pytest.mark.parametrize(
    "email",
    [{}, {"resend_api_key": "re_test_key"}, {"email_from": SENDER}],
)
def test_production_needs_resend_fully_configured(email):
    with pytest.raises(ValueError):
        build_email_service(LOGGER, make_settings("production", **email))

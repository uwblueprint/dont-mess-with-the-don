import logging
from typing import Any

import httpx

from ..interfaces.email_service import EmailSendError, IEmailService

RESEND_API_URL = "https://api.resend.com/emails"


class ResendEmailService(IEmailService):
    """
    EmailService implementation that sends through Resend's REST API
    """

    def __init__(
        self,
        logger: logging.Logger,
        api_key: str,
        sender: str,
        *,
        transport: httpx.AsyncBaseTransport | None = None,
        timeout_seconds: float = 10.0,
    ):
        """
        Create an instance of ResendEmailService

        :param logger: application's logger instance
        :param api_key: Resend API key (RESEND_API_KEY)
        :param sender: the "from" address, e.g. "Don't Mess With The Don <noreply@example.org>"
            (EMAIL_FROM). Its domain must be verified in Resend.
        :param transport: httpx transport to use instead of the network (tests)
        :param timeout_seconds: how long to wait for Resend before giving up
        :raises ValueError: if the API key or sender is missing
        """
        if not api_key:
            raise ValueError("RESEND_API_KEY is not configured")
        if not sender:
            raise ValueError("EMAIL_FROM is not configured")
        self.logger = logger
        self.api_key = api_key
        self.sender = sender
        self.transport = transport
        self.timeout_seconds = timeout_seconds

    async def send_email(
        self,
        to: str | list[str],
        subject: str,
        html: str,
        *,
        text: str | None = None,
        idempotency_key: str | None = None,
    ) -> str:
        payload: dict[str, Any] = {
            "from": self.sender,
            "to": [to] if isinstance(to, str) else list(to),
            "subject": subject,
            "html": html,
        }
        if text is not None:
            payload["text"] = text
        headers = {"Authorization": f"Bearer {self.api_key}"}
        if idempotency_key:
            headers["Idempotency-Key"] = idempotency_key

        try:
            async with httpx.AsyncClient(
                transport=self.transport, timeout=self.timeout_seconds
            ) as client:
                response = await client.post(RESEND_API_URL, json=payload, headers=headers)
        except httpx.HTTPError as e:
            self.logger.error(f"Failed to reach Resend for email {subject!r}: {e}")
            raise EmailSendError(f"Could not reach Resend: {e}") from e

        if response.is_success:
            return str(response.json()["id"])

        # Recipients aren't logged: they're personal data
        reason = _error_message(response)
        self.logger.error(f"Resend rejected email {subject!r}: {response.status_code} {reason}")
        raise EmailSendError(
            f"Resend returned {response.status_code}: {reason}", status_code=response.status_code
        )


def _error_message(response: httpx.Response) -> str:
    """Resend errors are JSON with a message; fall back to the raw body."""
    try:
        body = response.json()
    except ValueError:
        return response.text
    if isinstance(body, dict) and body.get("message"):
        return str(body["message"])
    return response.text

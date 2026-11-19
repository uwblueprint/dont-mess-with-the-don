import logging
from typing import Any
from uuid import uuid4

from ..interfaces.email_service import IEmailService


class LoggingEmailService(IEmailService):
    """
    Stand-in used in development and testing when RESEND_API_KEY isn't set: emails are
    logged instead of sent, so features that send email still work locally. Never used
    in production.
    """

    def __init__(self, logger: logging.Logger):
        self.logger = logger
        # Everything "sent", newest last, so tests can check what would have gone out
        self.sent: list[dict[str, Any]] = []

    async def send_email(
        self,
        to: str | list[str],
        subject: str,
        html: str,
        *,
        text: str | None = None,
        idempotency_key: str | None = None,
    ) -> str:
        email_id = f"not-sent-{uuid4()}"
        recipients = [to] if isinstance(to, str) else list(to)
        self.sent.append(
            {
                "id": email_id,
                "to": recipients,
                "subject": subject,
                "html": html,
                "text": text,
                "idempotency_key": idempotency_key,
            }
        )
        self.logger.info(f"Email not sent (Resend isn't configured): to={recipients} {subject!r}")
        return email_id

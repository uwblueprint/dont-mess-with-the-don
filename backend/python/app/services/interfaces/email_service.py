from abc import ABC, abstractmethod


class EmailSendError(Exception):
    """An email wasn't sent. status_code is the provider's HTTP status, if it answered."""

    def __init__(self, message: str, status_code: int | None = None):
        super().__init__(message)
        self.status_code = status_code


class IEmailService(ABC):
    """
    EmailService interface for sending emails (confirmations, reminders, strike notices)
    """

    @abstractmethod
    async def send_email(
        self,
        to: str | list[str],
        subject: str,
        html: str,
        *,
        text: str | None = None,
        idempotency_key: str | None = None,
    ) -> str:
        """
        Sends one email

        :param to: recipient address, or a list of addresses
        :param subject: subject line
        :param html: body as HTML
        :param text: plain-text body, defaults to None
        :param idempotency_key: sending again with the same key within 24 hours doesn't
            send a second email, so a retried job can't double-send. Defaults to None
        :return: the provider's id for the sent email
        :raises EmailSendError: if the email wasn't sent
        """
        pass

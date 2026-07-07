from abc import ABC, abstractmethod
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.form_submission import (
    FormSubmission,
    FormSubmissionCreate,
    FormSubmissionUpdate,
)


class IFormSubmissionService(ABC):
    """Interface to handle registration form submissions"""

    @abstractmethod
    async def get_form_submissions(
        self,
        session: AsyncSession,
        user_id: int | None = None,
        event_instance_id: UUID | None = None,
    ) -> list[FormSubmission]:
        pass

    @abstractmethod
    async def get_form_submission(
        self, session: AsyncSession, submission_id: int
    ) -> FormSubmission | None:
        pass

    @abstractmethod
    async def submit_form(
        self, session: AsyncSession, submission_data: FormSubmissionCreate
    ) -> tuple[FormSubmission, bool]:
        """Create or update the user's submission for an event.

        Returns the submission and whether it was newly created.
        """
        pass

    @abstractmethod
    async def update_form_submission(
        self,
        session: AsyncSession,
        submission_id: int,
        submission_data: FormSubmissionUpdate,
    ) -> FormSubmission | None:
        pass

    @abstractmethod
    async def delete_form_submission(self, session: AsyncSession, submission_id: int) -> bool:
        pass

import logging
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.models.event import Event
from app.models.event_type import EventType
from app.models.form import FormDefinition
from app.models.form_submission import (
    FormSubmission,
    FormSubmissionCreate,
    FormSubmissionUpdate,
)
from app.utilities.form_validation import validate_form_response


class FormSubmissionService:
    """Service for managing form submissions"""

    def __init__(self, logger: logging.Logger):
        self.logger = logger

    async def get_form_submissions(
        self,
        session: AsyncSession,
        user_id: int | None = None,
        event_instance_id: UUID | None = None,
    ) -> list[FormSubmission]:
        """Get all form submissions"""
        statement = select(FormSubmission)

        if user_id is not None:
            statement = statement.where(FormSubmission.user_id == user_id)
        if event_instance_id is not None:
            statement = statement.where(FormSubmission.event_instance_id == event_instance_id)

        result = await session.execute(statement)
        return list(result.scalars().all())

    async def get_form_submission(
        self, session: AsyncSession, submission_id: int
    ) -> FormSubmission | None:
        """Get form submission by ID"""
        statement = select(FormSubmission).where(FormSubmission.id == submission_id)
        result = await session.execute(statement)
        form_submission = result.scalars().first()

        if not form_submission:
            self.logger.error(f"FormSubmission with id {submission_id} not found")
            return None

        return form_submission

    async def _get_form_definition(
        self, session: AsyncSession, event_id: UUID
    ) -> FormDefinition | None:
        """Get the form an event's submissions answer, or None if it has no form.

        An event's own form_json overrides its event type's.
        """
        event = await session.get(Event, event_id)
        if event is None:
            return None

        form_json = event.form_json
        if not form_json and event.event_type_id is not None:
            event_type = await session.get(EventType, event.event_type_id)
            form_json = event_type.form_json if event_type else None
        if not form_json:
            return None

        try:
            return FormDefinition.model_validate(form_json)
        except ValueError as error:
            # A stored form that does not parse is bad data on our side, not a
            # problem with the response, so it must not surface as a ValueError
            raise RuntimeError(f"Event {event_id} has an invalid form definition") from error

    async def _validate_response(
        self, session: AsyncSession, event_id: UUID, response_json: dict | None
    ) -> None:
        """Check a response against the event's form; raises ValueError on mismatch.

        Nothing is checked when the event does not exist or has no form.
        """
        definition = await self._get_form_definition(session, event_id)
        if definition is None:
            return
        if not response_json:
            raise ValueError("A response is required for this event's form")
        validate_form_response(definition, response_json)

    async def create_form_submission(
        self, session: AsyncSession, form_submission_data: FormSubmissionCreate
    ) -> FormSubmission:
        """Create new form submission; raises ValueError if the response does not
        match the event's form"""
        await self._validate_response(
            session, form_submission_data.event_instance_id, form_submission_data.response_json
        )
        try:
            form_submission = FormSubmission(**form_submission_data.model_dump())
            session.add(form_submission)
            await session.commit()
            await session.refresh(form_submission)
            return form_submission
        except Exception as error:
            self.logger.error(f"Failed to create form submission: {error!s}")
            await session.rollback()
            raise error

    async def delete_form_submission(self, session: AsyncSession, form_submission_id: int) -> bool:
        """Delete form submission by ID"""
        try:
            statement = select(FormSubmission).where(FormSubmission.id == form_submission_id)
            result = await session.execute(statement)
            form_submission = result.scalars().first()

            if not form_submission:
                self.logger.error(f"Entity {form_submission} not found")
                return False

            await session.delete(form_submission)
            await session.commit()
            return True
        except Exception as error:
            self.logger.error(f"Failed to delete entity: {error!s}")
            await session.rollback()
            raise error

    async def update_form_submission(
        self,
        session: AsyncSession,
        form_submission_id: int,
        form_submission_data: FormSubmissionUpdate,
    ) -> FormSubmission | None:
        """Update form submission by ID; raises ValueError if the new response does
        not match the event's form"""
        form_submission = await self.get_form_submission(session, form_submission_id)
        if not form_submission:
            return None

        updates = form_submission_data.model_dump(exclude_unset=True)
        if "response_json" in updates:
            await self._validate_response(
                session, form_submission.event_instance_id, updates["response_json"]
            )
        try:
            for key, value in updates.items():
                setattr(form_submission, key, value)

            await session.commit()
            await session.refresh(form_submission)
            return form_submission
        except Exception as error:
            self.logger.error(f"Failed to update form submission: {error!s}")
            await session.rollback()
            raise error

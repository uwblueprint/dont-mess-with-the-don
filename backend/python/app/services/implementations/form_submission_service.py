import logging
from datetime import datetime
from uuid import UUID
from zoneinfo import ZoneInfo

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.models.event import Event
from app.models.event_type import EventType
from app.models.form import FormDefinition, validate_form_response
from app.models.form_submission import (
    FormSubmission,
    FormSubmissionCreate,
    FormSubmissionUpdate,
)
from app.models.registration import Registration
from app.services.interfaces.form_submission_service import IFormSubmissionService


class FormSubmissionService(IFormSubmissionService):
    """Service for managing registration form submissions"""

    def __init__(self, logger: logging.Logger):
        self.logger = logger

    async def get_form_submissions(
        self,
        session: AsyncSession,
        user_id: int | None = None,
        event_instance_id: UUID | None = None,
    ) -> list[FormSubmission]:
        """Get all form submissions, optionally filtered"""
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
        submission = result.scalars().first()

        if not submission:
            self.logger.warning(f"Form submission with id {submission_id} not found")
            return None

        return submission

    async def _resolve_form_definition(
        self, session: AsyncSession, event_instance_id: UUID
    ) -> FormDefinition:
        """Get the form for an event: its own form_json, else its event type's template.

        Raises LookupError if the event does not exist and ValueError if
        neither the event nor its event type defines a form.
        """
        statement = select(Event).where(Event.id == event_instance_id)
        result = await session.execute(statement)
        event = result.scalars().first()
        if not event:
            raise LookupError(f"Event with id {event_instance_id} not found")

        form_json = event.form_json
        if not form_json and event.event_type is not None:
            type_statement = select(EventType).where(EventType.id == event.event_type)
            type_result = await session.execute(type_statement)
            event_type = type_result.scalars().first()
            if event_type:
                form_json = event_type.form_json

        if not form_json:
            raise ValueError(f"Event with id {event_instance_id} does not have a registration form")
        return FormDefinition.model_validate(form_json)

    async def submit_form(
        self, session: AsyncSession, submission_data: FormSubmissionCreate
    ) -> tuple[FormSubmission, bool]:
        """Create or update the user's submission for an event"""
        try:
            if not submission_data.response_json:
                raise ValueError("response_json is required")

            definition = await self._resolve_form_definition(
                session, submission_data.event_instance_id
            )
            response = validate_form_response(definition, submission_data.response_json)

            statement = select(FormSubmission).where(
                FormSubmission.user_id == submission_data.user_id,
                FormSubmission.event_instance_id == submission_data.event_instance_id,
            )
            result = await session.execute(statement)
            submission = result.scalars().first()
            created = submission is None

            if submission:
                previous_version = (submission.response_json or {}).get("responseVersion", 0)
                response.response_version = previous_version + 1
                submission.response_json = response.model_dump(mode="json", by_alias=True)
                submission.updated_at = datetime.now(ZoneInfo("America/Toronto")).replace(
                    tzinfo=None
                )
            else:
                response.response_version = 1
                submission = FormSubmission(
                    user_id=submission_data.user_id,
                    event_instance_id=submission_data.event_instance_id,
                    response_json=response.model_dump(mode="json", by_alias=True),
                )
                session.add(submission)

            await session.flush()

            # Link the submission to the user's registration for this event, if any
            registration_statement = select(Registration).where(
                Registration.user_id == submission_data.user_id,
                Registration.event_instance_id == submission_data.event_instance_id,
            )
            registration_result = await session.execute(registration_statement)
            registration = registration_result.scalars().first()
            if registration and registration.response_id != submission.id:
                registration.response_id = submission.id

            await session.commit()
            await session.refresh(submission)
            return submission, created
        except (LookupError, ValueError):
            await session.rollback()
            raise
        except Exception as error:
            self.logger.error(f"Failed to submit form: {error!s}")
            await session.rollback()
            raise error

    async def update_form_submission(
        self,
        session: AsyncSession,
        submission_id: int,
        submission_data: FormSubmissionUpdate,
    ) -> FormSubmission | None:
        """Update an existing form submission's response"""
        try:
            statement = select(FormSubmission).where(FormSubmission.id == submission_id)
            result = await session.execute(statement)
            submission = result.scalars().first()

            if not submission:
                self.logger.warning(f"Form submission with id {submission_id} not found")
                return None

            if submission_data.response_json is not None:
                definition = await self._resolve_form_definition(
                    session, submission.event_instance_id
                )
                response = validate_form_response(definition, submission_data.response_json)
                previous_version = (submission.response_json or {}).get("responseVersion", 0)
                response.response_version = previous_version + 1
                submission.response_json = response.model_dump(mode="json", by_alias=True)

            submission.updated_at = datetime.now(ZoneInfo("America/Toronto")).replace(tzinfo=None)

            await session.commit()
            await session.refresh(submission)
            return submission
        except (LookupError, ValueError):
            await session.rollback()
            raise
        except Exception as error:
            self.logger.error(f"Failed to update form submission: {error!s}")
            await session.rollback()
            raise error

    async def delete_form_submission(self, session: AsyncSession, submission_id: int) -> bool:
        """Delete form submission by ID"""
        try:
            statement = select(FormSubmission).where(FormSubmission.id == submission_id)
            result = await session.execute(statement)
            submission = result.scalars().first()

            if not submission:
                self.logger.warning(f"Form submission with id {submission_id} not found")
                return False

            # Unlink any registrations pointing at this submission before deleting
            registration_statement = select(Registration).where(
                Registration.response_id == submission_id
            )
            registration_result = await session.execute(registration_statement)
            for registration in registration_result.scalars().all():
                registration.response_id = None

            await session.delete(submission)
            await session.commit()
            return True
        except Exception as error:
            self.logger.error(f"Failed to delete form submission: {error!s}")
            await session.rollback()
            raise error

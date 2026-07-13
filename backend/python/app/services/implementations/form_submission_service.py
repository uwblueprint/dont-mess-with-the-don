import logging

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.models.form_submission import FormSubmission, FormSubmissionCreate, FormSubmissionRead, FormSubmissionUpdate

class FormSubmissionService:
    """Service for managing form submissions"""

    def __init__(self, logger: logging.Logger):
        self.logger = logger

    async def get_form_submissions(self, session: AsyncSession, user_id: int | None = None, event_instance_id: int | None = None) -> list[FormSubmission]:
        """Get all form submissions"""
        statement = select(FormSubmission)

        if user_id is not None:
            statement = statement.where(FormSubmission.user_id == user_id)
        if event_instance_id is not None:
            statement = statement.where(FormSubmission.event_instance_id == event_instance_id)
            
        result = await session.execute(statement)
        return list(result.scalars().all())
    
    async def get_form_submission(self, session: AsyncSession, submission_id: int) -> FormSubmission | None:
        """Get form submission by ID"""
        statement = select(FormSubmission).where(FormSubmission.id == submission_id)
        result = await session.execute(statement)
        form_submission = result.scalars().first()

        if not form_submission:
            self.logger.error(f"FormSubmission with id {submission_id} not found")
            return None

        return form_submission

    async def create_form_submission(self, session: AsyncSession, form_submission_data: FormSubmissionCreate) -> FormSubmission:
        """Create new form submission"""
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

    async def update_form_submission(self, session: AsyncSession, form_submission_id: int, form_submission_data: FormSubmissionUpdate) -> FormSubmission | None:
        """Update form submission by ID"""
        try:
            form_submission = await self.get_form_submission(session, form_submission_id)
            if not form_submission:
                self.logger.error(f"FormSubmission with id {form_submission_id} not found")
                return None

            for key, value in form_submission_data.model_dump().items():
                setattr(form_submission, key, value)

            await session.commit()
            await session.refresh(form_submission)
            return form_submission
        except Exception as error:
            self.logger.error(f"Failed to update form submission: {error!s}")
            await session.rollback()
            raise error

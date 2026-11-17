import logging
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.models.form_template import FormTemplate, FormTemplateCreate, FormTemplateUpdate


class FormTemplateService:
    """Service for managing reusable form templates"""

    def __init__(self, logger: logging.Logger):
        self.logger = logger

    async def get_form_templates(self, session: AsyncSession) -> list[FormTemplate]:
        """Get all form templates"""
        result = await session.execute(select(FormTemplate))
        return list(result.scalars().all())

    async def get_form_template(
        self, session: AsyncSession, form_template_id: UUID
    ) -> FormTemplate | None:
        """Get form template by ID"""
        form_template = await session.get(FormTemplate, form_template_id)
        if not form_template:
            self.logger.error(f"Form template with id {form_template_id} not found")
            return None
        return form_template

    async def create_form_template(
        self, session: AsyncSession, form_template_data: FormTemplateCreate
    ) -> FormTemplate:
        """Create new form template"""
        try:
            form_template = FormTemplate(**form_template_data.model_dump())
            session.add(form_template)
            await session.commit()
            await session.refresh(form_template)
            return form_template
        except Exception as error:
            self.logger.error(f"Failed to create form template: {error!s}")
            await session.rollback()
            raise error

    async def update_form_template(
        self,
        session: AsyncSession,
        form_template_id: UUID,
        form_template_data: FormTemplateUpdate,
    ) -> FormTemplate | None:
        """Update form template by ID"""
        try:
            form_template = await self.get_form_template(session, form_template_id)
            if not form_template:
                return None

            update_data = form_template_data.model_dump(exclude_unset=True, exclude_none=True)
            for field, value in update_data.items():
                setattr(form_template, field, value)

            await session.commit()
            await session.refresh(form_template)
            return form_template
        except Exception as error:
            self.logger.error(f"Failed to update form template: {error!s}")
            await session.rollback()
            raise error

    async def delete_form_template(self, session: AsyncSession, form_template_id: UUID) -> bool:
        """Delete form template by ID; raises ValueError if submissions still use it"""
        try:
            form_template = await self.get_form_template(session, form_template_id)
            if not form_template:
                return False

            await session.delete(form_template)
            await session.commit()
            return True
        except IntegrityError as error:
            await session.rollback()
            self.logger.warning(f"Form template {form_template_id} still has submissions")
            raise ValueError(
                f"Form template {form_template_id} has submissions and cannot be deleted"
            ) from error
        except Exception as error:
            self.logger.error(f"Failed to delete form template: {error!s}")
            await session.rollback()
            raise error

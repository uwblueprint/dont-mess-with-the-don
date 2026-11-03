from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies.services import get_form_template_service
from app.models import get_session
from app.models.form_template import FormTemplateCreate, FormTemplateRead, FormTemplateUpdate
from app.services.implementations.form_template_service import FormTemplateService

router = APIRouter(prefix="/forms", tags=["forms"])


@router.get("/", response_model=list[FormTemplateRead])
async def get_form_templates(
    session: AsyncSession = Depends(get_session),
    form_template_service: FormTemplateService = Depends(get_form_template_service),
) -> list[FormTemplateRead]:
    """Retrieve all form templates"""
    form_templates = await form_template_service.get_form_templates(session)
    return [FormTemplateRead.model_validate(form_template) for form_template in form_templates]


@router.get("/{form_template_id}", response_model=FormTemplateRead)
async def get_form_template(
    form_template_id: UUID,
    session: AsyncSession = Depends(get_session),
    form_template_service: FormTemplateService = Depends(get_form_template_service),
) -> FormTemplateRead:
    """Get a single form template by ID"""
    form_template = await form_template_service.get_form_template(session, form_template_id)
    if not form_template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Form with id {form_template_id} not found",
        )
    return FormTemplateRead.model_validate(form_template)


@router.post("/", response_model=FormTemplateRead, status_code=status.HTTP_201_CREATED)
async def create_form_template(
    form_template: FormTemplateCreate,
    session: AsyncSession = Depends(get_session),
    form_template_service: FormTemplateService = Depends(get_form_template_service),
) -> FormTemplateRead:
    """Create a new form template"""
    try:
        created = await form_template_service.create_form_template(session, form_template)
        return FormTemplateRead.model_validate(created)
    except Exception as error:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create form",
        ) from error


@router.patch("/{form_template_id}", response_model=FormTemplateRead)
async def update_form_template(
    form_template_id: UUID,
    form_template: FormTemplateUpdate,
    session: AsyncSession = Depends(get_session),
    form_template_service: FormTemplateService = Depends(get_form_template_service),
) -> FormTemplateRead:
    """Update an existing form template"""
    try:
        updated = await form_template_service.update_form_template(
            session, form_template_id, form_template
        )
    except Exception as error:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update form",
        ) from error
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Form with id {form_template_id} not found",
        )
    return FormTemplateRead.model_validate(updated)


@router.delete("/{form_template_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_form_template(
    form_template_id: UUID,
    session: AsyncSession = Depends(get_session),
    form_template_service: FormTemplateService = Depends(get_form_template_service),
) -> None:
    """Delete a form template by ID; fails with 409 while submissions use it"""
    try:
        deleted = await form_template_service.delete_form_template(session, form_template_id)
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error
    except Exception as error:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete form",
        ) from error
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Form with id {form_template_id} not found",
        )

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies.auth import ensure_can_act_for, get_current_user, require_admin
from app.dependencies.services import get_form_submission_service
from app.models import get_session
from app.models.form_submission import (
    FormSubmissionCreate,
    FormSubmissionRead,
    FormSubmissionUpdate,
)
from app.models.user import User
from app.services.implementations.form_submission_service import FormSubmissionService

router = APIRouter(prefix="/form_submissions", tags=["form_submissions"])


@router.get("/", response_model=list[FormSubmissionRead], dependencies=[Depends(require_admin)])
async def get_form_submissions(
    user_id: int | None = None,
    event_instance_id: UUID | None = None,
    form_id: UUID | None = None,
    session: AsyncSession = Depends(get_session),
    form_submission_service: FormSubmissionService = Depends(get_form_submission_service),
) -> list[FormSubmissionRead]:
    """Retrieve all form submissions"""
    try:
        form_submissions = await form_submission_service.get_form_submissions(
            session, user_id=user_id, event_instance_id=event_instance_id, form_id=form_id
        )

        return [FormSubmissionRead.model_validate(submission) for submission in form_submissions]
    except Exception as error:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred",
        ) from error


@router.get(
    "/{form_submission_id}",
    response_model=FormSubmissionRead,
    dependencies=[Depends(require_admin)],
)
async def get_form_submission(
    form_submission_id: int,
    session: AsyncSession = Depends(get_session),
    form_submission_service: FormSubmissionService = Depends(get_form_submission_service),
) -> FormSubmissionRead:
    """Get a single form submission by ID"""
    try:
        form_submission = await form_submission_service.get_form_submission(
            session, form_submission_id
        )
        if not form_submission:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"FormSubmission with id {form_submission_id} not found",
            )
        return FormSubmissionRead.model_validate(form_submission)
    except HTTPException:
        raise
    except Exception as error:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred",
        ) from error


@router.post("/", response_model=FormSubmissionRead, status_code=status.HTTP_201_CREATED)
async def create_form_submission(
    form_submission: FormSubmissionCreate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
    form_submission_service: FormSubmissionService = Depends(get_form_submission_service),
) -> FormSubmissionRead:
    """Create a new form submission for yourself or your child (admins: for anyone)"""
    await ensure_can_act_for(session, current_user, form_submission.user_id)
    try:
        created_form_submission = await form_submission_service.create_form_submission(
            session, form_submission
        )
        return FormSubmissionRead.model_validate(created_form_submission)
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(error),
        ) from error
    except Exception as error:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred",
        ) from error


@router.delete(
    "/{form_submission_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_admin)],
)
async def delete_form_submission(
    form_submission_id: int,
    session: AsyncSession = Depends(get_session),
    form_submission_service: FormSubmissionService = Depends(get_form_submission_service),
) -> None:
    """Delete a form submission by ID"""
    try:
        success = await form_submission_service.delete_form_submission(session, form_submission_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"FormSubmission with id {form_submission_id} not found",
            )
    except HTTPException:
        raise
    except Exception as error:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred",
        ) from error


@router.patch(
    "/{form_submission_id}",
    response_model=FormSubmissionRead,
    dependencies=[Depends(require_admin)],
)
async def update_form_submission(
    form_submission_id: int,
    form_submission: FormSubmissionUpdate,
    session: AsyncSession = Depends(get_session),
    form_submission_service: FormSubmissionService = Depends(get_form_submission_service),
) -> FormSubmissionRead:
    """Update an existing form submission"""
    try:
        updated_form_submission = await form_submission_service.update_form_submission(
            session, form_submission_id, form_submission
        )
        if not updated_form_submission:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"FormSubmission with id {form_submission_id} not found",
            )
        return FormSubmissionRead.model_validate(updated_form_submission)
    except HTTPException:
        raise
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(error),
        ) from error
    except Exception as error:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred",
        ) from error

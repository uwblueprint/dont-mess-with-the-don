from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response
from fastapi import status as http_status
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies.services import get_form_submission_service
from app.models import get_session
from app.models.form_submission import (
    FormSubmissionCreate,
    FormSubmissionRead,
    FormSubmissionUpdate,
)
from app.services.implementations.form_submission_service import FormSubmissionService

router = APIRouter(prefix="/form-submissions", tags=["form-submissions"])


@router.get("/", response_model=list[FormSubmissionRead])
async def get_form_submissions(
    user_id: int | None = None,
    event_instance_id: UUID | None = None,
    session: AsyncSession = Depends(get_session),
    form_submission_service: FormSubmissionService = Depends(get_form_submission_service),
) -> list[FormSubmissionRead]:
    """Retrieve all form submissions, optionally filtered
    by user_id and/or event_instance_id
    """
    try:
        submissions = await form_submission_service.get_form_submissions(
            session,
            user_id=user_id,
            event_instance_id=event_instance_id,
        )
        return [FormSubmissionRead.model_validate(submission) for submission in submissions]
    except Exception as e:
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred",
        ) from e


@router.get("/{submission_id}", response_model=FormSubmissionRead)
async def get_form_submission(
    submission_id: int,
    session: AsyncSession = Depends(get_session),
    form_submission_service: FormSubmissionService = Depends(get_form_submission_service),
) -> FormSubmissionRead:
    """Get a single form submission by ID"""
    try:
        submission = await form_submission_service.get_form_submission(session, submission_id)
    except Exception as e:
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred",
        ) from e

    if not submission:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=f"Form submission with id {submission_id} not found",
        )
    return FormSubmissionRead.model_validate(submission)


@router.post("/", response_model=FormSubmissionRead, status_code=http_status.HTTP_201_CREATED)
async def submit_form(
    submission: FormSubmissionCreate,
    response: Response,
    session: AsyncSession = Depends(get_session),
    form_submission_service: FormSubmissionService = Depends(get_form_submission_service),
) -> FormSubmissionRead:
    """Submit a registration form response for an event.

    The response is validated against the event's form (falling back to the
    event type's form template). A user can only respond once per event:
    submitting again edits the existing submission (returns 200 instead of 201).
    """
    try:
        created_submission, created = await form_submission_service.submit_form(session, submission)
    except LookupError as e:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e
    except ValueError as e:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e
    except Exception as e:
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred",
        ) from e

    if not created:
        response.status_code = http_status.HTTP_200_OK
    return FormSubmissionRead.model_validate(created_submission)


@router.patch("/{submission_id}", response_model=FormSubmissionRead)
async def update_form_submission(
    submission_id: int,
    submission: FormSubmissionUpdate,
    session: AsyncSession = Depends(get_session),
    form_submission_service: FormSubmissionService = Depends(get_form_submission_service),
) -> FormSubmissionRead:
    """Update an existing form submission (revalidates the response)"""
    try:
        updated_submission = await form_submission_service.update_form_submission(
            session, submission_id, submission
        )
    except LookupError as e:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e
    except ValueError as e:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e
    except Exception as e:
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred",
        ) from e

    if not updated_submission:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=f"Form submission with id {submission_id} not found",
        )
    return FormSubmissionRead.model_validate(updated_submission)


@router.delete("/{submission_id}", status_code=http_status.HTTP_204_NO_CONTENT)
async def delete_form_submission(
    submission_id: int,
    session: AsyncSession = Depends(get_session),
    form_submission_service: FormSubmissionService = Depends(get_form_submission_service),
) -> None:
    """Delete an existing form submission"""
    try:
        success = await form_submission_service.delete_form_submission(session, submission_id)
    except Exception as e:
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred",
        ) from e

    if not success:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=f"Form submission with id {submission_id} not found",
        )

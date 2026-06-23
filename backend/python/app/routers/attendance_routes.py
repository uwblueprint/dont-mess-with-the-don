from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies.services import get_attendance_service
from app.models import get_session
from app.models.attendance import AttendanceCreate, AttendanceRead
from app.services.implementations.attendance_service import AttendanceService

router = APIRouter(prefix="/attendance", tags=["attendance"])


@router.get("/{attendance_id}", response_model=AttendanceRead)
async def get_attendance(
    attendance_id: int,
    session: AsyncSession = Depends(get_session),
    attendance_service: AttendanceService = Depends(get_attendance_service),
) -> AttendanceRead:
    attendance = await attendance_service.get_attendance(session, attendance_id)

    if not attendance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Attendance with id {attendance_id} not found",
        )

    return AttendanceRead.model_validate(attendance)


@router.get("/", response_model=list[AttendanceRead])
async def get_attendance_list(
    session: AsyncSession = Depends(get_session),
    attendance_service: AttendanceService = Depends(get_attendance_service),
) -> list[AttendanceRead]:
    attendance_records = await attendance_service.get_attendance_list(session)
    return [AttendanceRead.model_validate(attendance) for attendance in attendance_records]


@router.post("/", response_model=AttendanceRead, status_code=status.HTTP_201_CREATED)
async def create_attendance(
    attendance: AttendanceCreate,
    session: AsyncSession = Depends(get_session),
    attendance_service: AttendanceService = Depends(get_attendance_service),
) -> AttendanceRead:
    """Create a new attendance listing"""
    created_attendance = await attendance_service.create_attendance(session, attendance)
    return AttendanceRead.model_validate(created_attendance)


@router.delete("/{attendance_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_attendance(
    attendance_id: int,
    session: AsyncSession = Depends(get_session),
    attendance_service: AttendanceService = Depends(get_attendance_service),
) -> None:
    success = await attendance_service.delete_attendance(session, attendance_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Attendance with id {attendance_id} not found",
        )

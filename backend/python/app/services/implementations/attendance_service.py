import logging

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.models.attendance import Attendance, AttendanceCreate


class AttendanceService:
    def __init__(self, logger: logging.Logger):
        self.logger = logger

    async def create_attendance(
        self, session: AsyncSession, attendance_data: AttendanceCreate
    ) -> Attendance:
        """Create new attendance record"""
        try:
            attendance = Attendance(**attendance_data.model_dump())
            session.add(attendance)
            await session.commit()
            await session.refresh(attendance)
            return attendance
        except Exception as error:
            self.logger.error(f"Failed to create attendance: {error!s}")
            await session.rollback()
            raise

    async def get_attendance(self, session: AsyncSession, attendance_id: int) -> Attendance | None:
        statement = select(Attendance).where(Attendance.id == attendance_id)
        result = await session.execute(statement)
        return result.scalars().first()

    async def get_attendance_list(self, session: AsyncSession) -> list[Attendance]:
        statement = select(Attendance)
        result = await session.execute(statement)
        return list(result.scalars().all())

    async def delete_attendance(self, session: AsyncSession, attendance_id: int) -> bool:
        """Delete attendance by ID"""
        try:
            attendance = await self.get_attendance(session, attendance_id)

            if not attendance:
                self.logger.warning(f"Attendance with id {attendance_id} not found")
                return False

            await session.delete(attendance)
            await session.commit()
            return True
        except Exception as error:
            self.logger.error(f"Failed to delete attendance: {error!s}")
            await session.rollback()
            raise

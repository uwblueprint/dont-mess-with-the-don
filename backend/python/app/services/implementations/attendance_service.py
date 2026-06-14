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
        attendance = Attendance(**attendance_data.model_dump())
        session.add(attendance)
        await session.commit()
        await session.refresh(attendance)
        return attendance

    async def get_attendance(
        self, session: AsyncSession, attendance_id: int
    ) -> Attendance | None:
        statement = select(Attendance).where(Attendance.id == attendance_id)
        result = await session.execute(statement)
        return result.scalars().first()
    
    async def get_attendance_list(
        self, session: AsyncSession
    ) -> list[Attendance]:
        statement = select(Attendance)
        result = await session.execute(statement)
        return list(result.scalars().all())

    async def delete_attendance(
        self, session: AsyncSession, attendance_id: int
    ) -> bool:
        attendance = await self.get_attendance(session, attendance_id)

        if not attendance:
            return False

        await session.delete(attendance)
        await session.commit()
        return True
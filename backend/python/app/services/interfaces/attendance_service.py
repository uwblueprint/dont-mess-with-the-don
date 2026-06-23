from abc import ABC, abstractmethod
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.attendance import Attendance, AttendanceCreate


class IAttendanceService(ABC):
    """
    AttendanceService interface for handling attendance related functionality
    """

    @abstractmethod
    async def create_attendance(
        self, session: AsyncSession, attendance_data: AttendanceCreate
    ) -> Attendance:
        pass

    @abstractmethod
    async def get_attendance(
        self, session: AsyncSession, attendance_id: int
    ) -> Attendance | None:
        pass

    @abstractmethod
    async def get_attendance_list(
        self,
        session: AsyncSession,
        user_id: int | None = None,
        event_instance_id: UUID | None = None,
    ) -> list[Attendance]:
        pass

    @abstractmethod
    async def delete_attendance(
        self, session: AsyncSession, attendance_id: int
    ) -> bool:
        pass
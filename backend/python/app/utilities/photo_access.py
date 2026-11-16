"""Who may see an event's post-event photos (signed URLs).

Photos show identifiable people, often minors, so they go only to admins and to the
event's own attendees: anyone with an accepted registration or a check-in (attendance
row) for that event. A guardian qualifies through any of their children, the same way
`ensure_can_act_for` treats guardians.
"""

from uuid import UUID

from sqlalchemy import or_, union
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import col, select

from app.models.attendance import Attendance
from app.models.enum import RegistrationStatusEnum, UserRole
from app.models.registration import Registration
from app.models.user import User


async def get_event_ids_with_visible_photos(
    session: AsyncSession, user: User | None, event_ids: list[UUID]
) -> set[UUID]:
    """The subset of `event_ids` whose post-event photos `user` may see (one query)."""
    if user is None or not event_ids:
        return set()
    if user.role == UserRole.ADMIN:
        return set(event_ids)

    # The user and their children
    covered_users = select(col(User.id)).where(
        or_(col(User.id) == user.id, col(User.guardian_id) == user.id)
    )
    registered = select(col(Registration.event_instance_id)).where(
        col(Registration.event_instance_id).in_(event_ids),
        col(Registration.status) == RegistrationStatusEnum.ACCEPTED,
        col(Registration.user_id).in_(covered_users),
    )
    checked_in = select(col(Attendance.event_instance_id)).where(
        col(Attendance.event_instance_id).in_(event_ids),
        col(Attendance.user_id).in_(covered_users),
    )
    result = await session.execute(union(registered, checked_in))
    return set(result.scalars().all())

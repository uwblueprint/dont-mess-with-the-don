import logging
from functools import lru_cache

from app.services.implementations.attendance_service import AttendanceService
from app.services.implementations.entity_service import EntityService
from app.services.implementations.event_series_service import EventSeriesService
from app.services.implementations.event_service import EventService
from app.services.implementations.event_type_service import EventTypeService
from app.services.implementations.registration_service import RegistrationService
from app.services.implementations.scheduler_service import SchedulerService
from app.services.implementations.simple_entity_service import SimpleEntityService
from app.services.implementations.user_service import UserService


@lru_cache
def get_logger() -> logging.Logger:
    """Get logger instance"""
    return logging.getLogger(__name__)


@lru_cache
def get_entity_service() -> EntityService:
    """Get entity service instance"""
    logger = get_logger()
    return EntityService(logger)


@lru_cache
def get_registration_service() -> RegistrationService:
    """Get registration service instance"""
    logger = get_logger()
    return RegistrationService(logger)


@lru_cache
def get_simple_entity_service() -> SimpleEntityService:
    """Get simple entity service instance"""
    logger = get_logger()
    return SimpleEntityService(logger)


@lru_cache
def get_event_service() -> EventService:
    """Get event service instance"""
    logger = get_logger()
    return EventService(logger)


@lru_cache
def get_user_service() -> UserService:
    """Get user service instance"""
    logger = get_logger()
    return UserService(logger)


@lru_cache
def get_scheduler_service() -> SchedulerService:
    """Get scheduler service instance"""
    logger = get_logger()
    return SchedulerService(logger)


@lru_cache
def get_attendance_service() -> AttendanceService:
    """Get attendance service instance"""
    logger = get_logger()
    return AttendanceService(logger)


@lru_cache
def get_event_series_service() -> EventSeriesService:
    """Get event series service instance"""
    logger = get_logger()
    return EventSeriesService(logger)


@lru_cache
def get_event_type_service() -> EventTypeService:
    """Get event type service instance"""
    logger = get_logger()
    return EventTypeService(logger)

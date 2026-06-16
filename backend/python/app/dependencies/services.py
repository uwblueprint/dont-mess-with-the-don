import logging
from functools import lru_cache

from app.services.implementations.attendance_service import AttendanceService
from app.services.implementations.entity_service import EntityService
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
def get_simple_entity_service() -> SimpleEntityService:
    """Get simple entity service instance"""
    logger = get_logger()
    return SimpleEntityService(logger)


@lru_cache
def get_user_service() -> UserService:
    """Get user service instance"""
    logger = get_logger()
    return UserService(logger)


@lru_cache
def get_attendance_service() -> AttendanceService:
    """Get attendance service instance"""
    logger = get_logger()
    return AttendanceService(logger)

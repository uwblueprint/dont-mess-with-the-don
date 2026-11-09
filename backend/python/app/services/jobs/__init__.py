"""Scheduled jobs - follows same pattern as routers"""

from app.services.implementations.scheduler_service import SchedulerService


def init_jobs(scheduler_service: SchedulerService) -> None:
    """Initialize all scheduled jobs - add new jobs here

    This function follows the same pattern as app.routers.init_app().
    To add a new scheduled job:
    1. Create a new file in this directory (e.g., email_jobs.py)
    2. Define your job function
    3. Import and register it here
    """
    from .event_generation_jobs import generate_recurring_events

    scheduler_service.add_cron_job(
        generate_recurring_events,
        job_id="generate_recurring_events",
        hour=0,
        minute=5,
    )

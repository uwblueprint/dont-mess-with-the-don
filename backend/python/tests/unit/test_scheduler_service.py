import logging

import pytest

from app.services.implementations.scheduler_service import SchedulerService


def _make_service() -> SchedulerService:
    return SchedulerService(logging.getLogger("test_scheduler"))


def test_start_and_stop() -> None:
    svc = _make_service()
    svc.start()
    try:
        assert svc._is_running is True
        assert svc.scheduler is not None
    finally:
        svc.stop()
    assert svc._is_running is False


def test_start_twice_is_noop() -> None:
    svc = _make_service()
    svc.start()
    try:
        first_scheduler = svc.scheduler
        svc.start()
        assert svc.scheduler is first_scheduler
        assert svc._is_running is True
    finally:
        svc.stop()


def test_add_before_start_raises() -> None:
    svc = _make_service()

    with pytest.raises(RuntimeError, match="must be started"):
        svc.add_cron_job(lambda: None, job_id="too_early", hour=9, minute=0)


def test_add_list_and_remove_job() -> None:
    svc = _make_service()
    svc.start()
    try:

        def job() -> None:
            return None

        svc.add_cron_job(job, job_id="heartbeat", hour=9, minute=0)
        jobs = svc.list_jobs()
        assert any(j["id"] == "heartbeat" for j in jobs)

        svc.remove_job("heartbeat")
        assert all(j["id"] != "heartbeat" for j in svc.list_jobs())
    finally:
        svc.stop()


def test_replace_existing_job_keeps_single_entry() -> None:
    svc = _make_service()
    svc.start()
    try:
        svc.add_cron_job(lambda: None, job_id="heartbeat", hour=9, minute=0)
        svc.add_cron_job(lambda: None, job_id="heartbeat", hour=10, minute=0)
        matching = [j for j in svc.list_jobs() if j["id"] == "heartbeat"]
        assert len(matching) == 1
    finally:
        svc.stop()


def test_async_job_wrapper_runs() -> None:
    svc = _make_service()
    svc.start()
    try:
        ran = {"ok": False}

        async def job() -> None:
            ran["ok"] = True

        svc.add_cron_job(job, job_id="async_heartbeat", hour=9, minute=0)
        assert svc.scheduler is not None
        registered = svc.scheduler.get_job("async_heartbeat")
        assert registered is not None

        # Invoke the wrapped sync callable directly (no wall-clock wait)
        registered.func()
        assert ran["ok"] is True
    finally:
        svc.stop()

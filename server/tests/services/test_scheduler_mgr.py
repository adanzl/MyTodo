import types
from unittest.mock import MagicMock

import pytest


@pytest.fixture
def scheduler_mgr_instance(monkeypatch):
    """Create a SchedulerMgr with a fully mocked underlying APScheduler instance."""
    import core.services.scheduler_mgr as sm

    mgr = sm.SchedulerMgr()

    # Replace the real scheduler with a strict mock to avoid starting threads/greenlets.
    scheduler_mock = MagicMock()
    scheduler_mock.running = False
    scheduler_mock.get_job.return_value = None
    scheduler_mock.get_jobs.return_value = []
    mgr.scheduler = scheduler_mock

    return mgr


def test_start_startup_and_already_running(scheduler_mgr_instance):
    mgr = scheduler_mgr_instance

    mgr.scheduler.running = False
    mgr.start()
    mgr.scheduler.start.assert_called_once()

    mgr.scheduler.start.reset_mock()
    mgr.scheduler.running = True
    mgr.start()
    mgr.scheduler.start.assert_not_called()


def test_shutdown_only_when_running(scheduler_mgr_instance):
    mgr = scheduler_mgr_instance

    mgr.scheduler.running = False
    mgr.shutdown()
    mgr.scheduler.shutdown.assert_not_called()

    mgr.scheduler.running = True
    mgr.shutdown(wait=False)
    mgr.scheduler.shutdown.assert_called_once_with(wait=False)


def test_shutdown_not_running_noop(scheduler_mgr_instance):
    mgr = scheduler_mgr_instance
    mgr.scheduler.running = False
    mgr.shutdown(wait=False)
    mgr.scheduler.shutdown.assert_not_called()


def test_add_cron_job_with_expression_6_fields(monkeypatch, scheduler_mgr_instance):
    mgr = scheduler_mgr_instance

    import core.services.scheduler_mgr as sm

    # Ensure weekday conversion is invoked and deterministic
    monkeypatch.setattr(sm, "convert_standard_cron_weekday_to_apscheduler", lambda x: "mon")

    cron_trigger = object()
    monkeypatch.setattr(sm, "CronTrigger", MagicMock(return_value=cron_trigger))

    called = {"func": 0}

    def f():
        called["func"] += 1

    ok = mgr.add_cron_job(f, "job1", cron_expression="0 1 2 3 4 1")
    assert ok is True

    sm.CronTrigger.assert_called_once()
    mgr.scheduler.add_job.assert_called_once()


def test_add_cron_job_with_expression_5_fields(monkeypatch, scheduler_mgr_instance):
    mgr = scheduler_mgr_instance

    import core.services.scheduler_mgr as sm

    monkeypatch.setattr(sm, "convert_standard_cron_weekday_to_apscheduler", lambda x: "mon")

    cron_trigger = object()
    monkeypatch.setattr(sm, "CronTrigger", MagicMock(return_value=cron_trigger))

    ok = mgr.add_cron_job(lambda: None, "job2", cron_expression="1 2 3 4 1")
    assert ok is True

    sm.CronTrigger.assert_called_once()
    mgr.scheduler.add_job.assert_called_once()


def test_add_cron_job_invalid_expression_returns_false(monkeypatch, scheduler_mgr_instance):
    mgr = scheduler_mgr_instance

    import core.services.scheduler_mgr as sm

    monkeypatch.setattr(sm, "CronTrigger", MagicMock())

    ok = mgr.add_cron_job(lambda: None, "job_bad", cron_expression="1 2 3")
    assert ok is False


def test_add_cron_job_removes_existing_job(monkeypatch, scheduler_mgr_instance):
    mgr = scheduler_mgr_instance

    existing_job = object()
    mgr.scheduler.get_job.return_value = existing_job

    import core.services.scheduler_mgr as sm

    monkeypatch.setattr(sm, "CronTrigger", MagicMock(return_value=object()))

    ok = mgr.add_cron_job(lambda: None, "job3", minute="*/1")
    assert ok is True

    mgr.scheduler.remove_job.assert_called_once_with("job3")


def test_add_cron_job_when_trigger_construction_raises(monkeypatch, scheduler_mgr_instance):
    mgr = scheduler_mgr_instance

    import core.services.scheduler_mgr as sm

    monkeypatch.setattr(sm, "CronTrigger", lambda **kw: (_ for _ in ()).throw(ValueError("bad")))

    ok = mgr.add_cron_job(lambda: None, "job_bad2", minute="*/1")
    assert ok is False


def test_add_interval_job_and_date_job(monkeypatch, scheduler_mgr_instance):
    mgr = scheduler_mgr_instance

    import core.services.scheduler_mgr as sm

    monkeypatch.setattr(sm, "IntervalTrigger", MagicMock(return_value=object()))
    monkeypatch.setattr(sm, "DateTrigger", MagicMock(return_value=object()))

    assert mgr.add_interval_job(lambda: None, "int1", seconds=10) is True
    assert mgr.add_date_job(lambda: None, "date1", run_date=sm.datetime.now()) is True


def test_add_interval_job_exception_returns_false(monkeypatch, scheduler_mgr_instance):
    mgr = scheduler_mgr_instance

    # Force scheduler.add_job to fail
    mgr.scheduler.add_job.side_effect = RuntimeError("boom")

    ok = mgr.add_interval_job(lambda: None, "int_bad", seconds=1)
    assert ok is False


def test_add_date_job_exception_returns_false(monkeypatch, scheduler_mgr_instance):
    mgr = scheduler_mgr_instance

    mgr.scheduler.add_job.side_effect = RuntimeError("boom")

    import core.services.scheduler_mgr as sm

    ok = mgr.add_date_job(lambda: None, "date_bad", run_date=sm.datetime.now())
    assert ok is False


def test_remove_pause_resume_job(monkeypatch, scheduler_mgr_instance):
    mgr = scheduler_mgr_instance

    # job exists
    mgr.scheduler.get_job.return_value = object()
    assert mgr.remove_job("j1") is True
    mgr.scheduler.remove_job.assert_called_with("j1")

    mgr.scheduler.get_job.return_value = object()
    assert mgr.pause_job("j2") is True
    mgr.scheduler.pause_job.assert_called_with("j2")

    mgr.scheduler.get_job.return_value = object()
    assert mgr.resume_job("j3") is True
    mgr.scheduler.resume_job.assert_called_with("j3")

    # job not exist
    mgr.scheduler.get_job.return_value = None
    assert mgr.remove_job("j4") is False
    assert mgr.pause_job("j5") is False
    assert mgr.resume_job("j6") is False


def test_remove_job_exception_returns_false(scheduler_mgr_instance):
    mgr = scheduler_mgr_instance

    mgr.scheduler.get_job.return_value = object()
    mgr.scheduler.remove_job.side_effect = RuntimeError("boom")

    assert mgr.remove_job("j") is False


def test_pause_job_exception_returns_false(scheduler_mgr_instance):
    mgr = scheduler_mgr_instance

    mgr.scheduler.get_job.return_value = object()
    mgr.scheduler.pause_job.side_effect = RuntimeError("boom")

    assert mgr.pause_job("j") is False


def test_resume_job_exception_returns_false(scheduler_mgr_instance):
    mgr = scheduler_mgr_instance

    mgr.scheduler.get_job.return_value = object()
    mgr.scheduler.resume_job.side_effect = RuntimeError("boom")

    assert mgr.resume_job("j") is False


def test_get_job_and_get_all_jobs(scheduler_mgr_instance):
    mgr = scheduler_mgr_instance

    job_obj = object()
    mgr.scheduler.get_job.return_value = job_obj
    assert mgr.get_job("x") is job_obj

    jobs = [object(), object()]
    mgr.scheduler.get_jobs.return_value = jobs
    assert mgr.get_all_jobs() == jobs


def test_print_jobs_no_jobs(scheduler_mgr_instance, monkeypatch):
    mgr = scheduler_mgr_instance

    import core.services.scheduler_mgr as sm

    log_mock = MagicMock()
    monkeypatch.setattr(sm, "log", log_mock)

    mgr.scheduler.get_jobs.return_value = []
    mgr.print_jobs()
    assert log_mock.info.called


def test_print_jobs_with_jobs(scheduler_mgr_instance, monkeypatch):
    mgr = scheduler_mgr_instance

    import core.services.scheduler_mgr as sm

    log_mock = MagicMock()
    monkeypatch.setattr(sm, "log", log_mock)

    job1 = types.SimpleNamespace(id="j1", name="n1", next_run_time=1)
    job2 = types.SimpleNamespace(id="j2", name="n2", next_run_time=2)

    mgr.scheduler.get_jobs.return_value = [job1, job2]
    mgr.print_jobs()

    # should print header + each job
    assert log_mock.info.call_count >= 3


def test_job_executed_listener_handles_gevent_loopexit(monkeypatch, scheduler_mgr_instance):
    mgr = scheduler_mgr_instance

    import core.services.scheduler_mgr as sm

    # Provide a fake gevent module with LoopExit type
    class FakeLoopExit(Exception):
        pass

    fake_gevent = types.SimpleNamespace(exceptions=types.SimpleNamespace(LoopExit=FakeLoopExit))
    monkeypatch.setattr(sm, "gevent", fake_gevent, raising=False)

    event = types.SimpleNamespace(job_id="j", exception=FakeLoopExit("bye"))
    mgr._job_executed_listener(event)


def test_job_executed_listener_handles_other_exception(scheduler_mgr_instance):
    mgr = scheduler_mgr_instance

    event = types.SimpleNamespace(job_id="j", exception=Exception("boom"))
    mgr._job_executed_listener(event)


def test_job_executed_listener_success_no_exception(scheduler_mgr_instance):
    mgr = scheduler_mgr_instance

    event = types.SimpleNamespace(job_id="j", exception=None)
    mgr._job_executed_listener(event)

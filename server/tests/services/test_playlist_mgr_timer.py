import datetime
from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture
def mgr_with_mock_scheduler(monkeypatch):
    import core.services.playlist_mgr as pm

    # Disable all background workers before creating the instance
    monkeypatch.setattr(pm.PlaylistRepository, "start_save_worker", lambda self: None)
    monkeypatch.setattr(pm.DurationFetcher, "start_batch_fetch", lambda self, playlists: None)

    mgr = pm.PlaylistMgr()
    mgr._playlist_raw = {}
    # 用 clear 而非 reassign，保持 PlaylistScheduling 等持有的引用有效。
    mgr._devices.clear()
    mgr._playing_playlists.clear()
    mgr._play_state.clear()

    scheduler = MagicMock()
    scheduler.get_job.return_value = None

    # P3 后 scheduler_mgr 只在 playlist.scheduling 里 import；通过 __globals__ patch 命中原 module（避开 sys.modules 还原坑）
    monkeypatch.setitem(pm.PlaylistScheduling.refresh_cron_job.__globals__, "scheduler_mgr", scheduler)
    monkeypatch.setattr(pm.time, "sleep", lambda *_: None)

    # Mock the spawn function to run synchronously for testing RDS saves
    monkeypatch.setattr(pm, "spawn", lambda func, *args, **kwargs: func(*args, **kwargs))

    return mgr, scheduler, pm


def test_start_file_timer_and_callback_device_stopped(mgr_with_mock_scheduler, monkeypatch):
    mgr, scheduler, pm = mgr_with_mock_scheduler

    pid = "p1"
    mgr._playlist_raw[pid] = {"name": "P1", "pre_lists": [[] for _ in range(7)], "files": [{"uri": "a.mp3"}]}

    device = MagicMock()
    device.get_status.return_value = (0, {"state": "STOPPED", "duration": "00:00:10", "position": "00:00:10"})
    device.stop.return_value = (0, "ok")
    mgr._devices[pid] = {"obj": device}

    mgr.play_next = MagicMock(return_value=(0, "ok"))

    mgr._scheduling.start_file_timer(pid, 1)
    cb = scheduler.add_date_job.call_args.kwargs["func"]
    cb()

    device.get_status.assert_called_once()
    device.stop.assert_called()
    mgr.play_next.assert_called_once_with(pid)


def test_start_file_timer_callback_device_playing_with_delay(mgr_with_mock_scheduler, monkeypatch):
    mgr, scheduler, pm = mgr_with_mock_scheduler
    pid = "p1"
    mgr._playlist_raw[pid] = {"name": "P1", "files": [{"uri": "a.mp3"}]}
    device = MagicMock()
    device.get_status.return_value = (0, {"state": "PLAYING", "duration": "00:00:10", "position": "00:00:05"})
    mgr._devices[pid] = {"obj": device}
    mgr.play_next = MagicMock()

    with patch.object(pm.time, 'sleep') as mock_sleep:
        mgr._scheduling.start_file_timer(pid, 1)
        cb = scheduler.add_date_job.call_args.kwargs["func"]
        cb()
        mock_sleep.assert_called_once()


def test_start_file_timer_callback_get_status_fails(mgr_with_mock_scheduler):
    mgr, scheduler, pm = mgr_with_mock_scheduler
    pid = "p1"
    mgr._playlist_raw[pid] = {"name": "P1", "files": [{"uri": "a.mp3"}]}
    device = MagicMock()
    device.get_status.return_value = (-1, {"error": "failed"})
    mgr._devices[pid] = {"obj": device}
    mgr.play_next = MagicMock()

    mgr._scheduling.start_file_timer(pid, 1)
    cb = scheduler.add_date_job.call_args.kwargs["func"]
    cb()
    mgr.play_next.assert_called_once()


def test_start_playlist_duration_timer_clears_when_not_playing(mgr_with_mock_scheduler):
    mgr, scheduler, pm = mgr_with_mock_scheduler
    pid = "p1"
    mgr._playlist_raw[pid] = {"name": "P1"}
    mgr._scheduling.playlist_duration_timers[pid] = f"playlist_duration_timer_{pid}"

    mgr._scheduling.start_playlist_duration_timer(pid, 1)
    cb = scheduler.add_date_job.call_args.kwargs["func"]
    cb()
    assert pid not in mgr._scheduling.scheduled_play_start_times


def test_start_playlist_duration_timer_stops_when_playing(mgr_with_mock_scheduler):
    mgr, scheduler, pm = mgr_with_mock_scheduler
    pid = "p1"
    mgr._playlist_raw[pid] = {"name": "P1"}
    mgr._playing_playlists.add(pid)
    # duration timer 通过注入的 on_stop 回调触发停止；直接替换它最简单
    stop_mock = MagicMock(return_value=(0, "ok"))
    mgr._scheduling._on_stop = stop_mock

    mgr._scheduling.start_playlist_duration_timer(pid, 1)
    cb = scheduler.add_date_job.call_args.kwargs["func"]
    cb()
    stop_mock.assert_called_once_with(pid)

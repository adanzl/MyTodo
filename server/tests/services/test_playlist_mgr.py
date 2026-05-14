import pytest
from unittest.mock import patch, MagicMock, call
import json
import fakeredis
import datetime
import types

# Mock the global dependencies before importing the manager
mock_scheduler_mgr = MagicMock()
mock_gevent = MagicMock()

modules = {
    'core.services.scheduler_mgr': mock_scheduler_mgr,
    'gevent': mock_gevent,
}

with patch.dict('sys.modules', modules):
    import core.services.playlist_mgr as pm
    from core.services.playlist_mgr import PlaylistMgr
    import core.db.rds_mgr as rds_mgr


def create_playlist_data(p_id,
                         name,
                         files,
                         device_type='dlna',
                         trigger_button=None,
                         schedule=None,
                         device_volume=None,
                         pre_lists=None,
                         **extra_props):
    # 注意：实现侧使用 "playlist" 字段，这里同时写入 "playlist" 与 "files" 以兼容历史用例。
    data = {
        "id": p_id,
        "name": name,
        "playlist": files,
        "files": files,
        "device": {
            "type": device_type,
            "address": f"http://{p_id}.local"
        },
        "pre_lists": pre_lists if pre_lists is not None else [[] for _ in range(7)],
        "trigger_button": trigger_button,
        "schedule": schedule or {
            "enabled": 0,
            "cron": ""
        }
    }
    if device_volume is not None:
        data["device_volume"] = device_volume
    data.update(extra_props)
    return data


@pytest.fixture
def mock_device():
    device = MagicMock()
    device.play.return_value = (0, "ok")
    device.stop.return_value = (0, "ok")
    device.set_volume.return_value = (0, "ok")
    device.get_status.return_value = (0, {"state": "STOPPED", "duration": "00:00:10", "position": "00:00:10"})
    return device


@pytest.fixture
def playlist_mgr(monkeypatch, mock_device):
    # Mock network calls made by upnpclient
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.text = """<root><device>
        <serviceList>
            <service>
                <serviceType>urn:schemas-upnp-org:service:AVTransport:1</serviceType>
                <controlURL>/AVTransport/control</controlURL>
            </service>
            <service>
                <serviceType>urn:schemas-upnp-org:service:RenderingControl:1</serviceType>
                <controlURL>/RenderingControl/control</controlURL>
            </service>
        </serviceList>
    </device></root>"""
    monkeypatch.setattr('core.device.dlna.upnpclient.Device', MagicMock(return_value=mock_device))

    fake_redis_client = fakeredis.FakeRedis()
    monkeypatch.setattr(rds_mgr, 'rds', fake_redis_client)

    # P5 后 create_device 只在 playlist.devices 里 import；走 __globals__ 才能命中正确的 module 实例。
    monkeypatch.setitem(
        pm.PlaylistDevices.refresh_single.__globals__,
        "create_device",
        MagicMock(return_value={"obj": mock_device}),
    )
    # P3 后 scheduler_mgr 只在 playlist.scheduling 里 import；通过 __globals__ patch 才能命中
    # 真正的 scheduling module（with patch.dict('sys.modules') 还原后 import 得到的会是另一份）
    monkeypatch.setitem(pm.PlaylistScheduling.refresh_cron_job.__globals__, "scheduler_mgr", mock_scheduler_mgr)

    # Disable background workers by default; specific tests can call internal methods directly
    monkeypatch.setattr(pm.PlaylistRepository, "start_save_worker", lambda self: None)

    monkeypatch.setattr(pm, "spawn", lambda fn, *a, **kw: MagicMock())
    monkeypatch.setattr(pm, "sleep", lambda *a, **kw: None)

    mock_scheduler_mgr.reset_mock()
    mock_gevent.reset_mock()

    # Force linux-only behavior inside the playlist_mgr module (safe: doesn't touch global sys.platform)
    monkeypatch.setattr(pm.sys, "platform", "linux")

    mgr = PlaylistMgr()
    mgr._playlist_raw = {}
    # 用 clear 而非 reassign，保持 PlaylistScheduling 等持有的引用有效。
    mgr._devices.clear()
    mgr._playing_playlists.clear()
    mgr._play_state.clear()
    fake_redis_client.flushall()
    return mgr


def test_reload_from_rds(playlist_mgr):
    mock_playlist = create_playlist_data("p1", "Playlist 1", [{"uri": "file1.mp3"}])
    mock_playlist_data = {"p1": mock_playlist}
    rds_mgr.set("schedule_play:playlist_collection", json.dumps(mock_playlist_data))

    result = playlist_mgr.reload()

    assert result == 0
    assert "p1" in playlist_mgr._playlist_raw
    assert "p1" in playlist_mgr._devices


def test_reload_non_linux_is_noop(playlist_mgr, monkeypatch):
    monkeypatch.setattr(pm.sys, "platform", "darwin")
    result = playlist_mgr.reload()
    assert result == 0


def test_reload_redis_error_sets_needs_reload(playlist_mgr, monkeypatch):

    def bad_get(key):
        raise ConnectionError("no")

    monkeypatch.setattr(rds_mgr, "get", bad_get)
    result = playlist_mgr.reload()
    assert result == -1
    assert playlist_mgr._needs_reload is True


def test_reload_invalid_json_is_handled(playlist_mgr):
    rds_mgr.set("schedule_play:playlist_collection", "not json")
    result = playlist_mgr.reload()
    assert result == -1


def test_reload_cleans_up_orphaned_play_state(playlist_mgr):
    mock_playlist = create_playlist_data("p1", "P1", [])
    rds_mgr.set("schedule_play:playlist_collection", json.dumps({"p1": mock_playlist}))

    playlist_mgr._play_state = {"p1": {}, "orphan": {}}
    playlist_mgr.reload()
    assert "orphan" not in playlist_mgr._play_state


@patch.object(pm.DurationFetcher, 'update_file_duration', return_value=180)
def test_play_logic(mock_get_duration, playlist_mgr, mock_device):
    playlist_id = "p1"
    playlist_data = create_playlist_data(playlist_id, "Test Playlist", [{"uri": "s1.mp3"}, {"uri": "s2.mp3"}])
    playlist_mgr.update_single_playlist(playlist_data)

    code, msg = playlist_mgr.play(playlist_id)
    assert code == 0
    mock_device.play.assert_called_once_with("s1.mp3")

    mock_device.play.reset_mock()
    playlist_mgr.play_next(playlist_id)
    mock_device.play.assert_called_once_with("s2.mp3")

    playlist_mgr.stop(playlist_id)
    mock_device.stop.assert_called_once()


@patch.object(pm.DurationFetcher, 'update_file_duration', return_value=180)
def test_play_rejects_when_already_playing_unless_force(mock_get_duration, playlist_mgr):
    playlist_id = "p1"
    playlist_data = create_playlist_data(playlist_id, "Test Playlist", [{"uri": "s1.mp3"}])
    playlist_mgr.update_single_playlist(playlist_data)

    code, msg = playlist_mgr.play(playlist_id)
    assert code == 0

    code, msg = playlist_mgr.play(playlist_id, force=False)
    assert code != 0

    code, msg = playlist_mgr.play(playlist_id, force=True)
    assert code == 0


def test_get_playlist_nonexistent_id_returns_empty(playlist_mgr):
    """get_playlist 当 id 不存在时返回空 dict"""
    playlist_mgr._playlist_raw = {"p1": {"id": "p1", "name": "n", "files": []}}
    result = playlist_mgr.get_playlist("nonexistent")
    assert result == {}


def test_get_playlist_with_play_state_in_pre_files(playlist_mgr):
    """get_playlist 当列表在播放且 in_pre_files 为 True 时包含 pre_index"""
    playlist_id = "p1"
    playlist_mgr._playlist_raw = {playlist_id: {"id": playlist_id, "name": "n", "files": []}}
    playlist_mgr._play_state[playlist_id] = {"in_pre_files": True, "pre_index": 2}
    result = playlist_mgr.get_playlist(playlist_id)
    pl = result[playlist_id]
    assert pl.get("in_pre_files") is True
    assert pl.get("pre_index") == 2


def test_get_playlist_with_play_state_not_in_pre_files(playlist_mgr):
    """get_playlist 当列表在播放但 in_pre_files 为 False 时 pre_index 为 -1"""
    playlist_id = "p1"
    playlist_mgr._playlist_raw = {playlist_id: {"id": playlist_id, "name": "n", "files": []}}
    playlist_mgr._play_state[playlist_id] = {"in_pre_files": False}
    result = playlist_mgr.get_playlist(playlist_id)
    pl = result[playlist_id]
    assert pl.get("in_pre_files") is False
    assert pl.get("pre_index") == -1


def test_play_invalid_id(playlist_mgr):
    code, msg = playlist_mgr.play("nope")
    assert code != 0


@patch.object(pm.DurationFetcher, 'update_file_duration', return_value=180)
def test_play_invalid_file_uri(mock_get_duration, playlist_mgr):
    playlist_id = "p1"
    playlist_data = create_playlist_data(playlist_id, "Test Playlist", [{"bad": "x"}])
    playlist_mgr.update_single_playlist(playlist_data)

    code, msg = playlist_mgr.play(playlist_id)
    assert code != 0


@patch.object(pm.DurationFetcher, 'update_file_duration', return_value=180)
def test_play_device_play_failure(mock_get_duration, playlist_mgr, mock_device):
    playlist_id = "p1"
    playlist_data = create_playlist_data(playlist_id, "Test Playlist", [{"uri": "s1.mp3"}])
    playlist_mgr.update_single_playlist(playlist_data)

    mock_device.play.return_value = (-1, "fail")
    code, msg = playlist_mgr.play(playlist_id)
    assert code == -1


@patch.object(pm.DurationFetcher, 'update_file_duration', return_value=180)
def test_play_sets_volume_when_configured(mock_get_duration, playlist_mgr, mock_device):
    playlist_id = "p1"
    playlist_data = create_playlist_data(playlist_id, "Test Playlist", [{"uri": "s1.mp3"}], device_volume=15)
    playlist_mgr.update_single_playlist(playlist_data)

    code, msg = playlist_mgr.play(playlist_id)
    assert code == 0
    mock_device.set_volume.assert_called_once_with(15)


@patch.object(pm.DurationFetcher, 'update_file_duration', return_value=180)
def test_play_sets_volume_failure_is_ignored(mock_get_duration, playlist_mgr, mock_device):
    playlist_id = "p1"
    playlist_data = create_playlist_data(playlist_id, "Test Playlist", [{"uri": "s1.mp3"}], device_volume=15)
    playlist_mgr.update_single_playlist(playlist_data)

    mock_device.set_volume.return_value = (-1, "bad")

    code, msg = playlist_mgr.play(playlist_id)
    assert code == 0


@patch.object(pm.DurationFetcher, 'update_file_duration', return_value=180)
def test_play_sets_volume_exception_is_ignored(mock_get_duration, playlist_mgr, mock_device):
    playlist_id = "p1"
    playlist_data = create_playlist_data(playlist_id, "Test Playlist", [{"uri": "s1.mp3"}], device_volume=15)
    playlist_mgr.update_single_playlist(playlist_data)

    mock_device.set_volume.side_effect = Exception("boom")

    code, msg = playlist_mgr.play(playlist_id)
    assert code == 0


@patch.object(pm.DurationFetcher, 'update_file_duration', return_value=180)
def test_play_next_and_pre_logic(mock_get_duration, playlist_mgr, mock_device):
    weekday = datetime.datetime.today().weekday()
    pre_lists = [[] for _ in range(7)]
    pre_lists[weekday] = [{"uri": "pre1.mp3"}]

    playlist_id = "p1"
    playlist_data = create_playlist_data(playlist_id,
                                         "Test Playlist", [{
                                             "uri": "f1.mp3"
                                         }, {
                                             "uri": "f2.mp3"
                                         }],
                                         pre_lists=pre_lists)
    playlist_mgr.update_single_playlist(playlist_data)

    playlist_mgr.play(playlist_id)
    mock_device.play.assert_called_with("pre1.mp3")

    mock_device.play.reset_mock()
    playlist_mgr.play_next(playlist_id)
    mock_device.play.assert_called_with("f1.mp3")

    mock_device.play.reset_mock()
    playlist_mgr.play_pre(playlist_id)
    mock_device.play.assert_called_with("pre1.mp3")


def test_play_next_no_more_files(playlist_mgr):
    playlist_id = "p1"
    playlist_data = create_playlist_data(playlist_id, "Test Playlist", [])
    playlist_mgr.update_single_playlist(playlist_data)

    code, msg = playlist_mgr.play_next(playlist_id)
    assert code == -1


def test_trigger_button_stop(playlist_mgr):
    p1 = create_playlist_data("p1", "P1", [{"uri": "f1.mp3"}], trigger_button="1")
    p2 = create_playlist_data("p2", "P2", [{"uri": "f2.mp3"}], trigger_button="1")
    playlist_mgr.update_single_playlist(p1)
    playlist_mgr.update_single_playlist(p2)

    playlist_mgr.play("p1")
    assert "p1" in playlist_mgr._playing_playlists

    code, msg = playlist_mgr.trigger_button("1", "stop")
    assert code == 0
    assert not playlist_mgr._playing_playlists

    code, msg = playlist_mgr.trigger_button("99", "stop")
    assert code == -1


def test_trigger_button_play(playlist_mgr, mock_device):
    p1 = create_playlist_data("p1",
                              "P1", [{
                                  "uri": "f1.mp3"
                              }],
                              trigger_button="1",
                              schedule={
                                  "enabled": 1,
                                  "cron": "* * * * *"
                              })
    playlist_mgr.update_single_playlist(p1)

    code, msg = playlist_mgr.trigger_button("1", "play")
    assert code == 0
    mock_device.play.assert_called_with("f1.mp3")

    code, msg = playlist_mgr.trigger_button("99", "play")
    assert code == -1


def test_trigger_button_play_not_triggered_today(playlist_mgr):
    p1 = create_playlist_data("p1",
                              "P1", [{
                                  "uri": "f1.mp3"
                              }],
                              trigger_button="1",
                              schedule={
                                  "enabled": 1,
                                  "cron": "* * * * *"
                              })
    playlist_mgr.update_single_playlist(p1)

    code, msg = playlist_mgr.trigger_button("1", "play")
    assert code == 0


def test_stop_on_not_playing(playlist_mgr, mock_device):
    p1 = create_playlist_data("p1", "P1", [{"uri": "f1.mp3"}])
    playlist_mgr.update_single_playlist(p1)

    code, msg = playlist_mgr.stop("p1")
    assert code == 0
    mock_device.stop.assert_called_once()


def test_collect_files_without_duration(playlist_mgr):
    p1 = create_playlist_data("p1", "P1", [{"uri": "f1.mp3"}, {"uri": "f2.mp3", "duration": 10}])
    playlist_mgr._duration_fetcher.blacklist["f3.mp3"] = 4
    p1["pre_lists"][0] = [{"uri": "f3.mp3"}, {"uri": "f4.mp3"}]

    files_to_fetch = playlist_mgr._duration_fetcher.collect_files_without_duration(p1)
    assert files_to_fetch == {"f1.mp3", "f4.mp3"}


def test_update_files_duration(playlist_mgr):
    p1 = create_playlist_data("p1", "P1", [{"uri": "f1.mp3"}, {"uri": "f2.mp3"}])
    durations = {"f1.mp3": 10, "f3.mp3": 20}

    updated_count = playlist_mgr._duration_fetcher.update_files_duration(p1, durations)
    assert updated_count == 1
    assert p1["playlist"][0]["duration"] == 10
    assert "duration" not in p1["playlist"][1]


def test_cleanup_orphaned_cron_jobs(playlist_mgr):
    mock_scheduler_mgr.get_all_jobs.return_value = [
        types.SimpleNamespace(id="playlist_cron_p1"),
        types.SimpleNamespace(id="playlist_cron_orphan"),
        types.SimpleNamespace(id="other_job"),
    ]

    p1 = create_playlist_data("p1", "P1", [])
    playlist_mgr.update_single_playlist(p1)

    playlist_mgr._cleanup_orphans()

    mock_scheduler_mgr.remove_job.assert_any_call("playlist_cron_orphan")


def test_get_playlist_reloads_if_needed(playlist_mgr, monkeypatch):
    playlist_mgr._needs_reload = True
    mock_reload = MagicMock()
    monkeypatch.setattr(playlist_mgr, "reload", mock_reload)

    playlist_mgr.get_playlist()
    mock_reload.assert_called_once()


def test_get_playlist_injects_play_state(playlist_mgr):
    p1 = create_playlist_data("p1", "P1", [{"uri": "f1.mp3"}])
    playlist_mgr.update_single_playlist(p1)

    res = playlist_mgr.get_playlist("p1")
    assert res["p1"]["in_pre_files"] is False
    assert res["p1"]["pre_index"] == -1

    playlist_mgr._play_state["p1"] = {"in_pre_files": True, "pre_index": 0}
    res = playlist_mgr.get_playlist("p1")
    assert res["p1"]["in_pre_files"] is True
    assert res["p1"]["pre_index"] == 0

    playlist_mgr._play_state["p1"] = {"in_pre_files": False, "pre_index": 0}
    res = playlist_mgr.get_playlist("p1")
    assert res["p1"]["in_pre_files"] is False
    assert res["p1"]["pre_index"] == -1


def test_update_single_playlist_error_paths(playlist_mgr):
    assert playlist_mgr.update_single_playlist(None) == -1
    assert playlist_mgr.update_single_playlist({"name": "no-id"}) == -1


def test_validate_playlist_empty_and_missing_device(playlist_mgr):
    p1 = create_playlist_data("p1", "P1", [])
    playlist_mgr.update_single_playlist(p1)

    playlist_mgr._devices["p1"] = {"obj": MagicMock()}
    playlist_mgr._playlist_raw["p1"]["files"] = []
    playlist_mgr._playlist_raw["p1"]["pre_lists"] = [[] for _ in range(7)]

    data, code, msg = playlist_mgr._validate_playlist("p1")
    assert code == -1
    assert msg == "播放列表为空"

    p2 = create_playlist_data("p2", "P2", [{"uri": "f1.mp3"}])
    playlist_mgr._playlist_raw["p2"] = p2
    playlist_mgr._devices.pop("p2")

    data, code, msg = playlist_mgr._validate_playlist("p2")
    assert code == -1
    assert msg == "设备不存在或未初始化"


def test_get_current_file_out_of_range_errors(playlist_mgr):
    pre_files = [{"uri": "p.mp3"}]
    files = [{"uri": "f.mp3"}]

    item, err = playlist_mgr._get_current_file({
        "in_pre_files": True,
        "pre_index": 1,
        "file_index": 0
    }, pre_files, files)
    assert item is None
    assert "pre_files 索引" in err

    item, err = playlist_mgr._get_current_file({
        "in_pre_files": False,
        "pre_index": 0,
        "file_index": 2
    }, pre_files, files)
    assert item is None
    assert "playlist 索引" in err


def test_refresh_single_devices_invalid_type(playlist_mgr):
    p1 = create_playlist_data("p1", "P1", [], device_type="invalid_type")
    playlist_mgr.update_single_playlist(p1)
    assert "p1" not in playlist_mgr._devices


def test_start_file_timer_handles_get_status_error(playlist_mgr, mock_device, monkeypatch):
    captured = {}

    def capture_add_date_job(func, job_id, run_date):
        captured["func"] = func
        captured["job_id"] = job_id
        return True

    monkeypatch.setattr(mock_scheduler_mgr, 'add_date_job', capture_add_date_job)

    p1 = create_playlist_data("p1", "P1", [{"uri": "f1.mp3", "duration": 10}])
    playlist_mgr.update_single_playlist(p1)
    playlist_mgr.play("p1")

    mock_device.get_status.return_value = (-1, {"error": "device offline"})

    monkeypatch.setattr(playlist_mgr, "play_next", MagicMock(return_value=(0, "ok")))

    playlist_mgr._scheduling.start_file_timer("p1", 0.01)
    assert "func" in captured

    captured["func"]()
    playlist_mgr.play_next.assert_called_once_with("p1")


def test_start_playlist_duration_timer_when_existing_job_expired_is_removed(playlist_mgr, monkeypatch):

    class _Job:

        def __init__(self, next_run_time):
            self.next_run_time = next_run_time

    expired_job = _Job(datetime.datetime.now() - datetime.timedelta(seconds=60))

    monkeypatch.setattr(mock_scheduler_mgr, 'get_job', lambda job_id: expired_job)
    monkeypatch.setattr(mock_scheduler_mgr, 'remove_job', MagicMock())

    captured = {}

    def capture_add_date_job(func, job_id, run_date):
        captured["job_id"] = job_id
        captured["run_date"] = run_date
        return True

    monkeypatch.setattr(mock_scheduler_mgr, 'add_date_job', capture_add_date_job)

    p1 = create_playlist_data("p1", "P1", [{"uri": "f1.mp3"}])
    playlist_mgr.update_single_playlist(p1)

    playlist_mgr._scheduling.start_playlist_duration_timer("p1", 1)

    mock_scheduler_mgr.remove_job.assert_any_call("playlist_duration_timer_p1")
    assert captured["job_id"] == "playlist_duration_timer_p1"


def test_start_batch_duration_fetch_updates_and_blacklists(playlist_mgr, monkeypatch):
    # Make thread execute immediately and capture target/args
    captured = {}

    class FakeThread:

        def __init__(self, target, args=(), daemon=True, name=None):
            captured["target"] = target
            captured["args"] = args

        def is_alive(self):
            return False

        def start(self):
            captured["target"](*captured["args"])

    # 注意：测试顶部 `with patch.dict('sys.modules', ...)` 退出时会把 import 进来的
    # `core.services.playlist.duration_fetch` 从 sys.modules 中移除，于是模块对象
    # 没法通过 `import` / `sys.modules` 再拿到。但 fetcher 类还活着，它的方法的
    # `__globals__` 就是当年那份模块字典，直接 patch 这个字典即可。
    df_globals = pm.DurationFetcher.update_file_duration.__globals__
    monkeypatch.setattr(df_globals["threading"], "Thread", FakeThread)

    p1 = create_playlist_data("p1", "P1", [{"uri": "ok.mp3"}, {"uri": "none.mp3"}, {"uri": "boom.mp3"}])
    playlist_mgr.update_single_playlist(p1)
    playlist_mgr._playlist_raw = {"p1": playlist_mgr._playlist_raw["p1"]}

    def fake_get_media_duration(uri):
        if uri == "ok.mp3":
            return 12
        if uri == "none.mp3":
            return None
        raise RuntimeError("boom")

    monkeypatch.setitem(df_globals, "get_media_duration", fake_get_media_duration)

    q = MagicMock()
    playlist_mgr._duration_fetcher._rds_save_queue = q

    playlist_mgr._duration_fetcher.start_batch_fetch({"p1": playlist_mgr._playlist_raw["p1"]})

    assert playlist_mgr._playlist_raw["p1"]["playlist"][0]["duration"] == 12
    assert playlist_mgr._duration_fetcher.blacklist["none.mp3"] >= 1
    assert playlist_mgr._duration_fetcher.blacklist["boom.mp3"] >= 1
    q.put.assert_any_call('save_playlist')


def test_get_pre_list_for_today_edge_cases():
    """_get_pre_list_for_today: pre_lists 非7元素或当天元素非 list 时返回 []"""
    assert pm._get_pre_list_for_today([]) == []
    assert pm._get_pre_list_for_today([[]] * 3) == []
    # 7 个元素但当天索引处不是 list（由 weekday 决定，用 patch 固定）
    with patch.object(pm, 'get_weekday_index', return_value=0):
        assert pm._get_pre_list_for_today([[], [], [], [], [], [], []]) == []
        assert pm._get_pre_list_for_today([[{"uri": "a.mp3"}], [], [], [], [], [], []]) == [{"uri": "a.mp3"}]


def test_save_playlist_to_rds_exception(playlist_mgr, monkeypatch):
    """repo.save 异常时向上抛出"""
    playlist_mgr._playlist_raw = {"p1": {}}
    monkeypatch.setattr(rds_mgr, 'set', MagicMock(side_effect=RuntimeError("redis error")))
    with pytest.raises(RuntimeError, match="redis error"):
        playlist_mgr._repo.save()


def test_update_single_playlist_exception(playlist_mgr, monkeypatch):
    """update_single_playlist 内部异常时返回 -1"""
    playlist_mgr._playlist_raw = {}
    monkeypatch.setattr(playlist_mgr._repo, 'save', MagicMock(side_effect=Exception("save fail")))
    ret = playlist_mgr.update_single_playlist({"id": "p1", "name": "P1", "files": []})
    assert ret == -1


def test_refresh_cron_job_add_cron_fails(playlist_mgr, monkeypatch):
    """refresh_cron_job 当 add_cron_job 返回 False 时记录错误"""
    mock_scheduler_mgr.get_job.return_value = None
    mock_scheduler_mgr.add_cron_job.return_value = False
    p1 = create_playlist_data("p1", "P1", [{"uri": "f1.mp3"}], schedule={"enabled": 1, "cron": "0 8 * * *"})
    playlist_mgr._playlist_raw = {"p1": p1}
    playlist_mgr._refresh_device_map()
    mock_scheduler_mgr.add_cron_job.assert_called()
    # 仅验证调用过且返回 False 时不会抛错
    playlist_mgr._scheduling.refresh_cron_job("p1", p1)


def test_refresh_cron_job_play_task_skip_when_playing(playlist_mgr):
    """定时任务触发时若列表正在播放则跳过"""
    p1 = create_playlist_data("p1", "P1", [{"uri": "f1.mp3"}], schedule={"enabled": 1, "cron": "0 8 * * *"})
    playlist_mgr._playlist_raw = {"p1": p1}
    playlist_mgr._devices["p1"] = {"obj": mock_device}
    playlist_mgr._playing_playlists.add("p1")
    mock_scheduler_mgr.get_job.return_value = None
    captured_func = []

    def capture_and_return_true(func, job_id, cron_expression):
        captured_func.append(func)
        return True

    mock_scheduler_mgr.add_cron_job.side_effect = capture_and_return_true
    playlist_mgr._scheduling.refresh_cron_job("p1", p1)
    assert len(captured_func) == 1
    captured_func[0]()  # 执行定时任务回调，内部应因 p1 在 _playing_playlists 而跳过 play
    assert "p1" in playlist_mgr._playing_playlists


def test_cleanup_play_state_without_is_playing(playlist_mgr):
    """_cleanup_play_state 当 playlist_data 无 isPlaying 时不 del"""
    p1 = create_playlist_data("p1", "P1", [{"uri": "f1.mp3"}])
    playlist_mgr._playlist_raw["p1"] = p1
    playlist_mgr._play_state["p1"] = {"in_pre_files": False, "pre_index": 0, "file_index": 0}
    assert "isPlaying" not in p1
    playlist_mgr._cleanup_play_state("p1")
    assert "p1" not in playlist_mgr._play_state


def test_update_file_duration_empty_path(playlist_mgr):
    """update_file_duration 空路径返回 None"""
    assert playlist_mgr._duration_fetcher.update_file_duration("", {"uri": ""}) is None


def test_update_file_duration_already_has_duration(playlist_mgr, monkeypatch):
    """update_file_duration 已有 duration 时直接返回不调用 get_media_duration"""
    df_globals = pm.DurationFetcher.update_file_duration.__globals__
    get_duration = MagicMock()
    monkeypatch.setitem(df_globals, "get_media_duration", get_duration)
    file_item = {"uri": "f.mp3", "duration": 10}
    ret = playlist_mgr._duration_fetcher.update_file_duration("f.mp3", file_item)
    assert ret == 10
    get_duration.assert_not_called()


def test_update_file_duration_get_returns_none(playlist_mgr, monkeypatch):
    """update_file_duration get_media_duration 返回 None 时返回 None"""
    df_globals = pm.DurationFetcher.update_file_duration.__globals__
    monkeypatch.setitem(df_globals, "get_media_duration", lambda _: None)
    file_item = {"uri": "f.mp3"}
    ret = playlist_mgr._duration_fetcher.update_file_duration("f.mp3", file_item)
    assert ret is None
    assert "duration" not in file_item or file_item.get("duration") is None


def test_collect_files_without_duration_no_blacklist(playlist_mgr):
    """collect_files_without_duration check_blacklist=False 时不过滤黑名单"""
    p1 = create_playlist_data("p1", "P1", [{"uri": "bad.mp3"}])
    playlist_mgr._duration_fetcher.blacklist["bad.mp3"] = 5
    uris = playlist_mgr._duration_fetcher.collect_files_without_duration(p1, check_blacklist=False)
    assert "bad.mp3" in uris


def test_reload_fix_pre_lists_format(playlist_mgr):
    """reload 时 pre_lists 存在但格式错误（非 list 或长度非 7）会修复"""
    raw = {
        "p1": {
            "id": "p1",
            "name": "P1",
            "files": [{
                "uri": "f1.mp3"
            }],
            "pre_lists": "invalid",
            "device": {
                "type": "dlna",
                "address": "http://p1.local"
            },
            "schedule": {
                "enabled": 0,
                "cron": ""
            },
        }
    }
    rds_mgr.set("schedule_play:playlist_collection", json.dumps(raw))
    playlist_mgr.reload()
    assert "p1" in playlist_mgr._playlist_raw
    pre_lists = playlist_mgr._playlist_raw["p1"].get("pre_lists")
    assert isinstance(pre_lists, list) and len(pre_lists) == 7


def test_trigger_button_stop_some_fail(playlist_mgr, mock_device):
    """trigger_button stop 时部分列表停止失败返回错误信息"""
    p1 = create_playlist_data("p1", "P1", [{"uri": "f1.mp3"}], trigger_button="B1")
    playlist_mgr._playlist_raw = {"p1": p1}
    playlist_mgr._devices["p1"] = {"obj": mock_device}
    playlist_mgr._playing_playlists.add("p1")
    mock_device.stop.return_value = (-1, "device error")
    code, msg = playlist_mgr.trigger_button("B1", "stop")
    assert code == -1
    assert "p1" in msg or "device error" in msg


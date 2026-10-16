"""文字提取路由。
提供链接建任务、站点列表、状态查询、下载和删除。
"""
from __future__ import annotations

import os
from typing import Any, Dict, Optional

from flask import Blueprint, request, send_file
from flask.typing import ResponseReturnValue
from pydantic import BaseModel

from core import limiter
from core.config import app_logger
from core.services.tools import video_dump_auth
from core.services.tools.video_dump_mgr import video_dump_mgr
from core.services.tools.video_dump_sites import list_sites
from core.tools.validation import parse_with_model
from core.utils import _err, _ok, read_json_from_request

log = app_logger
video_dump_bp = Blueprint('video_dump', __name__)


class _VideoDumpCreateBody(BaseModel):
    url: str


class _VideoDumpDeleteBody(BaseModel):
    task_id: Optional[str] = None
    clear_all: bool = False


class _LogoutBody(BaseModel):
    site: str


@video_dump_bp.route("/video_dump/sites", methods=['GET'])
def video_dump_sites() -> ResponseReturnValue:
    """已登记的站点。页面用来识别链接，下载器仍会尝试未登记的地址。"""
    return _ok(list_sites())


@video_dump_bp.route("/video_dump/login", methods=['GET'])
def video_dump_login_status() -> ResponseReturnValue:
    """各站点是否已在页面保存登录态。不返回 Cookie 内容。"""
    return _ok(video_dump_auth.list_login_status())


@limiter.limit("20 per minute")
@video_dump_bp.route("/video_dump/login/bilibili/qr", methods=['POST'])
def video_dump_bilibili_qr() -> ResponseReturnValue:
    """申请一张哔哩哔哩登录二维码。"""
    try:
        code, msg, data = video_dump_auth.start_bilibili_qr()
        if code != 0 or not data:
            return _err(msg)
        return _ok(data)
    except Exception as e:
        log.error(f"[文字提取] 申请 B 站二维码失败: {e}")
        return _err("申请二维码失败")


@limiter.limit("120 per minute")
@video_dump_bp.route("/video_dump/login/bilibili/poll", methods=['GET'])
def video_dump_bilibili_poll() -> ResponseReturnValue:
    """查询一次扫码状态。页面约每 2 秒调用一次。"""
    try:
        code, msg, data = video_dump_auth.poll_bilibili_qr(request.args.get("login_id", ""))
        if code != 0 or not data:
            return _err(msg)
        return _ok(data)
    except Exception as e:
        log.error(f"[文字提取] 查询 B 站扫码状态失败: {e}")
        return _err("查询扫码状态失败")


@limiter.limit("20 per minute")
@video_dump_bp.route("/video_dump/login/douyin/qr", methods=['POST'])
def video_dump_douyin_qr() -> ResponseReturnValue:
    """申请一张抖音登录二维码。"""
    try:
        code, msg, data = video_dump_auth.start_douyin_qr()
        if code != 0 or not data:
            return _err(msg)
        return _ok(data)
    except Exception as e:
        log.error(f"[文字提取] 申请抖音二维码失败: {e}")
        return _err("申请二维码失败")


@limiter.limit("120 per minute")
@video_dump_bp.route("/video_dump/login/douyin/poll", methods=['GET'])
def video_dump_douyin_poll() -> ResponseReturnValue:
    """查询一次抖音扫码状态。页面约每 2 秒调用一次。"""
    try:
        code, msg, data = video_dump_auth.poll_douyin_qr(request.args.get("login_id", ""))
        if code != 0 or not data:
            return _err(msg)
        return _ok(data)
    except Exception as e:
        log.error(f"[文字提取] 查询抖音扫码状态失败: {e}")
        return _err("查询扫码状态失败")


@video_dump_bp.route("/video_dump/login/logout", methods=['POST'])
def video_dump_logout() -> ResponseReturnValue:
    """清除页面保存的某个站点登录态。"""
    try:
        data: Dict[str, Any] = read_json_from_request()
        body, err = parse_with_model(_LogoutBody, data, err_factory=_err)
        if err or not body:
            return err or _err("Invalid request body")
        code, msg = video_dump_auth.logout(body.site)
        if code != 0:
            return _err(msg)
        return _ok({"ready": False})
    except Exception as e:
        log.error(f"[文字提取] 退出登录失败: {e}")
        return _err("退出登录失败")


@limiter.limit("10 per minute; 50 per hour")
@video_dump_bp.route("/video_dump/create", methods=['POST'])
def video_dump_create() -> ResponseReturnValue:
    """提交视频链接并开始提取。"""
    try:
        data: Dict[str, Any] = read_json_from_request()
        body, err = parse_with_model(_VideoDumpCreateBody, data, err_factory=_err)
        if err or not body:
            return err or _err("Invalid request body")

        code, msg, task_id = video_dump_mgr.submit_url(body.url)
        if code != 0 or not task_id:
            return _err(msg)

        task_info = video_dump_mgr.get_task(task_id)
        if not task_info:
            return _err("任务创建成功但无法读取任务信息")
        return _ok(task_info)
    except Exception as e:
        log.error(f"[文字提取] 创建任务失败: {e}")
        return _err(f"创建任务失败: {str(e)}")


@video_dump_bp.route("/video_dump/task/<path:task_id>", methods=['GET'])
def video_dump_task_status(task_id: str) -> ResponseReturnValue:
    """获取文字提取任务状态。"""
    try:
        task_info = video_dump_mgr.get_task(task_id)
        if not task_info:
            return _err('任务不存在')

        return _ok(task_info)

    except Exception as e:
        log.error(f"[文字提取] 获取任务状态失败: {e}")
        return _err(f"获取任务状态失败: {str(e)}")


@video_dump_bp.route("/video_dump/list", methods=['GET'])
def video_dump_list() -> ResponseReturnValue:
    """列出文字提取任务。"""
    try:
        result = video_dump_mgr.list_tasks()
        return _ok(result)

    except Exception as e:
        log.error(f"[文字提取] 列出任务失败: {e}")
        return _err(f"列出任务失败: {str(e)}")


@video_dump_bp.route("/video_dump/download/<path:task_id>", methods=['GET'])
def video_dump_download(task_id: str) -> ResponseReturnValue:
    """下载视频、字幕或纯文本。type=video|subtitle|text。"""
    try:
        file_type = request.args.get('type', 'text')
        file_path = video_dump_mgr.resolve_download(task_id, file_type)
        if not file_path:
            return _err("文件不存在")
        return send_file(file_path, as_attachment=True, download_name=os.path.basename(file_path))
    except Exception as e:
        log.error(f"[文字提取] 下载文件失败: {e}")
        return _err(f"下载文件失败: {str(e)}")


@video_dump_bp.route("/video_dump/delete", methods=['POST'])
def video_dump_delete() -> ResponseReturnValue:
    """删除文字提取任务。"""
    try:
        data: Dict[str, Any] = read_json_from_request()
        body, err = parse_with_model(_VideoDumpDeleteBody, data, err_factory=_err)
        if err or not body:
            return err or _err("Invalid request body")

        if body.clear_all:
            code, msg, stats = video_dump_mgr.clear_tasks()
            if code != 0:
                return _err(msg, stats)
            return _ok({"message": msg, **stats})

        if not body.task_id:
            return _err("task_id 不能为空")

        code, msg = video_dump_mgr.delete_task(body.task_id)
        if code != 0:
            return _err(msg)

        return _ok({"message": msg})

    except Exception as e:
        log.error(f"[文字提取] 删除任务失败: {e}")
        return _err(f"删除任务失败: {str(e)}")

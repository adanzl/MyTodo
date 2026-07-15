"""Browser 浏览器配置下发路由。
提供浏览器客户端的版本查询、配置更新和构建功能。
"""

from __future__ import annotations

from flask import Blueprint
from flask.typing import ResponseReturnValue

from core.config import Config
from core.services.browser_mgr import browser_mgr
from core.utils import _err, _ok, read_json_from_request

browser_bp = Blueprint('browser', __name__)


@browser_bp.route('/browser/version', methods=['GET'])
def get_version() -> ResponseReturnValue:
    """获取版本信息（从配置中读取）"""
    try:
        config_data = browser_mgr.load_config()
        return _ok({
            "version": config_data.get("version", ""),
            "timestamp": config_data.get("timestamp", ""),
            "env": Config.ENV,
        })
    except Exception as e:
        return _err(f'error: {str(e)}')


@browser_bp.route('/browser/config', methods=['GET'])
def get_config() -> ResponseReturnValue:
    """查询浏览器配置（查）"""
    try:
        config_data = browser_mgr.load_config()
        config_data["env"] = Config.ENV
        return _ok(config_data)
    except Exception as e:
        return _err(f'error: {str(e)}')


@browser_bp.route('/browser/config/set', methods=['POST'])
def set_config() -> ResponseReturnValue:
    """更新浏览器配置（改），合并写入"""
    try:
        json_data = read_json_from_request()
        code, msg, data = browser_mgr.update_config(json_data)
        if code != 0:
            return _err(msg)
        return _ok(data)
    except Exception as e:
        return _err(f'error: {str(e)}')


@browser_bp.route('/browser/build', methods=['POST'])
def build_browser() -> ResponseReturnValue:
    """在指定目录执行 git 放弃本地修改 + 构建脚本"""
    try:
        json_data = read_json_from_request() or {}
        build_path = json_data.get(
            'path', '/mnt/data/project/linxi-browser').strip()
        code, msg, data = browser_mgr.build(build_path)
        if code != 0:
            return _err(msg)
        return _ok(data)
    except Exception as e:
        return _err(f'error: {str(e)}')


@browser_bp.route('/browser/build/status', methods=['GET'])
def get_build_status() -> ResponseReturnValue:
    """获取构建状态和时间"""
    try:
        status = browser_mgr.get_build_status()
        return _ok(status)
    except Exception as e:
        return _err(f'error: {str(e)}')


@browser_bp.route('/browser/build/log', methods=['GET'])
def get_build_log() -> ResponseReturnValue:
    """获取构建日志内容"""
    try:
        data = browser_mgr.get_build_log()
        return _ok(data)
    except Exception as e:
        return _err(f'error: {str(e)}')


@browser_bp.route('/browser/publish', methods=['POST'])
def publish_version() -> ResponseReturnValue:
    """发布版本：自动递增 version 并更新 publishTime"""
    try:
        code, msg, data = browser_mgr.publish_version()
        if code != 0:
            return _err(msg)
        return _ok(data)
    except Exception as e:
        return _err(f'error: {str(e)}')


@browser_bp.route('/browser/build/version', methods=['POST'])
def get_latest_apk_version() -> ResponseReturnValue:
    """获取最新 APK 版本号（从构建目录的 app/build.gradle.kts 读取）"""
    try:
        json_data = read_json_from_request() or {}
        build_path = json_data.get(
            'path', '/mnt/data/project/linxi-browser').strip()
        code, msg, data = browser_mgr.get_latest_apk_version(build_path)
        if code != 0:
            return _err(msg)
        return _ok(data)
    except Exception as e:
        return _err(f'error: {str(e)}')

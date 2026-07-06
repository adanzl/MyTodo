"""Browser 浏览器配置下发路由。
提供浏览器客户端的版本查询、配置查询和配置更新功能。
"""

from __future__ import annotations

import hashlib
import json
from typing import Any, Dict

from flask import Blueprint
from flask.typing import ResponseReturnValue

import core.db.rds_mgr as rds_mgr
from core.config import app_logger, Config
from core.utils import _err, _ok, read_json_from_request

log = app_logger
browser_bp = Blueprint('browser', __name__)

_REDIS_KEY = 'browser:config'


def _load_config() -> Dict[str, Any]:
    """从 Redis 加载浏览器配置"""
    try:
        raw = rds_mgr.get_str(_REDIS_KEY)
        if raw:
            parsed = json.loads(raw)
            if isinstance(parsed, dict):
                return parsed
    except Exception as e:
        log.warning(f"[BrowserRoutes] 从 Redis 加载配置失败: {e}")
    return {}


def _save_config(config_data: Dict[str, Any]) -> bool:
    """保存浏览器配置到 Redis"""
    try:
        rds_mgr.set(_REDIS_KEY, json.dumps(config_data, ensure_ascii=False))
        return True
    except Exception as e:
        log.error(f"[BrowserRoutes] 保存配置到 Redis 失败: {e}")
        return False


@browser_bp.route('/browser/version', methods=['GET'])
def get_version() -> ResponseReturnValue:
    """获取版本信息（从配置中读取）"""
    try:
        config_data = _load_config()
        return _ok({
            "version": config_data.get("version", ""),
            "timestamp": config_data.get("timestamp", ""),
            "env": Config.ENV,
        })
    except Exception as e:
        log.error(f"[BrowserRoutes] 获取版本异常: {e}", exc_info=True)
        return _err(f'error: {str(e)}')


@browser_bp.route('/browser/config', methods=['GET'])
def get_config() -> ResponseReturnValue:
    """查询浏览器配置（查）"""
    try:
        config_data = _load_config()
        config_data["env"] = Config.ENV
        return _ok(config_data)
    except Exception as e:
        log.error(f"[BrowserRoutes] 查询配置异常: {e}", exc_info=True)
        return _err(f'error: {str(e)}')


@browser_bp.route('/browser/config/set', methods=['POST'])
def set_config() -> ResponseReturnValue:
    """更新浏览器配置（改），合并写入"""
    try:
        json_data = read_json_from_request()
        if not json_data:
            return _err('请求数据不能为空')

        current = _load_config()

        # 如果包含 admin.pin，自动 MD5 加密
        admin = json_data.get("admin")
        if isinstance(admin, dict) and "pin" in admin:
            admin = dict(admin)
            admin["pin"] = hashlib.md5(admin["pin"].encode("utf-8")).hexdigest()
            json_data["admin"] = admin

        current.update(json_data)

        if _save_config(current):
            log.info(f"[BrowserRoutes] 配置已更新: {json_data}")
            return _ok(current)
        return _err('保存配置失败')
    except Exception as e:
        log.error(f"[BrowserRoutes] 更新配置异常: {e}", exc_info=True)
        return _err(f'error: {str(e)}')


@browser_bp.route('/browser/publish', methods=['POST'])
def publish_version() -> ResponseReturnValue:
    """发布版本：自动递增 version 并更新 buildTime"""
    try:
        config_data = _load_config()

        # 语义化版本递增 patch
        raw = config_data.get("version", "0.0.0")
        parts = raw.split(".")
        try:
            major, minor, patch = (int(parts[i]) if i < len(parts) and parts[i].isdigit() else 0 for i in range(3))
            patch += 1
        except (ValueError, IndexError):
            major, minor, patch = 0, 0, 1
        config_data["version"] = f"{major}.{minor}.{patch}"

        if _save_config(config_data):
            log.info(f"[BrowserRoutes] 版本已发布: {config_data['version']}")
            return _ok({
                "version": config_data["version"],
            })
        return _err('发布版本失败')
    except Exception as e:
        log.error(f"[BrowserRoutes] 发布版本异常: {e}", exc_info=True)
        return _err(f'error: {str(e)}')

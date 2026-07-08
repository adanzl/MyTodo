"""Browser 浏览器配置与构建管理。"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import time
from typing import Any, Dict, Optional, Tuple

import core.db.rds_mgr as rds_mgr
from core.config import app_logger

log = app_logger

_REDIS_KEY = 'browser:config'
_BUILD_STATUS_KEY = 'browser:build:status'
_TS_FMT = '%Y-%m-%d %H:%M:%S'
_DEFAULT_BUILD_PATH = '/mnt/data/project/linxi-browser'


class BrowserMgr:
    """浏览器配置与构建管理类。"""

    # ---------- 配置管理 ----------

    def load_config(self) -> Dict[str, Any]:
        """从 Redis 加载浏览器配置"""
        try:
            raw = rds_mgr.get_str(_REDIS_KEY)
            if raw:
                parsed = json.loads(raw)
                if isinstance(parsed, dict):
                    return parsed
        except Exception as e:
            log.warning(f"[BrowserMgr] 从 Redis 加载配置失败: {e}")
        return {}

    def save_config(self, config_data: Dict[str, Any]) -> bool:
        """保存浏览器配置到 Redis"""
        try:
            rds_mgr.set(_REDIS_KEY, json.dumps(
                config_data, ensure_ascii=False))
            return True
        except Exception as e:
            log.error(f"[BrowserMgr] 保存配置到 Redis 失败: {e}")
            return False

    def update_config(self, json_data: Dict[str, Any]) -> Tuple[int, str, Dict[str, Any]]:
        """更新浏览器配置，返回 (code, msg, config)"""
        if not json_data:
            return -1, '请求数据不能为空', {}

        current = self.load_config()

        # 如果包含 admin.pin，自动 MD5 加密（空字符串表示清空，不加密）
        admin = json_data.get("admin")
        if isinstance(admin, dict) and "pin" in admin and admin["pin"]:
            admin = dict(admin)
            admin["pin"] = hashlib.md5(
                admin["pin"].encode("utf-8")).hexdigest()
            json_data["admin"] = admin

        json_data["timestamp"] = time.strftime(_TS_FMT)
        current.update(json_data)

        if self.save_config(current):
            log.info(f"[BrowserMgr] 配置已更新: {json_data}")
            return 0, 'ok', current
        return -1, '保存配置失败', {}

    def publish_version(self) -> Tuple[int, str, Dict[str, Any]]:
        """发布版本：自动递增 version 并更新 publishTime，返回 (code, msg, data)"""
        config_data = self.load_config()

        # 语义化版本递增 patch
        raw = config_data.get("version", "0.0.0")
        parts = raw.split(".")
        try:
            major, minor, patch = (int(parts[i]) if i < len(
                parts) and parts[i].isdigit() else 0 for i in range(3))
            patch += 1
        except (ValueError, IndexError):
            major, minor, patch = 0, 0, 1
        config_data["version"] = f"{major}.{minor}.{patch}"
        config_data["publishTime"] = time.strftime(_TS_FMT)

        if self.save_config(config_data):
            log.info(f"[BrowserMgr] 版本已发布: {config_data['version']}")
            return 0, 'ok', {"version": config_data["version"]}
        return -1, '发布版本失败', {}

    # ---------- 构建管理 ----------

    def build(self, build_path: str) -> Tuple[int, str, Dict[str, Any]]:
        """执行构建：git reset + 构建脚本，全部输出写入日志文件，后台运行"""
        if not build_path:
            return -1, '构建路径不能为空', {}

        # 检查是否已有构建在运行
        existing_pid = self._get_build_pid()
        if existing_pid and self._is_pid_alive(existing_pid):
            return -1, f'已有构建任务在运行中 (pid={existing_pid})', {}

        log_file = os.path.join(build_path, 'build.log')

        # 将整个流程包装为一个后台脚本，输出全部写入日志文件
        shell_cmd = (
            'set -e; '
            'echo "=== git checkout . ==="; '
            'git checkout . 2>&1; '
            'echo "=== git clean -fd ==="; '
            'git clean -fd 2>&1; '
            'echo "=== sh deploy/package.sh ==="; '
            'sh deploy/package.sh 2>&1'
        )

        try:
            log_f = open(log_file, 'w')
            proc = subprocess.Popen(
                ['sh', '-c', shell_cmd],
                cwd=build_path,
                stdout=log_f,
                stderr=subprocess.STDOUT,
                start_new_session=True,
            )
            pid = proc.pid
        except Exception as e:
            return -1, f'启动构建脚本失败: {e}', {}

        # 记录构建状态
        self._save_build_status({
            'status': 'building',
            'time': time.strftime(_TS_FMT),
            'path': build_path,
            'pid': pid,
            'log': log_file,
        })
        log.info(f"[BrowserMgr] 构建已启动: pid={pid}, path={build_path}")
        return 0, 'ok', {'pid': pid, 'log': log_file}

    def get_build_status(self) -> Dict[str, Any]:
        """获取构建状态，自动检测后台进程是否完成"""
        status = self._load_build_status()
        if not status:
            return status

        # 如果正在构建，检查进程是否还在
        if status.get('status') == 'building':
            pid = status.get('pid')
            if pid and self._is_pid_alive(pid):
                status['alive'] = True
            else:
                # 进程已结束，通过 waitpid 获取退出码
                status['alive'] = False
                rc = self._wait_pid(pid) if pid else -1
                log_tail = self._read_log_tail(status.get('log', ''))
                if rc == 0:
                    status['status'] = 'success'
                else:
                    status['status'] = 'failed'
                status['error'] = f'退出码: {rc}\n{log_tail}' if log_tail else f'退出码: {rc}'
                self._save_build_status(status)
        return status

    def _get_build_pid(self) -> Optional[int]:
        """获取当前构建 PID"""
        status = self._load_build_status()
        return status.get('pid')

    @staticmethod
    def _is_pid_alive(pid: int) -> bool:
        """检查进程是否存活"""
        try:
            os.kill(pid, 0)
            return True
        except (OSError, ProcessLookupError):
            return False

    @staticmethod
    def _wait_pid(pid: int) -> int:
        """通过 waitpid 获取进程退出码，回收僵尸进程"""
        try:
            _, wstatus = os.waitpid(pid, os.WNOHANG)
            if os.WIFEXITED(wstatus):
                return os.WEXITSTATUS(wstatus)
            return -1
        except ChildProcessError:
            # 进程已被回收或不是子进程
            return 0

    @staticmethod
    def _read_log_tail(log_path: str, lines: int = 10) -> str:
        """读取日志文件最后 N 行"""
        if not log_path or not os.path.isfile(log_path):
            return ''
        try:
            with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
                all_lines = f.readlines()
                return ''.join(all_lines[-lines:]).strip()
        except Exception:
            return ''

    def _save_build_status(self, data: Dict[str, Any]) -> None:
        """保存构建状态到 Redis"""
        try:
            rds_mgr.set(_BUILD_STATUS_KEY, json.dumps(
                data, ensure_ascii=False))
        except Exception as e:
            log.warning(f"[BrowserMgr] 保存构建状态失败: {e}")

    def _load_build_status(self) -> Dict[str, Any]:
        """从 Redis 加载构建状态"""
        try:
            raw = rds_mgr.get_str(_BUILD_STATUS_KEY)
            if raw:
                parsed = json.loads(raw)
                if isinstance(parsed, dict):
                    return parsed
        except Exception as e:
            log.warning(f"[BrowserMgr] 加载构建状态失败: {e}")
        return {}


# 全局单例
browser_mgr = BrowserMgr()

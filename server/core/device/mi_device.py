'''
小米设备管理
'''
# 必须在导入 miservice 之前 patch fake_useragent，避免 ThreadPoolExecutor 导致的 LoopExit
from core.device.base import DeviceBase
from core.tools.useragent_fix import patch_fake_useragent

patch_fake_useragent()

import asyncio
import hashlib
import json
import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

from aiohttp import ClientSession
from miservice import MiAccount, MiNAService
from miservice.miaccount import get_random
from miservice.miiocommand import miio_command, MiIOService


# Monkey-patch: 修复 aiohttp follow 302 后 cookie 丢失导致登录失败的问题
async def _patched_securityTokenService(self, location, nonce, ssecurity):
    import base64, hashlib
    from urllib import parse
    from yarl import URL
    nsec = "nonce=" + str(nonce) + "&" + ssecurity
    clientSign = base64.b64encode(hashlib.sha1(
        nsec.encode()).digest()).decode()
    url = location + "&clientSign=" + parse.quote(clientSign)
    async with self.session.get(url) as r:
        serviceToken = r.cookies.get("serviceToken")
        if not serviceToken:
            jar = self.session.cookie_jar.filter_cookies(URL(url))
            serviceToken = jar.get("serviceToken")
        if not serviceToken:
            raise Exception(await r.text())
        return serviceToken.value


MiAccount._securityTokenService = _patched_securityTokenService

# Monkey-patch: 修复 serviceToken 过期后清空整个 token 导致 passToken 丢失的问题
import logging as _logging

_mi_logger = _logging.getLogger("miservice")


async def _patched_mi_request(self, sid, url, data, headers, relogin=True):
    headers["User-Agent"] = self.now_ua
    if (self.token and sid in self.token) or await self.login(sid):
        cookies = {
            "userId": self.token["userId"],
            "serviceToken": self.token[sid][1],
        }
        content = data(self.token, cookies) if callable(data) else data
        method = "GET" if data is None else "POST"
        async with self.session.request(method,
                                        url,
                                        data=content,
                                        cookies=cookies,
                                        headers=headers) as r:
            status = r.status
            if status == 200:
                resp = await r.json(content_type=None)
                code = resp["code"]
                if code == 0:
                    return resp
                if "auth" in resp.get("message", "").lower():
                    status = 401
            else:
                resp = await r.text()
        if status == 401 and relogin:
            _mi_logger.warn("Auth error on request %s %s, relogin...", url,
                            resp)
            self.token.pop(
                sid, None
            )  # only remove expired sid, keep passToken for lightweight refresh
            return await self.mi_request(sid, url, data, headers, False)
    else:
        resp = "Login failed"
    raise Exception(f"Error {url}: {resp}")


MiAccount.mi_request = _patched_mi_request


# Monkey-patch: 登录失败时不要删除 token 文件，且 userId/passToken 允许缺失
#
# miservice 原始 login() 的异常分支会执行 `self.token_store.save_token()`（无参），
# 而 MiTokenStore.save_token(None) 的行为是 os.remove(token_path)，
# 即一次网络抖动或风控校验（securityStatus=16）就会把唯一的凭据文件删掉。
# 小米密码登录已普遍返回 70016（登录验证失败），passToken 是当前唯一可用通道，
# 删文件等于把自己彻底锁在门外，因此这里改为保留原文件内容。
#
# 另外 serviceLoginAuth2 的成功响应并不总带 passToken/userId（同一 MiAccount
# 实例连续登录两个 sid 时第二次就缺 passToken），原始代码的 resp["passToken"]
# 会抛 KeyError 并连带触发上面的删文件逻辑，这里改为按需写入。
async def _patched_login(self, sid):
    original_token = dict(self.token) if isinstance(self.token, dict) else None
    if not self.token:
        self.token = {"deviceId": get_random(16).upper()}
    try:
        resp = await self._serviceLogin(f"serviceLogin?sid={sid}&_json=true")
        if resp["code"] != 0:
            data = {
                "_json": "true",
                "qs": resp["qs"],
                "sid": resp["sid"],
                "_sign": resp["_sign"],
                "callback": resp["callback"],
                "user": self.username,
                "hash": hashlib.md5(self.password.encode()).hexdigest().upper(),
            }
            resp = await self._serviceLogin("serviceLoginAuth2", data)
            if resp["code"] != 0:
                raise Exception(resp)

        if resp.get("userId") is not None:
            self.token["userId"] = resp["userId"]
        if resp.get("passToken"):
            self.token["passToken"] = resp["passToken"]

        serviceToken = await self._securityTokenService(
            resp["location"], resp["nonce"], resp["ssecurity"])
        self.token[sid] = (resp["ssecurity"], serviceToken)
        if self.token_store:
            self.token_store.save_token(self.token)
        return True

    except Exception as e:
        # 只在内存里回滚，绝不删除 token 文件
        self.token = original_token
        _mi_logger.exception("Exception on login %s: %s", self.username, e)
        return False


MiAccount.login = _patched_login

from core.config import app_logger, config
from core.tools.async_util import run_async
from core.utils import convert_to_http_url, format_time_str

log = app_logger

# 从环境变量读取小米账号信息，如果没有则使用默认值
DEFAULT_MI_USERNAME = config.MI_USER
DEFAULT_MI_PASSWORD = config.MI_PASS

# Token 文件路径
TOKEN_FILE = os.path.join(str(Path.home()), ".mi.token")

print(f'Token file {TOKEN_FILE}')


def _device_to_dict(device: Dict[str, Any]) -> Dict[str, str]:
    """将 Device 对象转换为字典"""
    try:
        return {
            "address": device.get('address', ''),
            "name": device.get('name', ''),
            "deviceID": device.get('deviceID', ''),
            "presence": device.get('presence', 'offline'),
            "miotDID": device.get('miotDID', ''),
            "mac": device.get('mac', ''),
        }
    except Exception as e:
        log.error(f"[MiDevice] Error converting device: {e}")
        return {}


async def _get_device_did_async(username: str, password: str,
                                device_id: str) -> Tuple[int, str]:
    session = None
    try:
        session = ClientSession()
        account = MiAccount(session, username, password, TOKEN_FILE)
        mina_service = MiNAService(account)
        device_list = await mina_service.device_list()
        for device in device_list:
            if device['deviceID'] == device_id:
                return 0, device['miotDID']
    except Exception as e:
        log.error(f"[MiDevice] Get device did error: {e}")
    finally:
        if session:
            await session.close()
    return -1, "设备未找到"


# ========== miot 文字播报（siid=5）==========
#
# 背景：ubus 的 `mibrain.text_to_speech` 在新固件（L05C / X08A 等）会被设备静默丢弃，
# 但接口仍返回 code=0 的转发成功回执，无法据此判断是否真的出声。
# 实测可用的替代通道是 miot 动作 `Intelligent Speaker → Play Text`。
#
# 坑：Play Text 的 aiid 在不同型号上不一致（同一份 siid=5 里动作顺序不同）：
#   xiaomi.wifispeaker.l05c → aiid=3
#   xiaomi.wifispeaker.x08a → aiid=1
#   xiaomi.wifispeaker.lx06 → aiid=1
# 在 L05C 上错发 aiid=1 会命中 `Wake Up`，返回 -704220025。
# 因此 aiid 必须按型号解析，不能写死。
MIOT_INTELLIGENT_SPEAKER_SIID = 5
MIOT_PLAY_TEXT_ACTION_NAME = "Play Text"

# 已实测的型号 → aiid。未命中时会回落到 miot-spec 查询。
MIOT_PLAY_TEXT_AIID = {
    "xiaomi.wifispeaker.l05c": 3,
    "xiaomi.wifispeaker.x08a": 1,
    "xiaomi.wifispeaker.lx06": 1,
}

# 型号 → 设备型号字符串（来自 MIoT Device Information 的 Device Model 属性）
MIOT_PROP_DEVICE_MODEL = (1, 2)


async def _resolve_play_text_aiid(service: MiIOService,
                                  model: str) -> Optional[int]:
    """解析指定型号的 `Play Text` 动作 aiid。

    先查实测缓存表，未命中则查 miot-spec（miservice 内部对 spec 有本地文件缓存）。
    解析结果回填到 MIOT_PLAY_TEXT_AIID，避免重复请求。

    Args:
        service: MiIOService 实例。
        model: 设备型号，如 `xiaomi.wifispeaker.l05c`。

    Returns:
        Optional[int]: 成功返回 aiid；型号不认识时返回 None。
    """
    if model in MIOT_PLAY_TEXT_AIID:
        return MIOT_PLAY_TEXT_AIID[model]

    try:
        spec = await service.miot_spec(model, "json")
    except Exception as e:
        log.error(f"[MiDevice] Fetch spec for {model} error: {e}")
        return None

    try:
        spec_dict = json.loads(spec) if isinstance(spec, str) else spec
    except Exception as e:
        log.error(f"[MiDevice] Parse spec for {model} error: {e}")
        return None

    for service_node in (spec_dict or {}).get("services") or []:
        if service_node.get("iid") != MIOT_INTELLIGENT_SPEAKER_SIID:
            continue
        for action in service_node.get("actions") or []:
            if action.get("description") == MIOT_PLAY_TEXT_ACTION_NAME:
                aiid = action.get("iid")
                if aiid is None:
                    continue
                MIOT_PLAY_TEXT_AIID[model] = int(aiid)
                log.info(
                    f"[MiDevice] Resolved Play Text aiid for {model}: {aiid}")
                return int(aiid)

    log.error(f"[MiDevice] Play Text action not found in spec of {model}")
    return None


class MiDevice(DeviceBase):
    """小米设备管理"""
    scanning = False

    def __init__(self,
                 address: str,
                 did: str,
                 username: Optional[str] = None,
                 password: Optional[str] = None,
                 name: str = "") -> None:
        """初始化小米设备。

        Args:
            address (str): 设备 ID。
            username (Optional[str]): 小米账号用户名。如果为 None，则从配置中读取。
            password (Optional[str]): 小米账号密码。如果为 None，则从配置中读取。
            name (str): 设备名称。
        """
        super().__init__(name=name)
        self.device_id = address  # 小米设备使用 deviceID 作为地址
        self.device_did = did
        self.username = username or DEFAULT_MI_USERNAME
        self.password = password or DEFAULT_MI_PASSWORD

    @staticmethod
    async def scan_devices(
            username: Optional[str] = None,
            password: Optional[str] = None) -> List[Dict[str, str]]:
        """扫描小米设备

        Args:
            username (Optional[str]): 小米账号用户名（可选，使用默认值）
            password (Optional[str]): 小米账号密码（可选，使用默认值）

        Returns:
            List[Dict[str, str]]: 设备列表
        """
        if MiDevice.scanning:
            log.warning("[MiDevice] Already scanning")
            return []

        username = username or DEFAULT_MI_USERNAME
        password = password or DEFAULT_MI_PASSWORD

        # 验证账号密码是否设置
        if not username or not password:
            error_msg = "小米账号或密码未设置，请设置环境变量 MI_USER 和 MI_PASS"
            log.error(f"[MiDevice] {error_msg}")
            return []

        try:
            MiDevice.scanning = True
            log.info(
                f"[MiDevice] Starting scan with username: {username[:3]}***")
            async with ClientSession() as session:
                account = MiAccount(
                    session,
                    username,
                    password,
                    TOKEN_FILE,
                )
                mina_service = MiNAService(account)
                result = await mina_service.device_list()
                # log.info(f"[MiDevice] Device list: {result}")
                device_list = [_device_to_dict(device) for device in result]
                log.info(f"[MiDevice] Found {len(device_list)} devices")
            return device_list

        except Exception as e:
            # 捕获 gevent LoopExit 异常（可能由 fake_useragent 的线程池操作引起）
            import gevent
            if isinstance(e, gevent.exceptions.LoopExit):
                log.warning(f"[MiDevice] Scan: gevent LoopExit (可忽略)")
                return []

            # 检查是否是登录失败
            error_str = str(e)
            if "Login failed" in error_str or "登录验证失败" in error_str or "70016" in error_str:
                log.error(f"[MiDevice] 登录验证失败，请检查账号密码是否正确。错误: {e}")
            else:
                log.error(f"[MiDevice] Scan error: {e}")
            return []
        finally:
            MiDevice.scanning = False

    def _create_account(self, session: ClientSession) -> MiAccount:
        return MiAccount(session, self.username, self.password, TOKEN_FILE)

    # ========== 统一设备接口 ==========
    def play(self, url: str) -> Tuple[int, str]:
        """在小米设备上播放指定的媒体 URL。

        Args:
            url (str): 媒体文件的 URL，会自动转换为 HTTP URL。

        Returns:
            Tuple[int, str]: (code, msg)。code=0 表示成功。
        """

        async def _play_async():
            session = None
            try:
                media_url = convert_to_http_url(url)
                # 获取 MiNAService 对象
                session = ClientSession()
                account = self._create_account(session)
                mina_service = MiNAService(account)
                await mina_service.play_by_url(self.device_id, media_url)
                return 0, "ok"
            except Exception as e:
                # 捕获 gevent LoopExit 异常（可能由 fake_useragent 的线程池操作引起）
                import gevent
                if isinstance(e, gevent.exceptions.LoopExit):
                    log.warning(
                        f"[MiDevice] Play: gevent LoopExit (可忽略), 重试播放")
                    # 重试一次
                    try:
                        await mina_service.play_by_url(self.device_id,
                                                       media_url)
                        return 0, "ok"
                    except Exception as e2:
                        log.error(f"[MiDevice] Play retry error: {e2}")
                        return -1, f"播放失败: {str(e2)}"

                error_str = str(e)
                if "Login failed" in error_str or "登录验证失败" in error_str or "70016" in error_str:
                    log.error(f"[MiDevice] 登录验证失败，请检查账号密码是否正确: {e}")
                    return -1, "登录验证失败，请检查账号密码是否正确"

                log.error(f"[MiDevice] Play error: {e}")
                return -1, f"播放失败: {str(e)}"
            finally:
                if session:
                    await session.close()

        try:
            return run_async(_play_async(), timeout=20.0)
        except Exception as e:
            # 捕获 gevent LoopExit 异常
            import gevent
            if isinstance(e, gevent.exceptions.LoopExit):
                log.warning(f"[MiDevice] Play: gevent LoopExit (可忽略)")
                return -1, "播放失败: gevent LoopExit"
            log.error(f"[MiDevice] Play error: {e}")
            return -1, f"播放失败: {str(e)}"

    async def _login_xiaomiio(
            self, force_refresh: bool = False
    ) -> Tuple[Optional[MiAccount], Optional[ClientSession], str]:
        """准备一个可用的 xiaomiio 账号（miot 通道凭据）。

        miot 动作走 api.io.mi.com，需要 `xiaomiio` 的 serviceToken，它与
        `micoapi` 的 token 相互独立。实测约束：

        - token 文件里已有的 `xiaomiio` serviceToken 可以直接用，不必重新登录；
        - 主动 `login("xiaomiio")` 反而经常失败：`serviceLogin` 返回 70016，
          走密码通道后 `serviceLoginAuth2` 虽 code=0 但带 `securityStatus: 16`
          且响应里没有 `nonce`/`ssecurity`，触发 `KeyError: 'nonce'`；
        - 只有 token 文件里缺 `xiaomiio`（或服务端已判定过期）时才需要先刷
          `micoapi` 的 passToken，再换新 session 登 `xiaomiio`
          （同一 MiAccount 实例连续登两个 sid 会失败）。

        Args:
            force_refresh (bool): 为 True 时跳过缓存，强制刷新凭据。
                调用方在收到 `Login failed` 后用它做一次重试。

        Returns:
            Tuple[MiAccount|None, ClientSession|None, str]:
                (账号, 需要调用方关闭的 session, 错误信息)。
        """
        # 快路径：直接复用 token 文件里的 xiaomiio serviceToken
        if not force_refresh:
            session = ClientSession()
            account = self._create_account(session)
            if account.token and "xiaomiio" in account.token:
                return account, session, ""
            await session.close()

        # 慢路径：先刷 micoapi 的 passToken（会落盘），再另开实例登 xiaomiio
        session = ClientSession()
        try:
            refresh_account = self._create_account(session)
            if not await refresh_account.login("micoapi"):
                return None, None, "登录验证失败，请检查账号密码是否正确"
        except Exception as e:
            log.error(f"[MiDevice] Speak: micoapi refresh error: {e}")
            return None, None, f"刷新凭据失败: {str(e)}"
        finally:
            await session.close()

        session = ClientSession()
        try:
            account = self._create_account(session)
            if await account.login("xiaomiio"):
                return account, session, ""
        except Exception as e:
            log.error(f"[MiDevice] Speak: xiaomiio login error: {e}")
        await session.close()
        return None, None, "miot 通道登录失败，请重新获取 ~/.mi.token"

    def speak(self, text: str) -> Tuple[int, str]:
        """让小爱音箱播报指定文字。

        走 miot 动作通道（`Intelligent Speaker → Play Text`）。不用 ubus 的
        `mibrain.text_to_speech`，因为后者在新固件上会被设备静默丢弃，接口却
        仍返回转发成功，无法据此判断是否真的出声。

        token 里的 `xiaomiio` serviceToken 会过期，届时 miot 请求返回
        `Login failed`；这种情况下强制刷新一次凭据再重试，避免必须重启进程。

        Args:
            text (str): 要播报的文本。

        Returns:
            Tuple[int, str]: (code, msg)。code=0 表示设备已接受播报请求。
        """
        text = (text or "").strip()
        if not text:
            return -1, "text is required"

        async def _attempt(force_refresh: bool) -> Tuple[int, str]:
            account, session, err = await self._login_xiaomiio(force_refresh)
            if account is None:
                return -1, err

            try:
                service = MiIOService(account)

                # 解析型号 → Play Text aiid（各型号动作顺序不同，不能写死）
                configs = await service.miot_get_props(
                    self.device_did, [MIOT_PROP_DEVICE_MODEL])
                model = configs[0] if configs else None
                if not model:
                    return -1, "无法获取设备型号"

                aiid = await _resolve_play_text_aiid(service, model)
                if aiid is None:
                    return -1, f"型号 {model} 不支持文字播报"

                code = await service.miot_action(self.device_did,
                                                 [MIOT_INTELLIGENT_SPEAKER_SIID, aiid],
                                                 [text])
                if code != 0:
                    log.error(
                        f"[MiDevice] Speak action failed: code={code}, model={model}, aiid={aiid}"
                    )
                    return -1, f"播报失败: miot 返回 {code}"

                log.info(
                    f"[MiDevice] Speak ok: model={model}, aiid={aiid}, text={text[:20]}"
                )
                return 0, "播报成功"
            except Exception as e:
                error_str = str(e)
                if "Login failed" in error_str or "登录验证失败" in error_str or "70016" in error_str:
                    # code=-2 表示「凭据可能只是过期」，调用方可强制刷新后重试
                    log.error(f"[MiDevice] 登录验证失败，请检查账号密码是否正确: {e}")
                    return -2, "登录验证失败，请检查账号密码是否正确"
                log.error(f"[MiDevice] Speak error: {e}")
                return -1, f"播报失败: {str(e)}"
            finally:
                await session.close()

        async def _speak_async() -> Tuple[int, str]:
            code, msg = await _attempt(force_refresh=False)
            if code in (0, -1):
                return code, msg

            # 缓存的 xiaomiio serviceToken 过期：强制刷新一次再重试
            log.warning("[MiDevice] Speak: xiaomiio token 可能已失效，强制刷新后重试")
            return await _attempt(force_refresh=True)

        try:
            return run_async(_speak_async(), timeout=20.0)
        except Exception as e:
            import gevent
            if isinstance(e, gevent.exceptions.LoopExit):
                log.warning(f"[MiDevice] Speak: gevent LoopExit (可忽略)")
                return -1, "播报失败: gevent LoopExit"
            log.error(f"[MiDevice] Speak error: {e}")
            return -1, f"播报失败: {str(e)}"

    def stop(self) -> Tuple[int, str]:
        """停止小米设备上的播放。

        Returns:
            Tuple[int, str]: (code, msg)。code=0 表示成功。
        """

        async def _stop_async():
            session = None
            try:
                # 获取 MiNAService 对象
                session = ClientSession()
                account = self._create_account(session)
                mina_service = MiNAService(account)
                # HTTP 流场景下单次 pause/stop 常假成功，连续发两次提高停下概率
                await mina_service.player_pause(self.device_id)
                await mina_service.player_stop(self.device_id)
                await asyncio.sleep(0.4)
                try:
                    await mina_service.player_pause(self.device_id)
                    await mina_service.player_stop(self.device_id)
                except Exception as e2:
                    log.warning(f"[MiDevice] Stop second pass ignored: {e2}")
                return 0, "ok"
            except Exception as e:
                error_str = str(e)
                if "Login failed" in error_str or "登录验证失败" in error_str or "70016" in error_str:
                    log.error(f"[MiDevice] 登录验证失败，请检查账号密码是否正确: {e}")
                    return -1, "登录验证失败，请检查账号密码是否正确"
                log.error(f"[MiDevice] Stop error: {e}")
                return -1, f"停止失败: {str(e)}"
            finally:
                if session:
                    await session.close()

        try:
            return run_async(_stop_async(), timeout=10.0)
        except Exception as e:
            log.error(f"[MiDevice] Stop error: {e}")
            return -1, f"停止失败: {str(e)}"

    def get_status(self) -> Tuple[int, Dict[str, Any]]:
        """获取小米设备的播放状态。

        Returns:
            Tuple[int, Dict[str, Any]]: (code, status_dict)。code=0 表示成功。
        """

        async def _get_status_async():
            session = None
            try:
                # 获取 MiNAService 对象
                session = ClientSession()
                account = self._create_account(session)
                _service = MiIOService(account)
                result = await miio_command(_service, self.device_did,
                                            '2-1,3-1,3-2')
                volume = result[0]  # 获取音量，确保始终有音量值
                state = 'PLAYING' if result[1] == 1 else 'STOPPED'
                state_code = result[1]
                return 0, {
                    "state": state,
                    "state_code": state_code,
                    "status": 'OK',
                    "track": 0,
                    "duration": "00:00:00",
                    "position": "00:00:00",
                    "volume": volume  # 确保音量始终返回
                }
            # try:
            #     # 获取 MiNAService 对象
            #     session = ClientSession()
            #     account = self._create_account(session)
            #     mina_service = MiNAService(account)
            #     ret = await mina_service.player_get_status(self.device_id)
            #     if ret['code'] != 0:
            #         return -1, {"error": ret['message']}
            #     log.info(f"[MiDevice] Get status: {ret}")
            #     info = json.loads(ret['data']['info'])
            #     state = 'STOPPED' if info.get('status') == 2 else 'PLAYING'
            #     state_code = info.get('status')
            #     volume = info.get('volume', 0)  # 获取音量，确保始终有音量值

            #     # 安全访问 play_song_detail，如果不存在或为空则返回基本状态（包含音量）
            #     play_song_detail = info.get('play_song_detail')
            #     if not play_song_detail or not isinstance(play_song_detail, dict) or len(play_song_detail) == 0:
            #         # 如果没有播放详情，返回基本状态（确保包含音量）
            #         return 0, {
            #             "state": state,
            #             "state_code": state_code,
            #             "status": 'OK',
            #             "track": 0,
            #             "duration": "00:00:00",
            #             "position": "00:00:00",
            #             "volume": volume  # 确保音量始终返回
            #         }

            #     duration = format_time_str(play_song_detail['duration'] /
            #                                1000) if play_song_detail.get('duration') else '00:00:00'
            #     track_list = info.get('track_list', [])
            #     audio_id = play_song_detail.get('audio_id')
            #     position = play_song_detail.get('position', 0)  # 播放位置 单位：毫秒

            #     track = 0
            #     if audio_id and track_list:
            #         try:
            #             track = track_list.index(audio_id) + 1
            #         except ValueError:
            #             track = 0

            #     return 0, {
            #         "state": state,  # PLAYING, STOPPED
            #         "state_code": state_code,
            #         "status": 'OK',  # OK, ERROR
            #         "track": track,  # 当前曲目索引（从1开始）
            #         "duration": duration,  # 总时长，格式如 "00:03:45"
            #         "position": format_time_str(position / 1000),  # 已播放时长，格式如 "00:01:30"
            #         "volume": volume  # 音量
            #     }
            except Exception as e:
                error_str = str(e)
                if "Login failed" in error_str or "登录验证失败" in error_str or "70016" in error_str:
                    log.error(f"[MiDevice] 登录验证失败，请检查账号密码是否正确: {e}")
                    return -1, {"error": "登录验证失败，请检查账号密码是否正确"}
                log.error(f"[MiDevice] Get status error: {e}")
                return -1, {"error": f"获取播放状态信息失败: {str(e)}"}
            finally:
                if session:
                    await session.close()

        try:
            return run_async(_get_status_async(), timeout=5.0)
        except Exception as e:
            log.error(f"[MiDevice] Get status error: {e}")
            return -1, {"error": f"获取播放状态信息失败: {str(e)}"}

    # ========== 设备功能接口 ==========
    def get_volume(self) -> Tuple[int, int]:
        """获取小米设备的音量。

        Returns:
            Tuple[int, int]: (code, volume)。code=0 表示成功。
        """

        async def _get_volume_async():
            session = None
            try:
                # 获取 MiNAService 对象
                session = ClientSession()
                account = self._create_account(session)
                _service = MiIOService(account)
                result = await miio_command(_service, self.device_did, '2-1')
                return 0, result[0]
            except Exception as e:
                error_str = str(e)
                if "Login failed" in error_str or "登录验证失败" in error_str or "70016" in error_str:
                    log.error(f"[MiDevice] 登录验证失败，请检查账号密码是否正确: {e}")
                    return -1, {"error": "登录验证失败，请检查账号密码是否正确"}
                log.error(f"[MiDevice] Get status error: {e}")
                return -1, {"error": f"获取播放状态信息失败: {str(e)}"}
            finally:
                if session:
                    await session.close()

        try:
            return run_async(_get_volume_async(), timeout=5.0)
        except Exception as e:
            log.error(f"[MiDevice] Get volume error: {e}")
            return -1, {"error": f"获取音量失败: {str(e)}"}

    def set_volume(self, volume: int) -> Tuple[int, str]:
        """设置小米设备的音量。

        Args:
            volume (int): 目标音量。

        Returns:
            Tuple[int, str]: (code, msg)。code=0 表示成功。
        """

        async def _set_volume_async():
            session = None
            try:
                # 获取 MiNAService 对象
                session = ClientSession()
                account = self._create_account(session)
                mina_service = MiNAService(account)
                await mina_service.player_set_volume(self.device_id, volume)
                return 0, "ok"
            except Exception as e:
                error_str = str(e)
                if "Login failed" in error_str or "登录验证失败" in error_str or "70016" in error_str:
                    log.error(f"[MiDevice] 登录验证失败，请检查账号密码是否正确: {e}")
                    return -1, "登录验证失败，请检查账号密码是否正确"
                log.error(f"[MiDevice] Set volume error: {e}")
                return -1, f"设置音量失败: {str(e)}"
            finally:
                if session:
                    await session.close()

        try:
            return run_async(_set_volume_async(), timeout=5.0)
        except Exception as e:
            log.error(f"[MiDevice] Set volume error: {e}")
            return -1, -1

    def get_device_did(self) -> Tuple[int, str]:
        """获取小米设备的设备ID。

        Returns:
            Tuple[int, str]: (code, did)。code=0 表示成功。
        """
        try:
            if self.device_did is None:
                code, self.device_did = run_async(_get_device_did_async(
                    self.username, self.password, self.device_id),
                                                  timeout=5.0)
                if code != 0:
                    return code, "设备未找到"
            return 0, self.device_did
        except Exception as e:
            log.error(f"[MiDevice] Get device did error: {e}")
            return -1, "设备未找到"


# 同步包装函数（用于在Flask路由中使用）


def scan_devices_sync(timeout: float = 5.0) -> List[Dict[str, str]]:
    """同步扫描设备"""
    try:
        username = os.getenv("MI_USER", DEFAULT_MI_USERNAME)
        password = os.getenv("MI_PASS", DEFAULT_MI_PASSWORD)
        return run_async(MiDevice.scan_devices(username, password),
                         timeout=timeout + 2.0)
    except asyncio.TimeoutError:
        log.error(f"[MiDevice] Scan timeout after {timeout + 2.0}s")
        return []
    except Exception as e:
        log.error(f"[MiDevice] Scan error: {e}")
        return []

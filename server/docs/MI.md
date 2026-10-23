# 小米模块

## 小米服务命令行

<https://github.com/Yonsm/MiService>

### 安装

    /opt/miniconda3/bin/python3 -m pip install -U pip setuptools wheel
    /opt/miniconda3/bin/python3 -m pip install aiofiles aiohttp
    /opt/miniconda3/bin/python3 -m pip install --no-build-isolation miservice

### 激活环境

#### conda

`conda activate flask_env`

#### env

`while IFS= read -r line; do line=$(echo "$line" | sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//'); [[ -z "$line" || "$line" =~ ^# ]] && continue; line=${line%%#*}; [[ -n "$line" && "$line" =~ = ]] && eval "export $line"; done < .env`

### 查询命令

#### 查询设备

所有 `micli list`

只要音箱，查看3行  `micli list | grep -A3 音箱`

    "name": "小爱音箱Play增强版",
    "model": "xiaomi.wifispeaker.l05c",
    "did": "982124869",
    "token": "1d2412b5bcb22a867393f7146ba29e2f"

设置DID export MI_DID=982124869

#### 查询设备的接口文档

`micli spec xiaomi.wifispeaker.l05c`

数字查询的命令支持批量 如 micli 1,2,3 ，返回则是数组

#### 查询设备音量

`micli 2-1`

#### 查询设备播放状态

`micli 3-1`

### 设置命令

#### 设置音量

`micli 2=#20`

    参数类型要根据接口描述文档来确定:
    #是强制文本类型，还可以用单引号'和双引号"来强制文本类型'（可单个引号，也可以两个）;
    如果不强制文本类型，默认将检测类型；可能的检测结果是 JSON 的 null、false、true、整数、浮点数或者文本

## 凭据文件 `~/.mi.token`

`micli` 和 `server/core/device/mi_device.py` 读的都是 `~/.mi.token`（同一个文件，含 `passToken`）。
该文件**不进 git**（已在 `server/.gitignore` 忽略）。

### 密码登录已经不可用

小米账号密码登录目前稳定返回：

```
{'code': 70016, 'description': '登录验证失败'}
```

`serviceLoginAuth2` 偶尔能过（`securityStatus: 16`），但多数情况下直接拒绝。因此
**唯一可用通道是 token 文件里的 `passToken`**。丢失 `passToken` 就只能重新抓取。

### 刷新 token

`passToken` 会在每次 `login` 时**轮换**，并立即写回文件；旧 `passToken` 仍可继续使用一段时间。
正常情况下不需要手动刷新 —— 应用里每次调用 `login()` 都会顺手刷新并落盘。

需要手动重新生成时：

1. 造一个只含 `deviceId` 的骨架文件：

   ```
   echo '{"deviceId": "OYP2VXSE79U4KKZO"}' > ~/.mi.token
   ```

2. 跑一次任意 micli 命令（会走密码登录并写入新 `passToken`）：

   ```
   cd server && set -a && . ./.env && set +a
   ./venv/bin/python -m miservice list
   ```

3. 检查结果：

   ```
   python3 -c "import json;d=json.load(open('$HOME/.mi.token'));print(list(d.keys()), len(d.get('passToken','')))"
   ```

   成功时 keys 应包含 `deviceId/userId/passToken/micoapi`，`passToken` 长度约 347。

注意：

- **文件完全为空时密码登录会失败，而且 miservice 会把文件删掉**。骨架文件里至少要保留 `deviceId`。
- 若 `serviceLoginAuth2` 返回 `securityStatus: 16` 且带 `notificationUrl`，说明触发了二次身份验证，需要先在小米账号侧完成验证再重试。
- 本项目已 monkey-patch `MiAccount.login`，**登录失败不再删除 token 文件**（原实现会 `os.remove`）。

### 不要主动重登 `xiaomiio`

miot 通道（播报、读属性）走 `api.io.mi.com`，用的是 token 文件里 `xiaomiio` 这一项的
`serviceToken`。实测：

- **直接复用文件里已有的 `xiaomiio` serviceToken 可以正常工作**，不需要 `login("xiaomiio")`；
- 主动 `login("xiaomiio")` 反而经常失败：`serviceLogin` 返回 70016，退回密码通道后
  `serviceLoginAuth2` 虽 `code=0` 却带 `securityStatus: 16`，响应里没有
  `nonce`/`ssecurity`，抛 `KeyError: 'nonce'` 并让 `login()` 返回 False；
- 同一个 `MiAccount` 实例上连续登两个 sid（micoapi → xiaomiio）第二次会缺 `passToken`。

因此 `MiDevice._login_xiaomiio()` 的策略是：**能复用就复用**；只有文件里根本没有
`xiaomiio` 时才先刷 `micoapi` 的 passToken，再另开 session 登 `xiaomiio`。
miot 请求返回 `Login failed`（serviceToken 过期）时，会带 `force_refresh=True` 重试一次。

### 播报通道与 aiid

小爱文字播报走 miot 动作 `Intelligent Speaker → Play Text`（`siid=5`）。该动作的 `aiid`
**因型号而异**（同一 `siid` 下动作顺序不同）：

| 型号 | Play Text 的 aiid |
| --- | --- |
| `xiaomi.wifispeaker.l05c` | 3 |
| `xiaomi.wifispeaker.x08a` | 1 |
| `xiaomi.wifispeaker.lx06` | 1 |

错发 aiid 会命中别的动作（例如 L05C 上 `aiid=1` 是 `Wake Up`），返回 `-704220025`。
`core/device/mi_device.py` 的 `MIOT_PLAY_TEXT_AIID` 存已实测型号，未命中时会查
`micli spec <model>` 对应的 miot-spec 自动解析并缓存。

不要用 ubus 的 `mibrain.text_to_speech`：新固件会静默丢弃，接口却返回转发成功（假成功）。

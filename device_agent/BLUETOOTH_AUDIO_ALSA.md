# 蓝牙音频播放指南（ALSA 方式，无 PulseAudio）

## 概述

本文档说明如何在不使用 PulseAudio 的情况下，通过蓝牙设备播放音频。我们使用 **ALSA + bluez-alsa** 方案。

## 系统要求

### 必需软件包

```bash
# 基础音频系统
sudo apt-get install alsa-utils

# 蓝牙音频支持
sudo apt-get install bluez bluez-alsa bluealsa

# 音频播放器（推荐 mpg123）
sudo apt-get install mpg123

# 可选：其他播放器
sudo apt-get install ffmpeg  # 提供 ffplay
```

## 架构说明

### 音频路径

```
音频文件 → mpg123 → ALSA → bluez-alsa → 蓝牙设备
```

不再需要 PulseAudio 中间层，直接使用 ALSA + bluez-alsa。

### bluez-alsa 工作原理

1. **bluealsa** 服务监听蓝牙音频设备
2. 为每个连接的蓝牙音频设备创建 ALSA PCM 设备
3. 应用程序通过 ALSA 接口播放音频到蓝牙设备

## 配置步骤

### 1. 安装 bluez-alsa

```bash
# 安装 bluez-alsa
sudo apt-get install bluez-alsa bluealsa

# 启动 bluealsa 服务
sudo systemctl enable bluealsa
sudo systemctl start bluealsa

# 检查服务状态
systemctl status bluealsa
```

### 2. 连接蓝牙设备

```bash
# 启动 bluetoothctl
bluetoothctl

# 在 bluetoothctl 中执行
power on
scan on
# 等待发现设备...
pair <MAC_ADDRESS>
connect <MAC_ADDRESS>
trust <MAC_ADDRESS>
```

### 3. 验证 ALSA 蓝牙设备

```bash
# 列出所有 ALSA 设备
aplay -L | grep bluealsa

# 应该看到类似输出：
# bluealsa:DEV=58:EA:1F:1A:9A:8B,PROFILE=a2dp
# bluealsa:DEV=58:EA:1F:1A:9A:8B,PROFILE=sco
```

### 4. 测试播放

```bash
# 使用 mpg123 播放到蓝牙设备
mpg123 -a bluealsa /path/to/music.mp3

# 或指定完整设备名
mpg123 -a bluealsa:DEV=58:EA:1F:1A:9A:8B,PROFILE=a2dp /path/to/music.mp3

# 使用 aplay 播放 WAV 文件
aplay -D bluealsa /path/to/sound.wav
```

## API 使用

### 1. 播放音频到蓝牙设备

**接口**: `POST /media/playDir`

**功能**: 自动检测蓝牙设备并播放音频

**请求参数**:
```json
{
  "path": "/mnt/music",
  "device_address": "58:EA:1F:1A:9A:8B"
}
```

**工作流程**:
1. 连接指定的蓝牙设备（或使用已连接的设备）
2. 查找对应的 bluealsa ALSA 设备
3. 使用 mpg123 播放音频到该设备

**响应示例**:
```json
{
  "code": 0,
  "msg": "ok",
  "data": {
    "directory": "/mnt/music",
    "bluetooth_device": {
      "address": "58:EA:1F:1A:9A:8B",
      "name": "小爱音箱-7324",
      "connected": true
    },
    "media_files": [...],
    "total_files": 5,
    "play_results": [
      {
        "file": "music.mp3",
        "result": {
          "code": 0,
          "msg": "Playing",
          "file": "music.mp3",
          "pid": 12345
        }
      }
    ]
  }
}
```

**cURL 示例**:
```bash
curl -X POST http://localhost:5000/media/playDir \
  -H "Content-Type: application/json" \
  -d '{
    "path": "/mnt/music",
    "device_address": "58:EA:1F:1A:9A:8B"
  }'
```

### 2. 停止播放

**接口**: `POST /media/stop`

**功能**: 停止当前正在播放的音频

**响应示例**:
```json
{
  "code": 0,
  "msg": "Playback stopped"
}
```

**cURL 示例**:
```bash
curl -X POST http://localhost:5000/media/stop
```

### 3. 获取音频设备列表

**接口**: `GET /media/getAudioDevices`

**功能**: 获取所有可用的 ALSA 音频设备

**响应示例**:
```json
{
  "code": 0,
  "msg": "ok",
  "data": {
    "devices": [
      {
        "name": "default",
        "description": "Default Audio Device",
        "is_bluetooth": false
      },
      {
        "name": "bluealsa:DEV=58:EA:1F:1A:9A:8B,PROFILE=a2dp",
        "description": "Bluetooth Audio Device",
        "is_bluetooth": true
      }
    ],
    "total": 2,
    "bluetooth_devices": [
      {
        "name": "bluealsa:DEV=58:EA:1F:1A:9A:8B,PROFILE=a2dp",
        "description": "Bluetooth Audio Device",
        "is_bluetooth": true
      }
    ]
  }
}
```

**cURL 示例**:
```bash
curl http://localhost:5000/media/getAudioDevices
```

## 播放器选择

### 优先级

系统会按以下顺序尝试播放：

1. **mpg123** (推荐) - 轻量级，支持指定 ALSA 设备
2. **pygame** (回退) - 如果 mpg123 不可用

### mpg123 优势

- ✅ 支持直接指定 ALSA 设备
- ✅ 轻量级，资源占用少
- ✅ 稳定可靠
- ✅ 支持多种音频格式

### 使用 mpg123

```bash
# 基本用法
mpg123 file.mp3

# 指定 ALSA 设备
mpg123 -a bluealsa file.mp3

# 指定完整的 bluealsa 设备
mpg123 -a "bluealsa:DEV=58:EA:1F:1A:9A:8B,PROFILE=a2dp" file.mp3

# 后台播放
mpg123 -a bluealsa file.mp3 &

# 停止播放
killall mpg123
```

## Python 客户端示例

### 自动播放

```python
import requests

# 播放音频到蓝牙设备
response = requests.post(
    'http://localhost:5000/media/playDir',
    json={
        'path': '/mnt/music',
        'device_address': '58:EA:1F:1A:9A:8B'
    }
)

result = response.json()
if result['code'] == 0:
    print(f"正在播放: {result['data']['play_results'][0]['file']}")
    print(f"蓝牙设备: {result['data']['bluetooth_device']['name']}")
else:
    print(f"播放失败: {result['msg']}")
```

### 检查可用设备

```python
import requests

# 获取所有音频设备
response = requests.get('http://localhost:5000/media/getAudioDevices')
data = response.json()

if data['code'] == 0:
    devices = data['data']['devices']
    bluetooth_devices = data['data']['bluetooth_devices']
    
    print(f"总设备数: {len(devices)}")
    print(f"蓝牙设备数: {len(bluetooth_devices)}")
    
    for device in bluetooth_devices:
        print(f"- {device['name']}")
        print(f"  {device['description']}")
```

## 故障排查

### 问题 1: bluealsa 服务未运行

**症状**: 找不到 bluealsa 设备

**解决方案**:
```bash
# 检查服务状态
systemctl --user status bluealsa
# 或
sudo systemctl status bluealsa

# 启动服务
systemctl --user start bluealsa
# 或
sudo systemctl start bluealsa

# 设置开机自启
systemctl --user enable bluealsa
```

### 问题 2: 找不到蓝牙设备

**症状**: `aplay -L` 中没有 bluealsa 设备

**排查步骤**:

1. 确认蓝牙设备已连接：
```bash
bluetoothctl paired-devices
bluetoothctl info 58:EA:1F:1A:9A:8B
```

2. 检查设备是否支持 A2DP：
```bash
bluetoothctl info 58:EA:1F:1A:9A:8B | grep -i a2dp
```

3. 重启 bluealsa 服务：
```bash
sudo systemctl restart bluealsa
```

4. 重新连接蓝牙设备

### 问题 3: mpg123 未安装

**症状**: 返回 "mpg123 not installed"

**解决方案**:
```bash
sudo apt-get install mpg123
```

### 问题 4: 音频播放卡顿

**可能原因**:
- 蓝牙信号弱
- 系统资源不足
- 音频格式不支持

**解决方案**:

1. 改善蓝牙信号质量：
   - 缩短设备距离
   - 减少障碍物

2. 检查系统资源：
```bash
top
free -h
```

3. 转换音频格式：
```bash
# 转换为更兼容的格式
ffmpeg -i input.flac -acodec mp3 -ab 192k output.mp3
```

### 问题 5: 权限问题

**症状**: "Permission denied" 错误

**解决方案**:
```bash
# 将用户添加到 audio 和 bluetooth 组
sudo usermod -a -G audio $USER
sudo usermod -a -G bluetooth $USER

# 重新登录生效
```

### 问题 6: 多个蓝牙设备冲突

**症状**: 连接了多个蓝牙设备时音频播放到错误的设备

**解决方案**:
- 在 API 请求中明确指定 `device_address`
- 断开不需要的蓝牙设备

## 配置文件

### bluealsa 配置

编辑 `/etc/bluealsa/bluealsa.conf` (如果存在):

```conf
# 启用 A2DP sink（音频输出）
enable-a2dp-sink = yes

# 启用 A2DP source（音频输入）
enable-a2dp-source = no

# 音频质量设置
a2dp-volume = 127
```

### ALSA 配置

编辑 `~/.asoundrc` 或 `/etc/asound.conf`:

```conf
# 设置 bluealsa 为默认设备（可选）
defaults.bluealsa.service "org.bluealsa"
defaults.bluealsa.device "58:EA:1F:1A:9A:8B"
defaults.bluealsa.profile "a2dp"

pcm.!default {
    type plug
    slave.pcm {
        type bluealsa
        device "58:EA:1F:1A:9A:8B"
        profile "a2dp"
    }
}
```

## 对比：ALSA vs PulseAudio

| 特性 | ALSA + bluez-alsa | PulseAudio |
|------|-------------------|------------|
| 资源占用 | 低 | 中等 |
| 配置复杂度 | 中等 | 简单 |
| 音频延迟 | 较低 | 中等 |
| 设备切换 | 需要手动指定 | 自动 |
| 系统依赖 | 少 | 多 |
| 适用场景 | 嵌入式、资源受限 | 桌面环境 |

## 命令速查表

```bash
# 安装必需软件
sudo apt-get install alsa-utils bluez bluez-alsa bluealsa mpg123

# 启动服务
sudo systemctl start bluealsa

# 连接蓝牙设备
bluetoothctl connect 58:EA:1F:1A:9A:8B

# 查看 ALSA 设备
aplay -L | grep bluealsa

# 播放测试
mpg123 -a bluealsa /path/to/music.mp3

# 停止播放
killall mpg123

# 查看 bluealsa 日志
journalctl -u bluealsa -f
```

## 最佳实践

1. **开机自启动**: 设置 bluealsa 服务开机自启动
2. **设备信任**: 对常用设备执行 `trust` 命令，确保自动连接
3. **音频格式**: 使用 MP3 格式以获得最佳兼容性
4. **错误处理**: 在播放前检查蓝牙设备连接状态
5. **资源管理**: 播放结束后及时停止进程

## 注意事项

1. **音频延迟**: 蓝牙音频有固有延迟（100-300ms），不适合需要精确同步的场景
2. **音频格式**: 不是所有格式都被所有蓝牙设备支持
3. **设备兼容性**: 确保蓝牙设备支持 A2DP 配置
4. **进程管理**: mpg123 以独立进程运行，需要妥善管理
5. **并发播放**: 同一时间只能播放一个音频文件

## 更新日志

### 2025-11-25
- ✅ 移除 PulseAudio 依赖
- ✅ 改用 ALSA + bluez-alsa 方案
- ✅ 集成 mpg123 播放器
- ✅ 自动检测和使用蓝牙 ALSA 设备
- ✅ 优化资源占用
- ✅ 增强错误处理和日志记录


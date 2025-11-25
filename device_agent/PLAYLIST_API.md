# 播放列表 API 使用说明

## 功能概述

播放列表功能允许你配置一组音乐文件，并通过定时任务自动播放。每次定时任务触发时，系统会播放列表中的下一首歌曲，并记录播放进度，实现循环播放。

## API 接口

### 1. 更新播放列表

**接口**: `POST /playlist/update`

**功能**: 更新播放列表，设置要播放的音乐文件列表。

**请求体**:
```json
{
  "playlist": [
    "/home/orangepi/Videos/song1.mp3",
    "/home/orangepi/Videos/song2.mp3",
    "/home/orangepi/Videos/song3.mp3"
  ],
  "device_address": "58:EA:1F:1A:9A:8B"
}
```

**参数说明**:
- `playlist` (必需): 音乐文件路径数组
- `device_address` (可选): 蓝牙设备 MAC 地址，用于播放音频

**响应示例**:
```json
{
  "success": true,
  "message": "播放列表已更新",
  "data": {
    "playlist": [
      "/home/orangepi/Videos/song1.mp3",
      "/home/orangepi/Videos/song2.mp3",
      "/home/orangepi/Videos/song3.mp3"
    ],
    "total": 3,
    "device_address": "58:EA:1F:1A:9A:8B",
    "current_index": 0
  }
}
```

**curl 示例**:
```bash
curl -X POST http://localhost:8080/playlist/update \
  -H "Content-Type: application/json" \
  -d '{
    "playlist": [
      "/home/orangepi/Videos/xiaopingguo.mp3",
      "/home/orangepi/Videos/song2.mp3"
    ],
    "device_address": "58:EA:1F:1A:9A:8B"
  }'
```

---

### 2. 获取播放列表状态

**接口**: `GET /playlist/status`

**功能**: 获取当前播放列表配置和播放进度。

**响应示例**:
```json
{
  "success": true,
  "data": {
    "playlist": [
      "/home/orangepi/Videos/song1.mp3",
      "/home/orangepi/Videos/song2.mp3",
      "/home/orangepi/Videos/song3.mp3"
    ],
    "total": 3,
    "current_index": 1,
    "current_file": "/home/orangepi/Videos/song2.mp3",
    "device_address": "58:EA:1F:1A:9A:8B"
  }
}
```

**curl 示例**:
```bash
curl http://localhost:8080/playlist/status
```

---

### 3. 播放当前歌曲

**接口**: `POST /playlist/play`

**功能**: 立即播放当前播放列表中的歌曲（不等待定时任务触发）。

**响应示例**:
```json
{
  "success": true,
  "message": "播放成功",
  "data": {
    "played_index": 0,
    "played_file": "/home/orangepi/Videos/song1.mp3",
    "next_index": 1,
    "playlist_total": 3
  }
}
```

**curl 示例**:
```bash
curl -X POST http://localhost:8080/playlist/play
```

---

### 4. 播放下一首歌曲

**接口**: `POST /playlist/playNext`

**功能**: 播放下一首歌曲，如果当前是最后一首则自动循环到第一首。

**响应示例**:
```json
{
  "success": true,
  "message": "播放成功",
  "data": {
    "played_index": 1,
    "played_file": "/home/orangepi/Videos/song2.mp3",
    "next_index": 2,
    "next_file": "/home/orangepi/Videos/song3.mp3",
    "playlist_total": 3,
    "is_looped": false
  }
}
```

**循环播放示例**（最后一首时）:
```json
{
  "success": true,
  "message": "播放成功 (已循环到第一首)",
  "data": {
    "played_index": 2,
    "played_file": "/home/orangepi/Videos/song3.mp3",
    "next_index": 0,
    "next_file": "/home/orangepi/Videos/song1.mp3",
    "playlist_total": 3,
    "is_looped": true
  }
}
```

**curl 示例**:
```bash
curl -X POST http://localhost:8080/playlist/playNext
```

---

## 定时任务配置

要启用定时播放功能，需要配置 cron 任务。

### 1. 配置定时任务触发播放

**接口**: `POST /cron/update`

**请求体**:
```json
{
  "enabled": true,
  "expression": "0 7 * * *",
  "command": "play_next_track"
}
```

**参数说明**:
- `enabled`: 启用定时任务
- `expression`: cron 表达式（例如 `0 7 * * *` 表示每天早上 7:00）
- `command`: 设置为 `play_next_track` 以触发播放列表播放

**curl 示例**:
```bash
# 设置每天早上 7:00 播放下一首歌
curl -X POST http://localhost:8080/cron/update \
  -H "Content-Type: application/json" \
  -d '{
    "enabled": true,
    "expression": "0 7 * * *",
    "command": "play_next_track"
  }'
```

### 2. 查看定时任务状态

```bash
curl http://localhost:8080/cron/status
```

**响应示例**:
```json
{
  "success": true,
  "data": {
    "running": true,
    "enabled": true,
    "cron_expression": "0 7 * * *",
    "command": "play_next_track",
    "jobs": [
      {
        "id": "cron_command_job",
        "name": "定时执行命令",
        "next_run_time": "2025-11-26T07:00:00+08:00"
      }
    ]
  }
}
```

---

## 完整使用流程

### 步骤 1: 配置播放列表

```bash
curl -X POST http://localhost:8080/playlist/update \
  -H "Content-Type: application/json" \
  -d '{
    "playlist": [
      "/home/orangepi/Videos/xiaopingguo.mp3",
      "/home/orangepi/Videos/song2.mp3",
      "/home/orangepi/Videos/song3.mp3"
    ],
    "device_address": "58:EA:1F:1A:9A:8B"
  }'
```

### 步骤 2: 配置定时任务

```bash
# 每天早上 7:00 播放
curl -X POST http://localhost:8080/cron/update \
  -H "Content-Type: application/json" \
  -d '{
    "enabled": true,
    "expression": "0 7 * * *",
    "command": "play_next_track"
  }'
```

### 步骤 3: 验证配置

```bash
# 查看播放列表
curl http://localhost:8080/playlist/status

# 查看定时任务
curl http://localhost:8080/cron/status
```

---

## Cron 表达式说明

Cron 表达式格式: `分 时 日 月 周`

**常用示例**:

| 表达式 | 说明 |
|--------|------|
| `0 7 * * *` | 每天早上 7:00 |
| `30 6 * * *` | 每天早上 6:30 |
| `0 */2 * * *` | 每 2 小时整点 |
| `0 7 * * 1-5` | 周一到周五早上 7:00 |
| `0 8 * * 6,0` | 周六和周日早上 8:00 |
| `0 7,19 * * *` | 每天早上 7:00 和晚上 19:00 |

---

## 工作原理

1. **播放列表管理**: 系统将播放列表保存在 `config.properties` 中（JSON 格式）
2. **播放进度跟踪**: 每次播放后，系统会更新 `current_track_index`，记录下次要播放的歌曲索引
3. **循环播放**: 当播放到列表末尾时，自动从第一首开始
4. **定时触发**: APScheduler 根据 cron 表达式定时触发 `play_next_track` 函数
5. **蓝牙播放**: 使用 `mpg123` 和 `bluez-alsa` 通过蓝牙设备播放音频

---

## 配置文件

所有配置保存在 `config.properties` 文件中：

```properties
# 定时任务配置
cron.enabled=true
cron.expression=0 7 * * *
cron.command=play_next_track

# 播放列表（JSON 格式）
playlist=["\/home\/orangepi\/Videos\/song1.mp3","\/home\/orangepi\/Videos\/song2.mp3"]

# 当前播放索引
current_track_index=0

# 蓝牙设备地址
bluetooth_device_address=58:EA:1F:1A:9A:8B
```

---

## 注意事项

1. **文件路径验证**: 更新播放列表时，系统会验证所有文件是否存在
2. **蓝牙设备**: 确保蓝牙设备已配对并连接
3. **音频格式**: 当前支持 `mpg123` 可播放的格式（主要是 MP3）
4. **权限要求**: 确保运行用户有权限访问音频文件和蓝牙设备
5. **播放重叠**: 定时任务不会停止当前播放，如果上一首还在播放，会启动新的播放进程

---

## 故障排查

### 查看日志

```bash
curl http://localhost:8080/log
```

### 常见问题

1. **没有声音**: 
   - 检查蓝牙设备是否已连接
   - 查看 `/media/debug` 接口检查系统状态
   - 确认 `bluez-alsa` 服务正在运行

2. **文件不存在错误**:
   - 确保文件路径正确
   - 检查文件权限

3. **定时任务不执行**:
   - 确认 `cron.enabled=true`
   - 检查 cron 表达式格式
   - 查看系统日志

---

## 手动测试

可以使用 Python 脚本手动测试播放功能：

```bash
cd /home/orangepi/project/MyTodo/device_agent
python3 -c "from core.playlist_player import play_next_track; play_next_track()"
```

或直接运行模块：

```bash
python3 -m core.playlist_player
```


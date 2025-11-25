# 播放列表功能 - 快速开始

## 5 分钟快速配置

### 步骤 1: 准备音乐文件

确保你的音乐文件已经放在服务器上，例如：

```bash
/home/orangepi/Videos/song1.mp3
/home/orangepi/Videos/song2.mp3
/home/orangepi/Videos/song3.mp3
```

### 步骤 2: 连接蓝牙设备

查看已配对的蓝牙设备：

```bash
curl http://localhost:5000/bluetooth/paired
```

记下要使用的蓝牙设备 MAC 地址，例如：`58:EA:1F:1A:9A:8B`

### 步骤 3: 配置播放列表

```bash
curl -X POST http://localhost:5000/playlist/update \
  -H "Content-Type: application/json" \
  -d '{
    "playlist": [
      "/home/orangepi/Videos/song1.mp3",
      "/home/orangepi/Videos/song2.mp3",
      "/home/orangepi/Videos/song3.mp3"
    ],
    "device_address": "58:EA:1F:1A:9A:8B"
  }'
```

### 步骤 4: 设置定时播放

设置每天早上 7:00 自动播放：

```bash
curl -X POST http://localhost:5000/cron/update \
  -H "Content-Type: application/json" \
  -d '{
    "enabled": true,
    "expression": "0 7 * * *",
    "command": "play_next_track"
  }'
```

### 步骤 5: 验证配置

查看播放列表状态：

```bash
curl http://localhost:5000/playlist/status
```

查看定时任务状态：

```bash
curl http://localhost:5000/cron/status
```

## 手动测试播放

### 方法 1: 使用 API 接口

立即播放当前歌曲：
```bash
curl -X POST http://localhost:5000/playlist/play
```

播放下一首歌曲：
```bash
curl -X POST http://localhost:5000/playlist/playNext
```

### 方法 2: 使用 Python 脚本

```bash
cd /home/orangepi/project/MyTodo/device_agent
python3 -m core.playlist_player
```

### 方法 3: 使用测试脚本

```bash
python3 test_playlist.py
```

## 常见定时配置

### 每天早上 7:00
```json
{
  "enabled": true,
  "expression": "0 7 * * *",
  "command": "play_next_track"
}
```

### 每天早上 6:30
```json
{
  "enabled": true,
  "expression": "30 6 * * *",
  "command": "play_next_track"
}
```

### 每 2 小时
```json
{
  "enabled": true,
  "expression": "0 */2 * * *",
  "command": "play_next_track"
}
```

### 周一到周五早上 7:00
```json
{
  "enabled": true,
  "expression": "0 7 * * 1-5",
  "command": "play_next_track"
}
```

### 每天早上 7:00 和晚上 19:00
```json
{
  "enabled": true,
  "expression": "0 7,19 * * *",
  "command": "play_next_track"
}
```

## 工作原理

1. **初次配置**: 你配置了包含 3 首歌的播放列表，当前索引为 0
2. **第一次触发**: 定时任务在 7:00 触发，播放第 1 首歌（索引 0），然后将索引更新为 1
3. **第二次触发**: 第二天 7:00，播放第 2 首歌（索引 1），然后将索引更新为 2
4. **第三次触发**: 第三天 7:00，播放第 3 首歌（索引 2），然后将索引更新为 0
5. **循环播放**: 第四天 7:00，又从第 1 首歌开始，如此循环

## 使用脚本快速配置

我们提供了一个交互式配置脚本：

```bash
bash example_playlist_setup.sh
```

这个脚本会引导你完成所有配置步骤。

## 故障排查

### 查看日志

```bash
# 通过 Web 界面
curl http://localhost:5000/log

# 或直接查看日志文件
tail -f logs/app.log
```

### 检查系统状态

```bash
# 检查环境和权限
curl http://localhost:5000/media/debug

# 检查蓝牙设备
curl http://localhost:5000/bluetooth/paired

# 检查播放列表
curl http://localhost:5000/playlist/status

# 检查定时任务
curl http://localhost:5000/cron/status
```

### 常见问题

**问题 1: 没有声音**
- 确认蓝牙设备已连接
- 检查 bluez-alsa 服务是否运行: `systemctl status bluealsa`
- 查看日志了解详细错误

**问题 2: 定时任务不执行**
- 确认 `cron.enabled=true`
- 检查 cron 表达式格式是否正确
- 查看定时任务状态: `curl http://localhost:5000/cron/status`

**问题 3: 文件找不到**
- 确认文件路径正确
- 检查文件权限

## 更新播放列表

随时可以更新播放列表，新配置会立即生效：

```bash
curl -X POST http://localhost:5000/playlist/update \
  -H "Content-Type: application/json" \
  -d '{
    "playlist": [
      "/path/to/new_song1.mp3",
      "/path/to/new_song2.mp3"
    ],
    "device_address": "58:EA:1F:1A:9A:8B"
  }'
```

更新播放列表会自动重置播放索引到 0。

## 暂停或禁用定时播放

要暂时禁用定时播放：

```bash
curl -X POST http://localhost:5000/cron/update \
  -H "Content-Type: application/json" \
  -d '{
    "enabled": false
  }'
```

要重新启用，将 `enabled` 设置为 `true`。

## 下一步

查看完整文档了解更多功能：

- [PLAYLIST_API.md](PLAYLIST_API.md) - 完整的 API 文档
- [README.md](README.md) - 项目主文档
- [TROUBLESHOOTING.md](TROUBLESHOOTING.md) - 故障排查指南


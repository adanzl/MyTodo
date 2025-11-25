# 播放列表 API 快速参考

## 📋 接口总览

| 接口 | 方法 | 功能 | 文档 |
|------|------|------|------|
| `/playlist/update` | POST | 更新播放列表 | [📄](#更新播放列表) |
| `/playlist/status` | GET | 获取播放状态 | [📄](#获取播放状态) |
| `/playlist/play` | POST | 播放当前歌曲 | [📄](#播放当前歌曲) |
| `/playlist/playNext` | POST | 播放下一首 | [📄](#播放下一首) |

---

## 更新播放列表

```bash
POST /playlist/update
```

**请求体**:
```json
{
  "playlist": ["/path/to/song1.mp3", "/path/to/song2.mp3"],
  "device_address": "58:EA:1F:1A:9A:8B"
}
```

**响应**:
```json
{
  "success": true,
  "message": "播放列表已更新",
  "data": {
    "playlist": [...],
    "total": 2,
    "device_address": "58:EA:1F:1A:9A:8B",
    "current_index": 0
  }
}
```

**curl**:
```bash
curl -X POST http://localhost:5000/playlist/update \
  -H "Content-Type: application/json" \
  -d '{"playlist":["/path/to/song1.mp3"], "device_address":"58:EA:1F:1A:9A:8B"}'
```

---

## 获取播放状态

```bash
GET /playlist/status
```

**响应**:
```json
{
  "success": true,
  "data": {
    "playlist": [...],
    "total": 3,
    "current_index": 1,
    "current_file": "/path/to/song2.mp3",
    "device_address": "58:EA:1F:1A:9A:8B"
  }
}
```

**curl**:
```bash
curl http://localhost:5000/playlist/status
```

---

## 播放当前歌曲

```bash
POST /playlist/play
```

**功能**: 立即播放当前索引的歌曲

**响应**:
```json
{
  "success": true,
  "message": "播放成功",
  "data": {
    "played_index": 0,
    "played_file": "/path/to/song1.mp3",
    "next_index": 1,
    "playlist_total": 3
  }
}
```

**curl**:
```bash
curl -X POST http://localhost:5000/playlist/play
```

---

## 播放下一首

```bash
POST /playlist/playNext
```

**功能**: 播放下一首歌曲，最后一首时自动循环到第一首

**响应**:
```json
{
  "success": true,
  "message": "播放成功",
  "data": {
    "played_index": 1,
    "played_file": "/path/to/song2.mp3",
    "next_index": 2,
    "next_file": "/path/to/song3.mp3",
    "playlist_total": 3,
    "is_looped": false
  }
}
```

**循环时**:
```json
{
  "success": true,
  "message": "播放成功 (已循环到第一首)",
  "data": {
    "played_index": 2,
    "played_file": "/path/to/song3.mp3",
    "next_index": 0,
    "next_file": "/path/to/song1.mp3",
    "playlist_total": 3,
    "is_looped": true
  }
}
```

**curl**:
```bash
curl -X POST http://localhost:5000/playlist/playNext
```

---

## 🔄 完整使用流程

```bash
# 1. 配置播放列表
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

# 2. 查看状态
curl http://localhost:5000/playlist/status

# 3. 播放第一首
curl -X POST http://localhost:5000/playlist/play

# 4. 播放第二首
curl -X POST http://localhost:5000/playlist/playNext

# 5. 播放第三首
curl -X POST http://localhost:5000/playlist/playNext

# 6. 播放第一首（循环）
curl -X POST http://localhost:5000/playlist/playNext
```

---

## ⏰ 定时播放配置

设置每天早上 7:00 自动播放下一首：

```bash
curl -X POST http://localhost:5000/cron/update \
  -H "Content-Type: application/json" \
  -d '{
    "enabled": true,
    "expression": "0 7 * * *",
    "command": "play_next_track"
  }'
```

---

## 🛠️ 相关接口

### 停止播放
```bash
curl -X POST http://localhost:5000/media/stop
```

### 查看系统状态
```bash
curl http://localhost:5000/media/debug
```

### 查看蓝牙设备
```bash
curl http://localhost:5000/bluetooth/paired
```

---

## 📚 详细文档

- **完整文档**: [PLAYLIST_API.md](PLAYLIST_API.md)
- **快速开始**: [QUICK_START_PLAYLIST.md](QUICK_START_PLAYLIST.md)
- **更新日志**: [CHANGELOG_PLAYLIST.md](CHANGELOG_PLAYLIST.md)

---

## 💡 常见用法

### 设置播放列表并立即播放
```bash
# 配置
curl -X POST http://localhost:5000/playlist/update \
  -H "Content-Type: application/json" \
  -d '{"playlist":["/path/to/song.mp3"], "device_address":"XX:XX:XX:XX:XX:XX"}'

# 播放
curl -X POST http://localhost:5000/playlist/play
```

### 连续播放多首歌
```bash
# 播放第一首
curl -X POST http://localhost:5000/playlist/play

# 等待 5 分钟后播放下一首
sleep 300
curl -X POST http://localhost:5000/playlist/playNext

# 等待 5 分钟后播放下一首
sleep 300
curl -X POST http://localhost:5000/playlist/playNext
```

### 循环播放整个列表
```bash
# 使用 cron 每天播放一次
curl -X POST http://localhost:5000/cron/update \
  -H "Content-Type: application/json" \
  -d '{
    "enabled": true,
    "expression": "0 7 * * *",
    "command": "play_next_track"
  }'
```

---

## ⚠️ 注意事项

1. **文件路径**: 必须使用绝对路径
2. **蓝牙设备**: 必须已配对并连接
3. **并发播放**: 多次调用会启动多个播放进程
4. **错误处理**: 文件不存在时会跳过并移动到下一首
5. **播放状态**: 播放进程在后台运行，不阻塞 API 响应

---

## 🐛 故障排查

### 没有声音
```bash
# 检查蓝牙设备
curl http://localhost:5000/bluetooth/paired

# 检查系统状态
curl http://localhost:5000/media/debug

# 查看日志
curl http://localhost:5000/log
```

### 文件不存在
```bash
# 检查文件路径
ls -l /path/to/your/music/file.mp3

# 确认配置
curl http://localhost:5000/playlist/status
```

### 播放列表为空
```bash
# 重新配置
curl -X POST http://localhost:5000/playlist/update \
  -H "Content-Type: application/json" \
  -d '{"playlist":["/valid/path/to/song.mp3"], "device_address":"XX:XX:XX:XX:XX:XX"}'
```


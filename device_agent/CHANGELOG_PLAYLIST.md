# 播放列表功能更新日志

## 版本 1.1.1 (2025-11-25)
**Bug 修复**: 定时任务调度器多次初始化问题

### 修复
- ✅ 修复定时任务调度器在应用启动时被多次初始化的问题
- ✅ 添加 `_started` 标志跟踪初始化状态，避免重复调用
- ✅ 使用双重检查锁定模式确保单例线程安全
- ✅ 优化初始化日志，只在首次启动时输出

### 技术改进
- ✅ 在 `CronScheduler.__init__()` 中添加 `self._started` 标志
- ✅ 在 `CronScheduler.start()` 中检查 `_started` 避免重复初始化
- ✅ 在 `get_scheduler()` 中添加 `threading.Lock` 保护
- ✅ 改进 `core/__init__.py` 中的启动日志逻辑

### 为什么不能只用 `scheduler.running`？
当 `cron.enabled=false` 时，调度器不会启动，`scheduler.running` 始终为 `False`，无法阻止重复初始化。使用 `_started` 标志可以跟踪是否已完成初始化流程。

### 文档
- ✅ 新增 `BUGFIX_SCHEDULER.md` - 详细说明修复内容

---

## 版本 1.1 (2025-11-25)
**功能**: 播放列表接口独立化 + 新增手动播放接口

### 重构
- ✅ 将播放列表相关接口独立到 `core/api/playlist_routes.py`
- ✅ 从 `routes.py` 中移除播放列表接口
- ✅ 注册 `playlist_bp` 蓝图到主应用

### 新增接口
- ✅ `POST /playlist/play` - 播放当前歌曲
- ✅ `POST /playlist/playNext` - 播放下一首歌曲（自动循环）

### 文档更新
- ✅ 更新 `PLAYLIST_API.md` 添加新接口说明
- ✅ 更新 `QUICK_START_PLAYLIST.md` 添加手动测试方法
- ✅ 更新 `README.md` 添加 API 快速参考
- ✅ 新增 `test_playlist_api.sh` 测试脚本
- ✅ 新增 `PLAYLIST_API_QUICK_REF.md` - API 快速参考卡片

---

## 版本 1.0 (2025-11-25)
**功能**: 播放列表管理与定时播放

---

## 新增功能

### 1. 播放列表管理
- ✅ 配置和管理音乐播放列表
- ✅ 支持通过 API 更新播放列表
- ✅ 播放列表持久化存储
- ✅ 文件路径验证

### 2. 播放进度跟踪
- ✅ 自动记录当前播放位置
- ✅ 循环播放支持
- ✅ 播放索引持久化

### 3. 定时播放
- ✅ 通过 Cron 表达式定时触发播放
- ✅ 集成到现有的定时任务系统
- ✅ 自动播放下一首歌曲

### 4. 蓝牙设备配置
- ✅ 配置默认蓝牙播放设备
- ✅ 自动获取 ALSA 设备名称
- ✅ 支持多蓝牙设备切换

---

## 新增 API 接口

### `POST /playlist/update`
更新播放列表和蓝牙设备配置

**参数**:
- `playlist`: 音乐文件路径数组（必需）
- `device_address`: 蓝牙设备 MAC 地址（可选）

### `GET /playlist/status`
获取当前播放列表状态和播放进度

**返回**:
- `playlist`: 播放列表
- `total`: 歌曲总数
- `current_index`: 当前播放索引
- `current_file`: 当前要播放的文件
- `device_address`: 蓝牙设备地址

---

## 新增模块

### `core/playlist_player.py`
播放列表播放器模块

**主要函数**:
- `play_next_track()`: 播放播放列表中的下一首歌曲
  - 读取播放列表配置
  - 获取当前播放索引
  - 通过 `mpg123` 和蓝牙设备播放音频
  - 更新播放索引到下一首
  - 支持循环播放

---

## 修改的模块

### `core/config.py`
添加播放列表配置管理

**新增方法**:
- `get_playlist()`: 获取播放列表
- `set_playlist(playlist)`: 设置播放列表
- `get_current_track_index()`: 获取当前播放索引
- `set_current_track_index(index)`: 设置当前播放索引
- `get_bluetooth_device_address()`: 获取蓝牙设备地址
- `set_bluetooth_device_address(address)`: 设置蓝牙设备地址

### `core/scheduler.py`
支持播放列表播放命令

**修改**:
- `execute_command()`: 识别 `play_next_track` 命令并调用播放函数
- 添加延迟导入机制避免循环依赖

### `core/api/routes.py`
添加播放列表管理接口

**新增路由**:
- `/playlist/update`: 更新播放列表
- `/playlist/status`: 获取播放列表状态

---

## 配置文件更新

### `config.properties`
添加播放列表相关配置

**新增配置项**:
```properties
# 播放列表（JSON 格式）
playlist=[]

# 当前播放索引
current_track_index=0

# 蓝牙设备地址
bluetooth_device_address=
```

**Cron 命令示例**:
```properties
cron.enabled=true
cron.expression=0 7 * * *
cron.command=play_next_track
```

---

## 新增文档

### 1. `PLAYLIST_API.md`
播放列表功能完整文档
- API 接口说明
- 定时任务配置
- 完整使用流程
- Cron 表达式说明
- 工作原理
- 故障排查

### 2. `QUICK_START_PLAYLIST.md`
5 分钟快速配置指南
- 步骤化配置流程
- 常见定时配置示例
- 手动测试方法
- 故障排查快速参考

### 3. `example_playlist_setup.sh`
交互式配置脚本
- 引导式配置流程
- 自动化配置示例

### 4. `test_playlist.py`
播放列表功能测试脚本
- 配置测试
- 播放测试
- 循环逻辑测试

---

## 使用示例

### 配置播放列表
```bash
curl -X POST http://localhost:5000/playlist/update \
  -H "Content-Type: application/json" \
  -d '{
    "playlist": [
      "/home/orangepi/Videos/song1.mp3",
      "/home/orangepi/Videos/song2.mp3"
    ],
    "device_address": "58:EA:1F:1A:9A:8B"
  }'
```

### 设置定时播放（每天早上 7:00）
```bash
curl -X POST http://localhost:5000/cron/update \
  -H "Content-Type: application/json" \
  -d '{
    "enabled": true,
    "expression": "0 7 * * *",
    "command": "play_next_track"
  }'
```

### 手动测试播放
```bash
python3 -m core.playlist_player
```

---

## 技术实现

### 数据持久化
- 播放列表以 JSON 格式存储在 `config.properties`
- 播放索引作为整数存储
- 所有配置通过 `Config` 类统一管理

### 定时任务集成
- 复用现有的 `APScheduler` 调度器
- 通过特殊命令 `play_next_track` 触发播放
- 支持动态更新配置

### 音频播放
- 使用 `mpg123` 播放音频
- 通过 `bluez-alsa` 输出到蓝牙设备
- 后台进程方式运行，不阻塞定时任务

### 循环播放逻辑
```python
next_index = (current_index + 1) % len(playlist)
```

---

## 兼容性

### 系统要求
- Linux 操作系统
- Python 3.7+
- `mpg123` 命令行工具
- `bluez-alsa` 蓝牙音频支持

### 依赖项
- Flask（Web 框架）
- APScheduler（定时任务）
- 现有的蓝牙管理模块

---

## 测试建议

### 单元测试
```bash
python3 test_playlist.py
```

### 集成测试
```bash
bash example_playlist_setup.sh
```

### 手动测试
```bash
# 1. 配置播放列表
curl -X POST http://localhost:5000/playlist/update -d '...'

# 2. 手动触发播放
python3 -m core.playlist_player

# 3. 检查日志
tail -f logs/app.log

# 4. 检查进程
ps aux | grep mpg123
```

---

## 已知限制

1. **音频格式**: 当前主要支持 MP3 格式（mpg123 限制）
2. **并发播放**: 不会自动停止上一首歌，如果定时间隔过短可能导致多个播放进程
3. **错误恢复**: 如果某首歌播放失败，会跳过并移动到下一首
4. **播放状态**: 不跟踪播放进程的完成状态

---

## 未来改进方向

- [ ] 支持更多音频格式（使用 `ffmpeg`）
- [ ] 添加播放队列管理
- [ ] 支持随机播放模式
- [ ] 添加音量控制
- [ ] 播放历史记录
- [ ] Web UI 播放列表管理界面
- [ ] 支持从 URL 播放（在线音频流）
- [ ] 播放完成状态跟踪

---

## 反馈与贡献

如果在使用过程中遇到问题或有改进建议，欢迎：
1. 查看日志文件 `logs/app.log`
2. 使用调试接口 `/media/debug`
3. 查看故障排查文档 `TROUBLESHOOTING.md`

---

## 版权与许可

本功能作为 Device Agent 项目的一部分发布。


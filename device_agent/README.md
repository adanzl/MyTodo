# Device Agent - 设备控制代理服务

一个基于 Flask 的设备控制服务，支持蓝牙设备管理、音频播放和定时任务等功能。

## 功能特性

### 🎵 蓝牙音频播放
- 蓝牙设备扫描和连接
- 通过蓝牙音箱播放音频文件
- 支持多种音频格式（MP3, WAV, OGG, FLAC 等）
- 使用 ALSA + bluez-alsa（无需 PulseAudio）

### 📡 蓝牙设备管理
- 扫描附近的蓝牙设备
- 连接/断开蓝牙设备
- 查看已配对设备列表
- 获取设备连接状态

### 📊 系统监控
- Web 日志查看界面
- API 状态查询

## 快速开始

### 系统要求

- Linux 操作系统（已在 Ubuntu/Debian 上测试）
- Python 3.7+
- 蓝牙硬件支持

### 安装依赖

```bash
# 系统包
sudo apt-get update
sudo apt-get install -y \
    bluetooth bluez bluez-alsa bluealsa \
    alsa-utils mpg123 \
    python3-pip python3-dev

# Python 包
pip install -r requirements.txt
```

### 启动服务

```bash
# 启动 bluealsa 服务
sudo systemctl start bluealsa
sudo systemctl enable bluealsa

# 启动应用
python main.py

# 使用 gunicorn（生产环境推荐）
gunicorn -w 1 -b 0.0.0.0:5000 main:app
```

## API 文档

### 蓝牙相关

#### 扫描蓝牙设备
```bash
GET /bluetooth/scan?timeout=5
```

#### 获取已配对设备
```bash
GET /bluetooth/paired
```

#### 连接蓝牙设备
```bash
POST /bluetooth/connect
Content-Type: application/json

{
  "address": "58:EA:1F:1A:9A:8B"
}
```

#### 设置默认蓝牙设备
```bash
POST /bluetooth/setDefault
Content-Type: application/json

{
  "address": "58:EA:1F:1A:9A:8B"
}
```

#### 获取默认蓝牙设备
```bash
GET /bluetooth/default
```

### 音频播放

#### 播放单个音频文件（推荐）
```bash
POST /media/play
Content-Type: application/json

{
  "file_path": "/home/orangepi/Videos/music.mp3",
  "device_address": "D4:DA:21:BA:81:67"
}

# 或使用默认设备（无需指定 device_address）
{
  "file_path": "/home/orangepi/Videos/music.mp3"
}
```

#### 播放目录音频
```bash
POST /media/playDir
Content-Type: application/json

{
  "path": "/mnt/music",
  "device_address": "58:EA:1F:1A:9A:8B"
}
```

#### 停止播放
```bash
POST /media/stop
```

#### 获取音频设备列表
```bash
GET /media/getAudioDevices
```

#### 调试信息（故障排查）
```bash
GET /media/debug
```

### 系统监控

#### Web 日志界面
```bash
GET /log
```

## 项目结构

```
device_agent/
├── main.py                 # 应用入口
├── config.properties       # 配置文件
├── requirements.txt        # Python 依赖
├── core/
│   ├── __init__.py        # Flask 应用初始化
│   ├── log_config.py      # 日志配置
│   ├── config.py          # 配置读取
│   ├── api/
│   │   ├── routes.py      # 通用路由
│   │   ├── bluetooth_routes.py  # 蓝牙相关路由
│   │   └── media_routes.py      # 媒体播放路由
│   └── device/
│       └── bluetooth.py   # 蓝牙设备管理
└── templates/
    ├── image.html         # 图片显示页面
    └── server_log.html    # 日志查看页面
```

## 技术栈

- **Web 框架**: Flask + Flask-CORS
- **异步支持**: Gevent
- **音频播放**: mpg123 (主要) / pygame (回退)
- **蓝牙管理**: BlueZ + bluez-alsa
- **音频系统**: ALSA
- **定时任务**: APScheduler
- **蓝牙 Python 库**: Bleak

## 常见问题

### 蓝牙音频无法播放

1. 检查 bluealsa 服务是否运行：
```bash
systemctl status bluealsa
```

2. 确认蓝牙设备已连接：
```bash
bluetoothctl info <MAC_ADDRESS>
```

3. 验证 ALSA 设备存在：
```bash
aplay -L | grep bluealsa
```

详细故障排查请参考 [BLUETOOTH_AUDIO_ALSA.md](BLUETOOTH_AUDIO_ALSA.md)

### 定时任务不执行

1. 检查配置文件中 `cron.enabled=true`
2. 验证 Cron 表达式格式正确
3. 查看应用日志确认错误信息

详细说明请参考 [README_CRON.md](README_CRON.md)

## 贡献

欢迎提交 Issue 和 Pull Request！

## 许可证

MIT License

## 更新日志

### 2025-11-25
- ✅ 实现蓝牙设备管理功能
- ✅ 支持蓝牙音频播放（ALSA 方案）
- ✅ 添加定时任务调度功能
- ✅ 精简代码，只保留 Linux 平台支持
- ✅ 修复中文字符显示问题
- ✅ 优化蓝牙设备连接状态检测
- ✅ 完善 API 文档和错误处理


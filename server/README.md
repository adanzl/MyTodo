# MyTodo Server

一个基于 Flask 的全功能后端服务，提供 AI 对话、媒体管理、设备控制、文件管理等综合功能。

## 📋 项目概述

MyTodo Server 是一个功能丰富的后端服务系统，集成了 AI 对话、语音识别与合成、媒体播放管理、智能设备控制、文件管理、定时任务调度等多种功能模块。采用 Flask + Gevent 异步架构，支持 WebSocket 实时通信。

## 🚀 快速开始

### 环境要求

- Python 3.x
- Conda 环境（推荐使用 `flask_env`）
- Redis 服务器
- SQLite 数据库

### 安装依赖

```bash
pip install -r requirements.txt
```

### 启动服务

#### 开发/生产模式

项目已经内置了 Gevent WSGIServer，**直接运行即可**：

```bash
python main.py
```

**说明**：

- ✅ 支持 WebSocket、异步处理、定时任务
- ✅ 使用 Gevent WSGIServer，性能足够
- ✅ 简单易维护，适合小型项目

**生产环境使用 systemd 管理**（见下方部署说明）

### 访问地址

- API 接口: `http://127.0.0.1:8000/api`
- Web 前端: `http://127.0.0.1:8000/web/index.html`
- 服务器日志: `http://127.0.0.1:8000/api/log`

## 📁 项目结构

```txt
server/
├── core/                    # 核心模块
│   ├── __init__.py         # Flask 应用工厂
│   ├── api/                # API 路由模块
│   │   ├── routes.py       # 通用路由（数据库、文件、积分等）
│   │   ├── agent_routes.py # Agent 相关路由
│   │   ├── bluetooth_routes.py  # 蓝牙设备路由
│   │   ├── dlna_routes.py  # DLNA 设备路由
│   │   ├── media_routes.py # 媒体播放路由
│   │   ├── mi_routes.py    # 小米设备路由
│   │   └── pdf_routes.py   # PDF 处理路由
│   ├── ai/                 # AI 模块
│   │   ├── ai_local.py     # 本地 AI 实现
│   │   └── ai_mgr.py       # AI 管理器（火山引擎）
│   ├── chat/               # 聊天模块
│   │   ├── chat_mgr.py     # 聊天管理器（WebSocket）
│   │   └── asr_client.py   # 语音识别客户端
│   ├── tts/                # 语音合成模块
│   │   ├── tts_client.py   # TTS 客户端
│   │   ├── tts_doubao.py   # 豆包 TTS
│   │   └── tts_zero.py     # Zero TTS
│   ├── db/                 # 数据库模块
│   │   ├── db_mgr.py       # SQLite 数据库管理器
│   │   └── rds_mgr.py      # Redis 管理器
│   ├── device/             # 设备控制模块
│   │   ├── agent.py        # Agent 设备
│   │   ├── bluetooth.py    # 蓝牙设备
│   │   ├── dlna.py         # DLNA 设备
│   │   └── mi_device.py    # 小米设备
│   ├── services/           # 业务服务模块
│   │   ├── agent_mgr.py    # Agent 管理器
│   │   ├── audio_merge_mgr.py  # 音频合成管理器
│   │   ├── pdf_mgr.py      # PDF 管理器
│   │   ├── playlist_mgr.py # 播放列表管理器
│   │   └── scheduler_mgr.py # 定时任务调度器
│   ├── models/             # 数据模型
│   │   ├── user.py         # 用户模型
│   │   └── score_history.py # 积分历史模型
│   ├── tools/              # 工具模块
│   │   ├── async_util.py   # 异步工具
│   │   └── useragent_fix.py # UserAgent 修复
│   ├── log_config.py       # 日志配置
│   └── utils.py            # 工具函数
├── frontend/               # 前端项目（Vue + Vite）
│   └── src/
│       ├── api/           # API 接口
│       │   ├── devices.ts # 设备相关 API（蓝牙、小米、DLNA）
│       │   ├── config.ts  # API 配置
│       │   └── ...        # 其他 API 模块
│       └── ...
├── static/                 # 静态文件目录
├── templates/             # HTML 模板
├── logs/                  # 日志目录
├── data.db                # SQLite 数据库文件
├── main.py                # 应用入口
├── requirements.txt       # Python 依赖
├── deploy.sh              # 部署脚本
└── README.md              # 项目文档
```

## 🔧 核心功能模块

### 1. AI 对话系统

- **本地 AI**: 支持本地 AI 模型对话
- **云端 AI**: 集成火山引擎豆包 API
- **流式响应**: 支持流式对话输出
- **对话历史**: 支持对话历史记录和恢复

**相关文件**:

- `core/ai/ai_local.py` - 本地 AI 实现
- `core/ai/ai_mgr.py` - AI 管理器

### 2. 语音识别与合成（ASR/TTS）

- **语音识别**: 集成 FunASR 语音识别服务
- **语音合成**: 支持豆包 TTS 和 Zero TTS
- **流式处理**: 支持音频流式传输和处理
- **自动 TTS**: 支持 AI 回复自动转换为语音

**相关文件**:

- `core/chat/asr_client.py` - ASR 客户端
- `core/tts/tts_client.py` - TTS 客户端
- `core/tts/tts_doubao.py` - 豆包 TTS
- `core/tts/tts_zero.py` - Zero TTS

### 3. WebSocket 实时通信

- **实时消息**: 基于 Flask-SocketIO 的 WebSocket 通信
- **多客户端**: 支持多客户端同时连接
- **房间管理**: 支持聊天室功能
- **事件处理**: 支持文本、音频等多种消息类型

**相关文件**:

- `core/chat/chat_mgr.py` - 聊天管理器

### 4. 媒体播放管理

- **播放列表**: 支持播放列表的创建、更新、播放
- **任务管理**: 支持媒体任务的创建、上传、管理
- **文件浏览**: 支持目录浏览和文件信息获取
- **媒体控制**: 支持播放、暂停、上一首、下一首等操作

**相关文件**:

- `core/api/media_routes.py` - 媒体路由
- `core/services/playlist_mgr.py` - 播放列表管理器
- `core/services/audio_merge_mgr.py` - 音频合成管理器

#### 播放列表 DB 与日期排期

播放列表仅通过 `db_mgr` 读写 SQLite 的 `t_playlist`，不再从 Redis 或本地 Redis 回退文件读取。
`t_playlist_history` 保留最近 10 个集合快照，另存一条一次性迁移标记。

- `mode=weekly` 保留 7 天 `pre_lists` 与原 cron；5 字段 cron 的秒为 0，6 字段 cron 保留秒，统一按上海时区执行和展开日历。日期列由 cron 推导；无有限起止日期时显示 `1970-01-01` 至 `2099-12-31`。多时刻 cron 的 `start_time` 为空，实际时刻以 cron 为准。启用但 cron 为空的旧列表仍支持手动播放。
- `mode=calendar` 使用 `pre_list`，起止日期包含最后一天，每天在 `start_time` 播放；最后一天启动的播放允许跨到次日。
- `status` 是启用状态的唯一来源，保存时同步 `schedule.enabled`，读取时从列值生成旧字段。兼容只发送 `schedule.enabled` 的旧客户端；两个字段同时发送时以 `status` 为准。禁用列表不播放、不注册 cron、不占档期。
- calendar 与同设备的 calendar、weekly 排期均不得重叠；weekly 之间保留旧行为。设备身份使用类型加地址，小米使用类型加 did。区间按 `[开始, 结束)` 判断，允许首尾相接，检查包含跨日尾段。保存和冲突检查使用同一个 SQLite 写事务，失败不覆盖原数据。
- 占用时长优先取 `schedule.duration`（分钟），否则取当次前置和正片曲目的秒数总和；日期排期及有 cron 的列表会在该时长后停止，避免循环播放超出档期。无 cron 的手动 weekly 保留原循环行为。启用 calendar 必须有可用设备及完整时长；共享设备的 weekly 若命中日时长未知，也拒绝无法确认的排期。
- `/playlist/*` 旧接口保留；新增 `GET /api/playlist/calendar?start_date=2026-11-01&end_date=2026-11-30`，一次最多查 62 天，返回两种模式的排期与跨日事件。密集 cron 按日汇总，返回 `occurrence_count` 和 `last_start`，不丢弃触发次数。
- 编辑接口支持 `_revision` 乐观锁；游标和定时器等后台字段按差异合并，避免后台保存覆盖新配置。前端默认打开 Weekly，保留原来的三列界面，仅处理 weekly；新增 Calendar 列表与日历视图两个 Tab。Calendar 列表仅展示日期排期，通过编辑抽屉设置日期时刻、前置曲目、正片和设备；日历视图展示 weekly 与 calendar。
- 新建、复制、改名和排序等集合保存完成后刷新 DB 版本号；失败时重读服务端数据并向调用方抛出错误，不再显示成功。Calendar 删除使用 `POST /api/playlist/delete`，请求包含 `id` 和可选 `_revision`，在事务中只删除目标行，保留并发新增的其他列表；带旧版本号的更新不能重新创建已删除的列表。
- 配置保存保留 DB 中当前的播放态、游标和定时器，不接受旧表单对这些运行字段的覆盖；播放控制仍由原专用接口和后台保存处理。复制列表不继承原列表版本号或正在播放标记。

新增模块：`core/db/playlist_store.py`（事务、版本和历史），`core/services/playlist/calendar_rules.py`（统一排期规则），`frontend/src/views/media/PlaylistWorkspace.vue`（三个 Tab），`migrate_playlists.py`（显式迁移），`tests/db/test_playlist_store.py`（存储与冲突回归）。

**首次切换必须先迁移。** 未完成迁移时播放列表读写报错，防止把空表误当成正式数据。正式数据从远程服务获取，不能使用开发机的 `data.db` 或 `rds_local.json` 代替。准备步骤：冻结旧服务的播放列表写入，使用 SQLite 在线 backup 下载正式 DB，并从同一远程 Redis 通过一个事务读取 `schedule_play:playlist_collection` 和 `schedule_play:playlist_collection_history`，导出为：

```json
{"collection": {"id": {"id": "id", "schedule": {"enabled": 1}}}, "history": {"原时间戳": "原集合 JSON 字符串"}}
```

保留原始备份及 SHA256，在副本先预览、执行并校验，再由部署人员安排正式切换：

```bash
python migrate_playlists.py --snapshot /backup/remote-playlists.json --db /backup/validation-data.db
python migrate_playlists.py --snapshot /backup/remote-playlists.json --db /backup/validation-data.db --apply
```

工具默认只读预览，`--apply` 要求目标 DB 已存在；保留原曲目、设备、播放态和自定义 payload 字段，统一补充 weekly 派生字段。重复导入同一集合不写入；不同集合或已有业务行的目标会拒绝覆盖。工具不会启动 Flask、访问设备、重启服务或拉取代码。正式切换前重新获取冻结后的快照，保留旧版本、DB 在线备份和 Redis 原键作为回退依据；本地副本验证不等同于已完成远程切换。

相关测试在隔离 SQLite 上运行，不依赖正式 Redis：

```bash
mkdir -p tmp/test-case
REDIS_ENABLED=false PYTHONPATH=server python -m pytest server/tests/db/test_playlist_store.py server/tests/services/test_playlist_mgr.py server/tests/services/test_playlist_mgr_timer.py server/tests/services/test_playlist_storage_recovery.py server/tests/services/test_playlist_device_reload.py server/tests/services/test_scheduler_mgr.py server/tests/api/test_playlist_routes.py --basetemp=tmp/test-case/playlist-db
```

### 5. 智能设备控制

#### 蓝牙设备

- 扫描蓝牙设备
- 连接/断开蓝牙设备
- 获取已配对设备列表

#### DLNA 设备

- 扫描 DLNA 设备
- 控制 DLNA 设备音量
- 停止 DLNA 播放

#### 小米设备

- 扫描小米设备
- 获取设备状态（包含音量和播放状态）
- 控制小米设备音量
- 停止小米设备播放

**相关文件**:

- `core/api/bluetooth_routes.py` - 蓝牙路由
- `core/api/dlna_routes.py` - DLNA 路由
- `core/api/mi_routes.py` - 小米设备路由
- `core/device/` - 设备控制实现

### 6. PDF 处理

- **PDF 上传**: 支持 PDF 文件上传
- **PDF 解密**: 支持加密 PDF 解密
- **PDF 列表**: 获取 PDF 文件列表
- **PDF 下载**: 支持 PDF 文件下载
- **PDF 删除**: 支持删除 PDF 文件

**相关文件**:

- `core/api/pdf_routes.py` - PDF 路由
- `core/services/pdf_mgr.py` - PDF 管理器

### 7. 数据库管理

#### SQLite 数据库

- **通用 CRUD**: 支持通用的增删改查操作
- **分页查询**: 支持分页和条件查询
- **数据模型**: 用户、积分历史等数据模型

#### Redis 缓存

- **键值存储**: 支持 Redis 键值对操作
- **列表操作**: 支持 Redis 列表操作
- **数据持久化**: 支持 Redis 数据持久化

**相关文件**:

- `core/db/db_mgr.py` - SQLite 管理器
- `core/db/rds_mgr.py` - Redis 管理器

### 8. 定时任务调度

- **Cron 任务**: 支持标准 Cron 表达式
- **间隔任务**: 支持按时间间隔执行
- **定时任务**: 支持指定时间执行
- **任务管理**: 支持任务的添加、删除、暂停、恢复

**相关文件**:

- `core/services/scheduler_mgr.py` - 定时任务调度器

### 9. 文件管理

- **目录浏览**: 支持目录浏览和文件列表
- **文件信息**: 支持获取文件详细信息
- **媒体时长**: 支持获取媒体文件时长（使用 ffprobe，支持处理警告信息）
- **路径安全**: 支持路径安全检查和限制

**相关文件**:

- `core/api/routes.py` - 文件相关路由
- `core/utils.py` - 工具函数（包含 `get_media_duration`）

### 10. 用户积分系统

- **积分管理**: 支持用户积分增减
- **积分历史**: 记录积分变动历史
- **抽奖系统**: 支持基于积分的抽奖功能

**相关文件**:

- `core/models/user.py` - 用户模型
- `core/models/score_history.py` - 积分历史模型

## 🔌 API 接口文档

### 通用接口

#### 数据库操作

- `GET /api/getAll` - 获取列表数据（支持分页和条件查询）
- `GET /api/getData` - 获取单条数据
- `POST /api/setData` - 设置数据（新增或更新）
- `POST /api/delData` - 删除数据
- `POST /api/query` - 执行 SQL 查询

#### Redis 操作

- `GET /api/getRdsData` - 获取 Redis 数据
- `GET /api/getRdsList` - 获取 Redis 列表（支持分页）
- `POST /api/setRdsData` - 设置 Redis 数据
- `POST /api/addRdsList` - 向 Redis 列表添加数据

#### 文件操作

- `GET /api/listDirectory` - 浏览目录
- `GET /api/getFileInfo` - 获取文件信息

#### 用户相关

- `POST /api/addScore` - 增加积分
- `POST /api/doLottery` - 执行抽奖

### 媒体接口

- `GET /api/playlist/get` - 获取播放列表
- `POST /api/playlist/update` - 更新播放列表
- `POST /api/playlist/play` - 播放
- `POST /api/playlist/playNext` - 下一首
- `POST /api/playlist/playPre` - 上一首
- `POST /api/playlist/stop` - 停止播放
- `GET /api/media/files/<path>` - 获取媒体文件
- `POST /api/media/task/create` - 创建媒体任务
- `POST /api/media/task/start` - 启动媒体任务

### 设备接口

#### 蓝牙接口

- `GET /api/bluetooth/scan` - 扫描蓝牙设备
- `GET /api/bluetooth/device` - 获取蓝牙设备信息
- `POST /api/bluetooth/connect` - 连接蓝牙设备
- `POST /api/bluetooth/disconnect` - 断开蓝牙设备

#### DLNA接口

- `GET /api/dlna/scan` - 扫描 DLNA 设备
- `GET /api/dlna/volume` - 获取/设置 DLNA 音量
- `POST /api/dlna/stop` - 停止 DLNA 播放

#### 小米接口

- `GET /api/mi/scan` - 扫描小米设备
- `GET /api/mi/status` - 获取小米设备状态（包含音量和播放状态）
- `GET /api/mi/volume` - 获取小米设备音量
- `POST /api/mi/volume` - 设置小米设备音量
- `POST /api/mi/stop` - 停止小米设备播放

### PDF 接口

- `POST /api/pdf/upload` - 上传 PDF
- `POST /api/pdf/decrypt` - 解密 PDF
- `GET /api/pdf/list` - 获取 PDF 列表
- `GET /api/pdf/download/<filename>` - 下载 PDF
- `POST /api/pdf/delete` - 删除 PDF

### Agent 接口

- `POST /api/agent/heartbeat` - Agent 心跳
- `POST /api/agent/event` - Agent 事件
- `GET /api/agent/list` - 获取 Agent 列表
- `POST /api/agent/mock` - Mock Agent 数据

### WebSocket 事件

#### 客户端发送事件

- `handshake` - 握手连接
- `message` - 发送消息（文本/音频）
- `tts` - 请求 TTS
- `ttsCancel` - 取消 TTS
- `chatCancel` - 取消对话
- `config` - 更新配置

#### 服务端发送事件

- `handshakeResponse` - 握手响应
- `msgAsr` - ASR 识别结果
- `msgChat` - AI 对话消息
- `endChat` - 对话结束
- `dataAudio` - 音频数据
- `endAudio` - 音频结束
- `error` - 错误消息

## 🛠️ 技术栈

### 后端框架

- **Flask 2.2.5** - Web 框架
- **Flask-SocketIO 5.5.1** - WebSocket 支持
- **Flask-CORS 3.0.10** - 跨域支持
- **Flask-SQLAlchemy 3.1.1** - ORM 框架

### 异步处理

- **Gevent 23.9.1+** - 异步网络库
- **Gevent-WebSocket 0.10.1+** - WebSocket 支持
- **Gunicorn** - WSGI 服务器

### 数据库

- **SQLite** - 关系型数据库
- **Redis 6.0.0** - 缓存数据库

### 任务调度

- **APScheduler 3.10.4** - 定时任务调度

### AI 服务

- **火山引擎豆包 API** - 云端 AI 服务
- **FunASR** - 语音识别服务
- **CosyVoice** - 语音合成服务

### 设备控制

- **Bleak 0.22.3+** - 蓝牙设备控制
- **UPnP Client 0.0.8+** - DLNA 设备控制
- **miservice_fork 0.1.0+** - 小米设备控制

### 其他工具

- **PikePDF 8.0.0+** - PDF 处理
- **LXML 5.0.0+** - XML 处理
- **Requests 2.32.3** - HTTP 客户端
- **WebSocket Client 1.8.0** - WebSocket 客户端

## 📝 配置说明

### 环境变量

项目使用 `python-dotenv` 加载 `.env` 文件中的环境变量。需要配置的环境变量包括：

- Redis 连接配置（在 `core/db/rds_mgr.py` 中配置）
- AI API 密钥（在 `core/ai/ai_mgr.py` 中配置）

#### ASR Provider

默认使用阿里云百炼实时 ASR，原本地 FunASR 完整保留，可通过环境变量随时切换。

```bash
# 阿里云（默认）
ASR_PROVIDER=aliyun
# 不设置时复用 ALI_KEY；也可单独配置 ASR_ALIYUN_API_KEY
ASR_ALIYUN_API_KEY=sk-xxx
ASR_ALIYUN_MODEL=qwen-audio-3.1-asr-flash-streaming
ASR_ALIYUN_VAD_MODEL=near_meeting_16k
ASR_ALIYUN_LANGUAGE_HINTS=zh,en
# 可选：儿童科普场景上下文与即时热词
ASR_ALIYUN_CONTEXT=儿童科普问答，可能出现恐龙、天文、物理、数学和英文科学名词
ASR_ALIYUN_VOCABULARY={"霸王龙":5,"Tyrannosaurus rex":5}
```

默认兼容公共 WebSocket 地址；生产环境可将 `ASR_ALIYUN_SERVER` 配成百炼业务空间专属 WebSocket 地址。API Key 与接口地域必须一致。

切回原本地 FunASR 不需要改代码：

```bash
ASR_PROVIDER=funasr
ASR_SERVER=ws://192.168.50.172:9096
ASR_MODE=offline
```

### 数据库配置

- **SQLite**: 数据库文件位于项目根目录 `data.db`
- **Redis**: 默认连接 `mini:6379`（可在 `core/db/rds_mgr.py` 中修改）

### 日志配置

日志文件位于 `logs/app.log`，可通过 `core/log_config.py` 配置日志级别和格式。

## 🚀 部署说明

### 生产环境部署

项目使用 Gevent WSGIServer，直接运行 `python main.py` 即可。

**启动方式**：

```bash
python main.py
```

**使用 systemd 管理**（推荐）：

### Systemd 服务配置

创建 `/etc/systemd/system/my-todo.service`:

```ini
[Unit]
Description=MyTodo Server
After=network.target

[Service]
Type=simple
User=leo
WorkingDirectory=/mnt/data/project/MyTodo/server
Environment="PATH=/home/leo/.conda/envs/flask_env/bin:/usr/local/bin:/usr/bin:/bin"
ExecStart=/home/leo/.conda/envs/flask_env/bin/python /mnt/data/project/MyTodo/server/main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

启动服务:

```bash
sudo systemctl start my-todo
sudo systemctl enable my-todo
```

### 前端部署

使用 `deploy.sh` 脚本自动构建并部署前端:

```bash
./deploy.sh
```

该脚本会：

1. 构建前端项目
2. 复制构建文件到 `static/` 目录
3. 修复资源路径

## 🔍 开发说明

### Gevent Monkey Patching

项目在 `main.py` 开头进行了 gevent monkey patching，但设置了 `thread=False` 和 `queue=False`，以避免与 asyncio 事件循环冲突。

### 异步处理说明

- 使用 Gevent 进行异步 I/O 处理
- WebSocket 使用 gevent 模式
- 定时任务使用 GeventScheduler

### 代码规范

- 使用 Python 类型提示
- 统一的错误处理和日志记录
- RESTful API 设计

## 📦 前端 API 结构

### 设备 API 统一管理

所有设备相关的 API 已统一整合到 `frontend/src/api/devices.ts`：

- **蓝牙设备**: `bluetoothAction()` - 蓝牙操作接口
- **小米设备**:
  - `scanMiDevices()` - 扫描设备
  - `getMiDeviceStatus()` - 获取设备状态（包含音量和播放状态）
  - `setMiDeviceVolume()` - 设置音量
  - `stopMiDevice()` - 停止播放
- **DLNA 设备**:
  - `scanDlnaDevices()` - 扫描设备
  - `getDlnaDeviceVolume()` - 获取音量
  - `setDlnaDeviceVolume()` - 设置音量
  - `stopDlnaDevice()` - 停止播放

### 其他 API 模块

- `api/config.ts` - API 配置和基础请求封装
- `api/common.ts` - 通用 API
- `api/user.ts` - 用户相关 API
- `api/playlist.ts` - 播放列表 API
- `api/audioMerge.ts` - 音频合成 API
- `api/pdf.ts` - PDF 处理 API
- `api/cron.ts` - 定时任务 API

---

**最后更新**: 2025-01-XX

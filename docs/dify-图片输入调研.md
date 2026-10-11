# Dify 如何接收图片 —— 调研报告

> 调研时间：本次会话；调研对象：文档 + 本机实例 `http://192.168.50.172:9098/v1`（Dify）
> 目的：判断本项目（`PageChat.vue` AI 对话）能否把用户选的图片直接发给 Dify 做多模态对话。

## 1. 结论速览

| 问题 | 结论 |
| --- | --- |
| Dify 支持收图片吗 | 支持，走标准两步式文件 API |
| 现在能用吗 | **不能**。本机 3 个应用的「文件上传」全部未开启，且传了也不报错，文件被静默丢弃 |
| 改代码够吗 | **不够**。必须先在 Dify 控制台改应用配置（API 改不了），再改服务端与前端 |
| 纯前端能做到什么 | 只能走已有的 DashScope `qwen-vl-plus`（OCR/图片转文字），那不是真正的多模态对话 |

## 2. Dify 侧的机制

### 2.1 两步式文件 API

**第一步：上传文件拿 id**

```
POST {base}/files/upload        Content-Type: multipart/form-data
  file=<二进制>                  # 单个文件；文件名不能含 / 或 \
  user=<终端用户标识>             # 必填，决定文件归属
→ 201 {"id":"<upload_file_id>","name":"a.png","extension":"png",
       "mime_type":"image/png","size":70,"source_url":"/files/<id>/file-preview?..."}
```

**第二步：发消息时引用该 id**

```json
POST {base}/chat-messages
{
  "inputs": {},
  "query": "这张图里是什么",
  "user": "leo",
  "response_mode": "streaming",
  "conversation_id": "...",
  "files": [
    { "type": "image", "transfer_method": "local_file", "upload_file_id": "<id>" }
  ]
}
```

也可以用免上传的 `"transfer_method": "remote_url", "url": "https://..."`。

要点与限制：

- `user` 必须与上传时**完全一致**，否则引用不到该文件（文件按 user 归属）。
- `type` 取值：`image` / `document` / `audio` / `video` / `custom`。
- 图片默认上限 **10MB**；`number_limits` 是每条消息最多几张（本机「楠楠」为 3）。
- 允许的图片扩展名（本机实例）：`.JPG .JPEG .PNG .GIF .WEBP .SVG`。
- `/files/upload` 的 `file` part 必须带 MIME；不带会 415 `unsupported_file_type`。实测用 PowerShell 的 `-Form` 上传会变成 `application/octet-stream`，用 curl/requests 显式指定才得到 `image/png`。

### 2.2 光上传还不够：应用与工作流都得「接住」

官方文档明确指出（`zh/learn/tutorials/article-reader.md`、`zh/self-host/use-dify/nodes/llm.md`）：

1. 应用要在 **「功能」→ 文件上传** 里打开并勾选文件类型（图片）。开启后，对话中上传的文件进入系统变量 **`sys.files`**，且每次上传新文件都会**覆写**该变量。
2. 工作流的 **LLM 节点必须开启视觉（Vision）**，并让提示词引用文件变量（默认选择器 `userinput.files` / Chatflow 里即 `sys.files`）。
3. **模型本身要支持视觉**（如 qwen-vl 系列）。
4. 文档原话提醒的误区：**「LLM 是无法直接读取文件的」**——只把文件变量丢给 LLM 节点而没开视觉/没有多模态模型时，「LLM 读到的内容为空」。
5. 基础应用（Chatbot）则是在「功能」里选择多模态模型后，才出现 **视觉 / 音频 / 文档** 开关，并可设置分辨率（高/低细节）、上传方式、每条消息数量上限。

### 2.3 从 `/parameters` 读出应用当前能力

`GET {base}/parameters` 的 `file_upload` 字段就是上面「功能」面板的镜像：

```json
"file_upload": {
  "image": { "detail":"high", "enabled": true, "number_limits": 3,
             "transfer_methods": ["remote_url","local_file"] },
  "enabled": true, "allowed_file_types": ["image"],
  "allowed_file_extensions": [".JPG", ...], "number_limits": 3
}
```

## 3. 本机实例实测（`192.168.50.172:9098`）

### 3.1 实例与三个应用

- `GET /console/api/version?current_version=0.0.0` → `{"version":"1.16.1"}`（该接口回的是版本号；`/files/upload` 实测可用，说明文件 API 已支持）。
- `GET /v1/info` 三个 key 对应三个应用，**都是 `advanced-chat`（Chatflow）**：

| Key（`.env`） | 应用名 | 使用者 |
| --- | --- | --- |
| `AI_DIFY_API_KEY` | 楠楠 | `leo` |
| `AI_DIFY_CANCAN_API_KEY` | 星星 | `灿灿` |
| `AI_DIFY_ZHAOZHAO_API_KEY` | 豆豆 | 其他（含 `昭昭`） |

### 3.2 文件上传开关状态（`GET /parameters`）

- **楠楠**：`file_upload.enabled = false`，`image.enabled = false`；但 `allowed_file_types: ["image"]`、`allowed_file_upload_methods: ["local_file","remote_url"]`、`number_limits: 3` —— 即**类型已配好图片，只差把开关打开**。
- **星星 / 豆豆**：`file_upload: {}` —— 完全没配置。

### 3.3 端到端探测结果（用「楠楠」+ 探针 user + 1x1 PNG 70 字节）

1. `POST /files/upload` → **201 成功**，返回 `id`；显式指定 MIME 时 `mime_type: image/png`、`extension: png`。
2. `POST /chat-messages` 带 `files: [{type:image, transfer_method:local_file, upload_file_id:<id>}]` → **HTTP 200，不报错**，但流里 `workflow_started` 的 inputs 是 **`"sys.files":[]`** —— **文件被静默丢弃**，工作流照常跑完。
3. 换成正确的 `image/png` MIME 重测，`sys.files` 仍是 `[]`：**说明丢文件的原因是应用级 `file_upload.enabled=false`，与 MIME 无关**。
4. 探测会**自动新建一个会话**（说明「应用关着文件上传」时不是校验失败，而是直接忽略 files 继续跑）。

### 3.4 探测残留与清理

- 两次探测产生的会话已用 `DELETE /v1/conversations/{conversation_id}` 删除（204），复查该探针 user 会话数为 0。
- 遗留 **2 个 70 字节的图片文件记录**在 Dify 存储里：服务 API 没有删除文件的接口（只有 `/files/upload` 与 `/files/{file_id}/preview`），无法通过 API 清掉。影响可忽略。

## 4. 对本项目的落地路径

### 4.1 现状缺口

- 前端：已有「发送按钮右侧图片按钮 + 选图 + 预览」（本次已实现），但只停在本地预览。
- 服务端：`core/ai/ai_local.py` 的 `stream_msg()` 只发 `inputs / query / conversation_id / response_mode / user`，**没有 `files` 字段**；也没有转发 `/files/upload` 的端点。
- 传输：对话走 **socket.io**，而 socket.io 传不了二进制文件，图片必须另走一条 HTTP 上传通道。
- 身份：服务端发给 Dify 的 `user` 是 `data['user']`（前端 `globalVar.user.name`，见 `PageChat.vue`），上传文件时必须用**同一个** `user`。

### 4.2 打通所需改动

1. **Dify 控制台（人工，API 做不到）**
   - 「楠楠」应用：功能 → 文件上传 → 打开**图片**（类型已配好，只差开关）；「星星 / 豆豆」需要从零配置。
   - 确认工作流里的 **LLM 节点开启视觉**、模型是视觉模型、提示词引用了 `sys.files`。否则开了开关，LLM 依然读不到图。
2. **服务端**
   - 新增 `POST /chat/file` 之类的端点：收 multipart → 用同一个 `user` 转发到 Dify `/files/upload` → 返回 `upload_file_id`。
   - `stream_msg()` 增加 `files` 参数并透传；socket 消息里带上 file id 列表；注意 10MB / 3 张 / 扩展名白名单校验。
3. **前端**
   - 复用现有 `pendingImages`：发送时先 POST 到自家上传端点拿 id，再随消息发出。

### 4.3 备选方案（完全不动 Dify）

项目已有视觉能力：`server/core/ai/ocr_ali.py`（DashScope `qwen-vl-plus`）+ `/ai/ocr` 接口（见 TTS 任务的 OCR 用法）。
选图 → 调 OCR 取文字 → 结果填入输入框 → 用户确认后发送。**纯前端 + 现有接口即可闭环**，代价是「图片转文字」，不是真正的多模态对话（会丢版面/图像语义）。

## 5. 一句话建议

想要「真·多模态对话」就必须走 §4.2：**先在 Dify 控制台把「楠楠」的图片上传与 LLM 视觉配好**（这一步只能人工点），再加服务端上传转发 + `files` 透传；若不接受改 Dify 配置，则用 §4.3 的 OCR 方案。

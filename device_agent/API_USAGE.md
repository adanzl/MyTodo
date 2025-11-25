# Cron 定时任务 API 使用文档

## API 接口

### 1. 获取定时任务状态

**接口**: `GET /cron/status`

**描述**: 获取当前定时任务的配置和运行状态

**请求示例**:
```bash
curl http://localhost:5000/cron/status
```

**响应示例**:
```json
{
  "success": true,
  "data": {
    "running": true,
    "enabled": true,
    "cron_expression": "0 2 * * *",
    "command": "python /path/to/script.py",
    "jobs": [
      {
        "id": "cron_command_job",
        "name": "定时执行命令",
        "next_run_time": "2025-11-26T02:00:00+08:00"
      }
    ]
  }
}
```

---

### 2. 更新定时任务配置

**接口**: `POST /cron/update`

**描述**: 更新定时任务的配置并自动重启调度器

**请求参数**:
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| enabled | boolean | 否 | 是否启用定时任务 |
| expression | string | 否 | Cron 表达式（格式: 分 时 日 月 周） |
| command | string | 否 | 要执行的命令 |

**请求示例 1**: 更新 cron 表达式
```bash
curl -X POST http://localhost:5000/cron/update \
  -H "Content-Type: application/json" \
  -d '{
    "expression": "*/10 * * * *"
  }'
```

**请求示例 2**: 更新命令
```bash
curl -X POST http://localhost:5000/cron/update \
  -H "Content-Type: application/json" \
  -d '{
    "command": "python /home/orangepi/scripts/backup.py"
  }'
```

**请求示例 3**: 启用定时任务
```bash
curl -X POST http://localhost:5000/cron/update \
  -H "Content-Type: application/json" \
  -d '{
    "enabled": true
  }'
```

**请求示例 4**: 更新完整配置
```bash
curl -X POST http://localhost:5000/cron/update \
  -H "Content-Type: application/json" \
  -d '{
    "enabled": true,
    "expression": "0 3 * * *",
    "command": "python /home/orangepi/scripts/daily_backup.py"
  }'
```

**请求示例 5**: 禁用定时任务
```bash
curl -X POST http://localhost:5000/cron/update \
  -H "Content-Type: application/json" \
  -d '{
    "enabled": false
  }'
```

**响应示例** (成功):
```json
{
  "success": true,
  "message": "配置已更新",
  "data": {
    "running": true,
    "enabled": true,
    "cron_expression": "0 3 * * *",
    "command": "python /home/orangepi/scripts/daily_backup.py",
    "jobs": [
      {
        "id": "cron_command_job",
        "name": "定时执行命令",
        "next_run_time": "2025-11-26T03:00:00+08:00"
      }
    ]
  }
}
```

**响应示例** (失败):
```json
{
  "success": false,
  "error": "cron 表达式格式错误，应为 5 个字段（分 时 日 月 周）"
}
```

---

## 使用场景

### 场景 1: 每 5 分钟执行一次
```bash
curl -X POST http://localhost:5000/cron/update \
  -H "Content-Type: application/json" \
  -d '{
    "enabled": true,
    "expression": "*/5 * * * *",
    "command": "python /home/orangepi/scripts/sync.py"
  }'
```

### 场景 2: 每天凌晨 2 点备份数据库
```bash
curl -X POST http://localhost:5000/cron/update \
  -H "Content-Type: application/json" \
  -d '{
    "enabled": true,
    "expression": "0 2 * * *",
    "command": "bash /home/orangepi/scripts/backup_db.sh"
  }'
```

### 场景 3: 每周一早上 8 点执行
```bash
curl -X POST http://localhost:5000/cron/update \
  -H "Content-Type: application/json" \
  -d '{
    "enabled": true,
    "expression": "0 8 * * 1",
    "command": "python /home/orangepi/scripts/weekly_report.py"
  }'
```

### 场景 4: 工作日每 2 小时执行一次
```bash
curl -X POST http://localhost:5000/cron/update \
  -H "Content-Type: application/json" \
  -d '{
    "enabled": true,
    "expression": "0 */2 * * 1-5",
    "command": "python /home/orangepi/scripts/check_status.py"
  }'
```

### 场景 5: 临时禁用定时任务（不删除配置）
```bash
curl -X POST http://localhost:5000/cron/update \
  -H "Content-Type: application/json" \
  -d '{
    "enabled": false
  }'
```

---

## Python 客户端示例

### 获取状态
```python
import requests

response = requests.get('http://localhost:5000/cron/status')
data = response.json()

if data['success']:
    status = data['data']
    print(f"调度器运行: {status['running']}")
    print(f"任务启用: {status['enabled']}")
    print(f"Cron 表达式: {status['cron_expression']}")
    print(f"执行命令: {status['command']}")
    
    if status['jobs']:
        for job in status['jobs']:
            print(f"下次执行时间: {job['next_run_time']}")
```

### 更新配置
```python
import requests

# 更新配置
config = {
    'enabled': True,
    'expression': '0 2 * * *',
    'command': 'python /home/orangepi/scripts/backup.py'
}

response = requests.post(
    'http://localhost:5000/cron/update',
    json=config
)

data = response.json()
if data['success']:
    print("配置更新成功！")
    print(f"消息: {data['message']}")
else:
    print(f"更新失败: {data['error']}")
```

---

## JavaScript 客户端示例

### 使用 Fetch API
```javascript
// 获取状态
async function getCronStatus() {
  try {
    const response = await fetch('http://localhost:5000/cron/status');
    const data = await response.json();
    
    if (data.success) {
      console.log('调度器状态:', data.data);
      return data.data;
    }
  } catch (error) {
    console.error('获取状态失败:', error);
  }
}

// 更新配置
async function updateCronConfig(config) {
  try {
    const response = await fetch('http://localhost:5000/cron/update', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(config)
    });
    
    const data = await response.json();
    
    if (data.success) {
      console.log('配置更新成功:', data.message);
      return data.data;
    } else {
      console.error('更新失败:', data.error);
    }
  } catch (error) {
    console.error('更新配置失败:', error);
  }
}

// 使用示例
updateCronConfig({
  enabled: true,
  expression: '*/10 * * * *',
  command: 'python /path/to/script.py'
});
```

---

## 常见 Cron 表达式

| 表达式 | 说明 |
|--------|------|
| `* * * * *` | 每分钟执行 |
| `*/5 * * * *` | 每 5 分钟执行 |
| `0 * * * *` | 每小时执行 |
| `0 */2 * * *` | 每 2 小时执行 |
| `0 0 * * *` | 每天午夜执行 |
| `0 2 * * *` | 每天凌晨 2 点执行 |
| `0 12 * * *` | 每天中午 12 点执行 |
| `0 0 * * 0` | 每周日午夜执行 |
| `0 0 * * 1` | 每周一午夜执行 |
| `0 8 * * 1-5` | 周一到周五早上 8 点执行 |
| `0 0 1 * *` | 每月 1 号午夜执行 |
| `30 8 1 * *` | 每月 1 号早上 8:30 执行 |

---

## 错误处理

### 常见错误响应

1. **缺少请求数据**
```json
{
  "success": false,
  "error": "请提供配置数据"
}
```

2. **参数类型错误**
```json
{
  "success": false,
  "error": "enabled 参数必须是布尔值"
}
```

3. **Cron 表达式格式错误**
```json
{
  "success": false,
  "error": "cron 表达式格式错误，应为 5 个字段（分 时 日 月 周）"
}
```

4. **保存配置失败**
```json
{
  "success": false,
  "error": "保存配置失败"
}
```

5. **重启调度器失败**
```json
{
  "success": false,
  "error": "配置已保存，但重启调度器失败: [错误详情]"
}
```

---

## 注意事项

1. **配置立即生效**: 调用更新接口后，调度器会立即重启并应用新配置
2. **部分更新**: 可以只更新部分配置，未指定的参数保持不变
3. **配置持久化**: 所有配置都会保存到 `config.properties` 文件中
4. **时区**: 默认使用 `Asia/Shanghai` 时区
5. **命令执行**: 命令在 shell 环境中执行，支持管道、重定向等特性
6. **超时时间**: 命令执行超时时间为 5 分钟
7. **日志记录**: 所有执行结果都会记录在应用日志中

---

## 安全建议

1. 在生产环境中，建议添加认证机制保护 API
2. 验证命令的安全性，避免执行危险命令
3. 限制可执行命令的路径和权限
4. 定期检查日志文件，监控任务执行情况


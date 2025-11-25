# 定时任务使用说明

## 功能介绍

本系统支持通过配置文件设置定时任务（Cron Job），可以在指定的时间自动执行命令。

## 安装依赖

首先确保已安装 APScheduler：

```bash
pip install APScheduler==3.10.4
```

或者安装所有依赖：

```bash
pip install -r requirements.txt
```

## 配置说明

在项目根目录的 `config.properties` 文件中配置定时任务：

```properties
# 是否启用定时任务 (true/false)
cron.enabled=true

# Cron 表达式 (格式: 分 时 日 月 周)
cron.expression=0 2 * * *

# 要执行的命令
cron.command=python /path/to/your/script.py
```

### Cron 表达式格式

Cron 表达式由 5 个字段组成：`分 时 日 月 周`

| 字段 | 允许值 | 允许的特殊字符 |
|------|--------|----------------|
| 分   | 0-59   | * , - /        |
| 时   | 0-23   | * , - /        |
| 日   | 1-31   | * , - /        |
| 月   | 1-12   | * , - /        |
| 周   | 0-6    | * , - /        |

**注意**：周的范围是 0-6，其中 0 表示周日。

### 常用 Cron 表达式示例

```properties
# 每天凌晨2点执行
cron.expression=0 2 * * *

# 每5分钟执行一次
cron.expression=*/5 * * * *

# 每2小时执行一次
cron.expression=0 */2 * * *

# 每周日午夜执行
cron.expression=0 0 * * 0

# 周一到周五早上8:30执行
cron.expression=30 8 * * 1-5

# 每月1号凌晨3点执行
cron.expression=0 3 1 * *

# 每天中午12点执行
cron.expression=0 12 * * *
```

### 命令示例

```properties
# 执行 Python 脚本
cron.command=python /home/orangepi/scripts/backup.py

# 执行 Shell 脚本
cron.command=bash /home/orangepi/scripts/cleanup.sh

# 重启服务
cron.command=systemctl restart my-service

# 多个命令（使用分号分隔）
cron.command=cd /path/to/dir && python script.py && echo "Done"

# 带参数的命令
cron.command=python /home/orangepi/scripts/process.py --mode=daily --verbose
```

## 使用方法

### 1. 启用定时任务

编辑 `config.properties` 文件：

```properties
cron.enabled=true
cron.expression=0 2 * * *
cron.command=python /home/orangepi/scripts/daily_task.py
```

### 2. 启动应用

正常启动应用，定时任务会自动初始化并按计划执行：

```bash
python main.py
# 或使用 gunicorn
gunicorn -w 1 -b 0.0.0.0:5000 main:app
```

### 3. 查看定时任务状态

访问 API 接口查看定时任务状态：

```bash
curl http://localhost:5000/cron/status
```

返回示例：

```json
{
  "success": true,
  "data": {
    "running": true,
    "enabled": true,
    "cron_expression": "0 2 * * *",
    "command": "python /home/orangepi/scripts/daily_task.py",
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

### 4. 查看日志

定时任务的执行日志会记录在应用日志中，可以通过以下方式查看：

```bash
# 查看日志文件
tail -f logs/app.log

# 或访问 Web 日志页面
http://localhost:5000/log
```

## 日志内容

定时任务执行时会记录以下信息：

- 任务启动信息
- 命令执行开始
- 命令执行结果（成功/失败）
- 标准输出和错误输出
- 超时或异常信息

## 注意事项

1. **命令超时**：默认命令执行超时时间为 5 分钟，超时会自动终止
2. **时区设置**：默认使用 `Asia/Shanghai` 时区
3. **权限问题**：确保执行的命令有适当的权限
4. **路径问题**：使用绝对路径避免路径错误
5. **日志监控**：定期检查日志确保任务正常执行
6. **测试配置**：修改配置后建议先测试命令是否能正常执行

## 故障排查

### 任务没有执行

1. 检查 `cron.enabled` 是否为 `true`
2. 检查 cron 表达式格式是否正确
3. 查看应用日志是否有错误信息
4. 访问 `/cron/status` 接口查看任务状态

### 命令执行失败

1. 手动在终端执行命令测试
2. 检查命令路径是否正确（建议使用绝对路径）
3. 检查文件权限
4. 查看日志中的错误信息

### 时间不准确

1. 检查系统时间是否正确
2. 检查时区设置（默认为 Asia/Shanghai）
3. 验证 cron 表达式是否符合预期

## 动态修改配置

修改 `config.properties` 文件后，需要重启应用才能生效：

```bash
# 停止应用
pkill -f "python main.py"

# 启动应用
python main.py
```

## 示例：每天凌晨备份数据

```properties
cron.enabled=true
cron.expression=0 2 * * *
cron.command=python /home/orangepi/scripts/backup_database.py
```

这将在每天凌晨 2:00 执行数据库备份脚本。


# 定时任务调度器多次初始化问题修复

## 问题描述

在启动应用时，定时任务调度器被多次初始化，导致日志中出现重复的初始化信息：

```
2025-11-25 16:49:37,650 [INFO] [scheduler.py:100] 定时任务未启用 (cron.enabled=false)
2025-11-25 16:49:37,654 [INFO] [__init__.py:46] 定时任务调度器初始化完成
2025-11-25 16:49:37,761 [INFO] [scheduler.py:100] 定时任务未启用 (cron.enabled=false)
2025-11-25 16:49:37,762 [INFO] [scheduler.py:100] 定时任务未启用 (cron.enabled=false)
2025-11-25 16:49:37,764 [INFO] [__init__.py:46] 定时任务调度器初始化完成
2025-11-25 16:49:37,764 [INFO] [__init__.py:46] 定时任务调度器初始化完成
```

## 问题原因

1. **Flask 应用多次创建**: 在某些模式下（如 debug 模式、使用 gunicorn 等），Flask 的 `create_app()` 可能被多次调用
2. **缺少重复检查**: `scheduler.start()` 没有检查调度器是否已经在运行
3. **缺少线程安全**: `get_scheduler()` 单例模式没有线程锁保护

## 解决方案

### 1. 添加运行状态检查

在 `CronScheduler.start()` 方法中添加检查：

```python
def start(self):
    """启动调度器"""
    # 检查调度器是否已经在运行，避免重复启动
    if self.scheduler.running:
        log.debug("定时任务调度器已经在运行，跳过重复启动")
        return
    
    # ... 其余启动逻辑
```

### 2. 添加线程锁保护

使用双重检查锁定模式确保单例的线程安全：

```python
import threading

_scheduler_instance = None
_scheduler_lock = threading.Lock()

def get_scheduler() -> CronScheduler:
    """获取全局调度器实例（线程安全单例）"""
    global _scheduler_instance
    
    # 双重检查锁定模式
    if _scheduler_instance is None:
        with _scheduler_lock:
            if _scheduler_instance is None:
                log.debug("创建定时任务调度器实例")
                _scheduler_instance = CronScheduler()
    
    return _scheduler_instance
```

### 3. 优化初始化日志

只在真正启动时输出日志：

```python
# 启动定时任务调度器
try:
    scheduler = get_scheduler()
    was_running = scheduler.scheduler.running
    scheduler.start()
    # 只在首次启动时输出日志
    if not was_running and scheduler.scheduler.running:
        log.info("定时任务调度器已启动")
    elif not was_running and not scheduler.scheduler.running:
        log.debug("定时任务调度器已初始化（未启用）")
except Exception as e:
    log.error(f"定时任务调度器启动失败: {str(e)}")
```

## 修复后效果

应用启动后，只会看到一次初始化日志：

```
2025-11-25 17:00:00,123 [DEBUG] [scheduler.py:215] 创建定时任务调度器实例
2025-11-25 17:00:00,124 [INFO] [scheduler.py:100] 定时任务未启用 (cron.enabled=false)
2025-11-25 17:00:00,125 [DEBUG] [__init__.py:44] 定时任务调度器已初始化（未启用）
```

或者如果启用了定时任务：

```
2025-11-25 17:00:00,123 [DEBUG] [scheduler.py:215] 创建定时任务调度器实例
2025-11-25 17:00:00,124 [INFO] [scheduler.py:135] 定时任务已启动: cron=0 7 * * *, command=play_next_track
2025-11-25 17:00:00,125 [INFO] [__init__.py:44] 定时任务调度器已启动
```

## 技术细节

### 双重检查锁定（Double-Checked Locking）

这是一种常用的单例模式优化技术：

1. **第一次检查**（无锁）：快速检查实例是否已存在
2. **加锁**：如果不存在，获取锁
3. **第二次检查**（有锁）：再次确认实例是否已创建（可能其他线程已创建）
4. **创建实例**：如果确实不存在，则创建

这样可以避免每次获取实例都加锁的性能开销。

### APScheduler 的线程安全

`BackgroundScheduler` 本身是线程安全的，但我们的单例创建过程需要额外保护。

## 测试验证

启动应用后检查：

```bash
# 查看日志，确认只有一次初始化
curl http://localhost:5000/log | grep "调度器"

# 查看调度器状态
curl http://localhost:5000/cron/status
```

## 相关文件

- `core/scheduler.py` - 定时任务调度器
- `core/__init__.py` - Flask 应用初始化

## 版本信息

- **修复日期**: 2025-11-25
- **影响范围**: 定时任务模块
- **向后兼容**: ✅ 完全兼容，无需修改现有配置


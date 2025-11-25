# 故障排查指南

## 问题：Python 执行 mpg123 没有声音

### 症状

- ✅ 命令行手动执行 `mpg123 -a bluealsa:... file.mp3` 可以正常播放
- ❌ Python 通过 API 调用播放没有声音
- ❌ 或者 mpg123 进程立即退出

### 原因

Python subprocess 默认的环境变量不完整，缺少音频系统需要的关键环境变量：
- `XDG_RUNTIME_DIR` - 用户运行时目录
- `HOME` - 用户主目录
- `DBUS_SESSION_BUS_ADDRESS` - D-Bus 会话总线地址（某些音频系统需要）

### 解决方案

已在代码中实现以下修复：

1. **传递完整环境变量**
```python
env = os.environ.copy()  # 继承当前进程的所有环境变量
process = subprocess.Popen(cmd, env=env, ...)
```

2. **确保关键环境变量存在**
```python
if 'XDG_RUNTIME_DIR' not in env:
    env['XDG_RUNTIME_DIR'] = f"/run/user/{os.getuid()}"
if 'HOME' not in env:
    env['HOME'] = user_info.pw_dir
```

3. **在新会话中启动进程**
```python
start_new_session=True  # 避免继承父进程的信号处理
```

4. **检查进程是否立即退出**
```python
time.sleep(0.1)
if process.poll() is not None:
    # 进程已退出，读取错误信息
    stdout, stderr = process.communicate()
    log.error(f"mpg123 failed: {stderr}")
```

## 调试步骤

### 1. 检查系统环境

```bash
# 查看调试信息
curl http://localhost:5000/media/debug
```

返回的信息包括：
- 用户和组信息
- 环境变量
- mpg123 路径
- 蓝牙设备状态
- 当前播放状态

### 2. 检查用户权限

```bash
# 查看当前用户的组
groups

# 应该包含 audio 和 bluetooth 组
# 如果没有，添加：
sudo usermod -a -G audio $USER
sudo usermod -a -G bluetooth $USER

# 重新登录或重启服务生效
```

### 3. 检查环境变量

```bash
# 在应用运行的终端中检查
echo $XDG_RUNTIME_DIR
# 应该输出类似: /run/user/1000

echo $HOME
# 应该输出用户主目录

# 如果缺少，设置：
export XDG_RUNTIME_DIR=/run/user/$(id -u)
```

### 4. 测试 mpg123

```bash
# 直接测试
mpg123 -a bluealsa:HCI=hci0,DEV=58:EA:1F:1A:9A:8B,PROFILE=a2dp /path/to/file.mp3

# 查看详细输出
mpg123 -v -a bluealsa:HCI=hci0,DEV=58:EA:1F:1A:9A:8B,PROFILE=a2dp /path/to/file.mp3
```

### 5. 检查蓝牙设备连接

```bash
# 查看蓝牙设备状态
bluetoothctl info 58:EA:1F:1A:9A:8B

# 应该显示 "Connected: yes"
# 如果没有连接：
bluetoothctl connect 58:EA:1F:1A:9A:8B
```

### 6. 检查 bluealsa 服务

```bash
# 检查服务状态
systemctl status bluealsa

# 如果未运行，启动：
sudo systemctl start bluealsa
sudo systemctl enable bluealsa

# 查看日志
journalctl -u bluealsa -f
```

### 7. 查看应用日志

```bash
# 查看日志文件
tail -f logs/app.log

# 或通过 Web 界面
http://localhost:5000/log
```

查找关键错误信息：
- `mpg123 not found` - mpg123 未安装或不在 PATH 中
- `mpg123 exited immediately` - mpg123 启动失败
- `Bluetooth device not connected` - 蓝牙设备未连接
- `No bluealsa ALSA device found` - bluealsa 服务问题

## 常见问题

### Q1: 进程启动但没有声音

**可能原因**：
1. 蓝牙设备未连接或连接到错误的设备
2. 音量设置为 0
3. bluealsa 服务未运行

**解决方法**：
```bash
# 1. 检查蓝牙连接
bluetoothctl info <MAC_ADDRESS>

# 2. 检查音量（如果支持）
amixer

# 3. 重启 bluealsa
sudo systemctl restart bluealsa
```

### Q2: 权限被拒绝

**错误信息**: `Permission denied` 或 `Cannot access audio device`

**解决方法**：
```bash
# 将用户添加到 audio 组
sudo usermod -a -G audio $USER

# 重新登录或重启服务
```

### Q3: mpg123 找不到设备

**错误信息**: `Can't find audio device bluealsa:...`

**解决方法**：
```bash
# 1. 检查 bluealsa 服务
systemctl status bluealsa

# 2. 检查设备是否可用
aplay -L | grep bluealsa

# 3. 手动测试设备
mpg123 -a bluealsa /path/to/test.mp3
```

### Q4: 应用以 systemd 服务运行时没有声音

**原因**: systemd 服务默认没有用户会话环境

**解决方法**：

在 systemd 服务文件中添加：
```ini
[Service]
Type=simple
User=orangepi
Group=orangepi
WorkingDirectory=/home/orangepi/project/device_agent

# 添加环境变量
Environment="HOME=/home/orangepi"
Environment="XDG_RUNTIME_DIR=/run/user/1000"

# 确保用户组正确
SupplementaryGroups=audio bluetooth

ExecStart=/home/orangepi/project/device_agent/.venv/bin/python main.py
```

重新加载并重启服务：
```bash
sudo systemctl daemon-reload
sudo systemctl restart your-service
```

## 高级调试

### 使用 strace 跟踪

```bash
# 跟踪 Python 进程
strace -f -e trace=open,access,connect -p <PID>
```

### 检查音频设备访问

```bash
# 列出所有音频设备
ls -l /dev/snd/

# 检查权限
getfacl /dev/snd/controlC0
```

### 测试 ALSA 直接播放

```bash
# 使用 speaker-test 测试
speaker-test -D bluealsa -c 2 -t wav

# 使用 aplay 测试
aplay -D bluealsa test.wav
```

## 成功标志

播放成功时，日志应该显示：
```
[MEDIA] Target bluetooth device: 小爱音箱-7324 (58:EA:1F:1A:9A:8B)
[MEDIA] Using ALSA device: bluealsa:HCI=hci0,DEV=58:EA:1F:1A:9A:8B,PROFILE=a2dp
[MEDIA] Playing with mpg123: mpg123 -a bluealsa:HCI=hci0,DEV=58:EA:1F:1A:9A:8B,PROFILE=a2dp /path/to/file.mp3
[MEDIA] Started playback: /path/to/file.mp3 (PID: 12345)
```

## 预防措施

1. **确保正确的启动方式**
```bash
# 在用户会话中启动（推荐用于开发）
python main.py

# 或使用 gunicorn
gunicorn -w 1 -b 0.0.0.0:5000 main:app
```

2. **设置正确的环境**
```bash
# 在启动脚本中
export XDG_RUNTIME_DIR=/run/user/$(id -u)
export HOME=$HOME
```

3. **使用正确的用户运行**
```bash
# 不要使用 root 用户
# 使用有音频权限的普通用户
```

## 参考资料

- [bluez-alsa GitHub](https://github.com/Arkq/bluez-alsa)
- [ALSA Project](https://www.alsa-project.org/)
- [mpg123 Manual](https://www.mpg123.de/api/)


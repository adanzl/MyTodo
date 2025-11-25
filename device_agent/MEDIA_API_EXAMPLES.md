# 媒体播放 API 使用示例

## 快速开始

### 1. 查看可用的音频设备

```bash
curl http://localhost:5000/media/getAudioDevices
```

**响应示例**:
```json
{
  "code": 0,
  "msg": "ok",
  "data": {
    "devices": [
      {
        "name": "default",
        "description": "Default Audio Device",
        "is_bluetooth": false
      },
      {
        "name": "bluealsa:HCI=hci0,DEV=D4:DA:21:BA:81:67,PROFILE=a2dp",
        "description": "Bluetooth Audio ALSA Backend",
        "is_bluetooth": true
      },
      {
        "name": "bluealsa:HCI=hci0,DEV=58:EA:1F:1A:9A:8B,PROFILE=a2dp",
        "description": "Bluetooth Audio ALSA Backend",
        "is_bluetooth": true
      }
    ],
    "total": 3,
    "bluetooth_devices": [
      {
        "name": "bluealsa:HCI=hci0,DEV=D4:DA:21:BA:81:67,PROFILE=a2dp",
        "description": "Bluetooth Audio ALSA Backend",
        "is_bluetooth": true
      },
      {
        "name": "bluealsa:HCI=hci0,DEV=58:EA:1F:1A:9A:8B,PROFILE=a2dp",
        "description": "Bluetooth Audio ALSA Backend",
        "is_bluetooth": true
      }
    ]
  }
}
```

## 播放方式

### 方式 1: 直接播放单个文件（推荐）

**自动查找蓝牙设备**:
```bash
curl -X POST http://localhost:5000/media/play \
  -H "Content-Type: application/json" \
  -d '{
    "file_path": "/home/orangepi/Videos/xiaopingguo.mp3",
    "device_address": "D4:DA:21:BA:81:67"
  }'
```

**指定完整的 ALSA 设备名**:
```bash
curl -X POST http://localhost:5000/media/play \
  -H "Content-Type: application/json" \
  -d '{
    "file_path": "/home/orangepi/Videos/xiaopingguo.mp3",
    "alsa_device": "bluealsa:HCI=hci0,DEV=D4:DA:21:BA:81:67,PROFILE=a2dp"
  }'
```

**使用默认蓝牙设备**:
```bash
curl -X POST http://localhost:5000/media/play \
  -H "Content-Type: application/json" \
  -d '{
    "file_path": "/home/orangepi/Videos/xiaopingguo.mp3"
  }'
```

**响应示例**:
```json
{
  "code": 0,
  "msg": "Playing",
  "data": {
    "file": "xiaopingguo.mp3",
    "pid": 12345,
    "alsa_device": "bluealsa:HCI=hci0,DEV=D4:DA:21:BA:81:67,PROFILE=a2dp",
    "bluetooth_device": {
      "address": "D4:DA:21:BA:81:67",
      "name": "小爱触屏音箱-9750",
      "connected": true
    }
  }
}
```

### 方式 2: 播放目录中的音频文件

```bash
curl -X POST http://localhost:5000/media/playDir \
  -H "Content-Type: application/json" \
  -d '{
    "path": "/home/orangepi/Videos",
    "device_address": "D4:DA:21:BA:81:67"
  }'
```

**响应示例**:
```json
{
  "code": 0,
  "msg": "ok",
  "data": {
    "directory": "/home/orangepi/Videos",
    "bluetooth_device": {
      "address": "D4:DA:21:BA:81:67",
      "name": "小爱触屏音箱-9750",
      "connected": true
    },
    "media_files": [
      {
        "name": "xiaopingguo.mp3",
        "path": "/home/orangepi/Videos/xiaopingguo.mp3",
        "size": 1234567
      }
    ],
    "total_files": 1,
    "play_results": [
      {
        "file": "xiaopingguo.mp3",
        "result": {
          "code": 0,
          "msg": "Playing",
          "file": "xiaopingguo.mp3",
          "pid": 12345
        }
      }
    ]
  }
}
```

## 停止播放

```bash
curl -X POST http://localhost:5000/media/stop
```

**响应示例**:
```json
{
  "code": 0,
  "msg": "Playback stopped"
}
```

## 完整工作流程示例

### 场景：播放音频到特定的蓝牙音箱

```bash
# 1. 查看可用的蓝牙音频设备
curl http://localhost:5000/media/getAudioDevices | jq '.data.bluetooth_devices'

# 2. 播放音频文件
curl -X POST http://localhost:5000/media/play \
  -H "Content-Type: application/json" \
  -d '{
    "file_path": "/home/orangepi/Videos/xiaopingguo.mp3",
    "device_address": "D4:DA:21:BA:81:67"
  }'

# 3. 等待播放...

# 4. 停止播放
curl -X POST http://localhost:5000/media/stop
```

## Python 客户端示例

### 基础播放

```python
import requests

# 播放音频文件
response = requests.post(
    'http://localhost:5000/media/play',
    json={
        'file_path': '/home/orangepi/Videos/xiaopingguo.mp3',
        'device_address': 'D4:DA:21:BA:81:67'
    }
)

result = response.json()
if result['code'] == 0:
    print(f"正在播放: {result['data']['file']}")
    print(f"ALSA 设备: {result['data']['alsa_device']}")
    print(f"进程 ID: {result['data']['pid']}")
else:
    print(f"播放失败: {result['msg']}")
```

### 高级播放控制

```python
import requests
import time

class BluetoothAudioPlayer:
    def __init__(self, base_url='http://localhost:5000'):
        self.base_url = base_url
    
    def get_bluetooth_devices(self):
        """获取所有蓝牙音频设备"""
        response = requests.get(f'{self.base_url}/media/getAudioDevices')
        data = response.json()
        if data['code'] == 0:
            return data['data']['bluetooth_devices']
        return []
    
    def play(self, file_path, device_address=None, alsa_device=None):
        """播放音频文件"""
        payload = {'file_path': file_path}
        if device_address:
            payload['device_address'] = device_address
        if alsa_device:
            payload['alsa_device'] = alsa_device
        
        response = requests.post(
            f'{self.base_url}/media/play',
            json=payload
        )
        return response.json()
    
    def stop(self):
        """停止播放"""
        response = requests.post(f'{self.base_url}/media/stop')
        return response.json()
    
    def play_to_device(self, file_path, device_mac):
        """播放音频到指定的蓝牙设备"""
        print(f"开始播放: {file_path}")
        print(f"目标设备: {device_mac}")
        
        result = self.play(file_path, device_address=device_mac)
        
        if result['code'] == 0:
            print(f"✓ 播放成功")
            print(f"  文件: {result['data']['file']}")
            print(f"  ALSA 设备: {result['data']['alsa_device']}")
            if result['data'].get('bluetooth_device'):
                bt_device = result['data']['bluetooth_device']
                print(f"  蓝牙设备: {bt_device['name']} ({bt_device['address']})")
            return True
        else:
            print(f"✗ 播放失败: {result['msg']}")
            return False

# 使用示例
player = BluetoothAudioPlayer()

# 查看可用设备
print("可用的蓝牙音频设备:")
devices = player.get_bluetooth_devices()
for i, device in enumerate(devices):
    print(f"{i+1}. {device['name']}")

# 播放音频
player.play_to_device(
    '/home/orangepi/Videos/xiaopingguo.mp3',
    'D4:DA:21:BA:81:67'
)

# 等待一段时间
time.sleep(30)

# 停止播放
player.stop()
```

## 命令行等效操作

### 使用 mpg123 直接播放

```bash
# 查看所有 ALSA 设备
aplay -L

# 直接使用 mpg123 播放
mpg123 -a bluealsa:HCI=hci0,DEV=D4:DA:21:BA:81:67,PROFILE=a2dp \
  /home/orangepi/Videos/xiaopingguo.mp3

# 后台播放
mpg123 -a bluealsa:HCI=hci0,DEV=D4:DA:21:BA:81:67,PROFILE=a2dp \
  /home/orangepi/Videos/xiaopingguo.mp3 &

# 停止播放
killall mpg123
```

## 常见问题

### Q: 如何知道我的蓝牙设备地址？

```bash
# 方法 1: 使用 bluetoothctl
bluetoothctl paired-devices

# 方法 2: 使用 API
curl http://localhost:5000/bluetooth/paired
```

### Q: 播放失败，提示 "No bluealsa device found"

**解决方案**:
1. 确保 bluealsa 服务正在运行：
```bash
sudo systemctl status bluealsa
sudo systemctl start bluealsa
```

2. 确保蓝牙设备已连接：
```bash
bluetoothctl connect D4:DA:21:BA:81:67
```

3. 检查 ALSA 设备：
```bash
aplay -L | grep bluealsa
```

### Q: 如何播放到默认蓝牙设备？

不指定 `device_address` 即可：
```bash
curl -X POST http://localhost:5000/media/play \
  -H "Content-Type: application/json" \
  -d '{
    "file_path": "/home/orangepi/Videos/xiaopingguo.mp3"
  }'
```

### Q: 支持哪些音频格式？

支持的格式（取决于系统编解码器）：
- MP3 ✓ (推荐)
- WAV ✓
- OGG ✓
- FLAC ✓
- M4A ✓
- AAC ✓
- WMA ✓

### Q: 如何同时连接多个蓝牙音箱？

当前实现一次只能播放到一个设备。如果需要多设备播放，需要：
1. 多次调用 API，分别指定不同的 `device_address`
2. 或在系统级别配置音频镜像

## 进阶用法

### 使用完整的 ALSA 设备名称

如果你已经知道完整的 ALSA 设备名称（通过 `aplay -L` 获取），可以直接指定：

```bash
curl -X POST http://localhost:5000/media/play \
  -H "Content-Type: application/json" \
  -d '{
    "file_path": "/home/orangepi/Videos/xiaopingguo.mp3",
    "alsa_device": "bluealsa:HCI=hci0,DEV=D4:DA:21:BA:81:67,PROFILE=a2dp"
  }'
```

这样可以跳过设备查找步骤，直接播放。

### 批量播放

```python
import requests
import time
import os

# 要播放的音频文件列表
audio_files = [
    '/home/orangepi/Videos/song1.mp3',
    '/home/orangepi/Videos/song2.mp3',
    '/home/orangepi/Videos/song3.mp3',
]

device_address = 'D4:DA:21:BA:81:67'

for file_path in audio_files:
    print(f"正在播放: {os.path.basename(file_path)}")
    
    response = requests.post(
        'http://localhost:5000/media/play',
        json={
            'file_path': file_path,
            'device_address': device_address
        }
    )
    
    result = response.json()
    if result['code'] == 0:
        print(f"  ✓ 开始播放")
        # 等待播放完成（这里简单等待固定时间，实际应该获取文件长度）
        time.sleep(180)  # 等待 3 分钟
    else:
        print(f"  ✗ 失败: {result['msg']}")
    
    # 停止当前播放
    requests.post('http://localhost:5000/media/stop')
    time.sleep(1)

print("播放完成！")
```

## 性能优化

### 减少延迟

1. 使用有线连接代替蓝牙（如果可能）
2. 减少蓝牙设备与主机的距离
3. 使用支持低延迟编解码器的设备（aptX、LDAC）

### 提高稳定性

1. 信任蓝牙设备以确保自动重连：
```bash
bluetoothctl trust D4:DA:21:BA:81:67
```

2. 设置 bluealsa 服务开机自启：
```bash
sudo systemctl enable bluealsa
```

3. 使用高质量的音频文件（推荐 MP3 192kbps+）

## 日志调试

查看应用日志：
```bash
# 查看实时日志
tail -f logs/app.log

# 或通过 Web 界面
open http://localhost:5000/log
```

查看 bluealsa 日志：
```bash
journalctl -u bluealsa -f
```

查看系统蓝牙日志：
```bash
journalctl -u bluetooth -f
```

## 总结

- **推荐使用** `POST /media/play` 接口播放单个文件
- **自动检测** bluealsa 设备，无需手动配置
- **支持多种格式**，MP3 兼容性最好
- **简单集成**，RESTful API 易于使用


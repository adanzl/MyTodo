#!/bin/bash

# 播放列表功能完整配置示例
# 此脚本演示如何配置播放列表并启用定时播放

API_URL="http://localhost:5000"

echo "=========================================="
echo "播放列表功能配置示例"
echo "=========================================="
echo ""

# 步骤 1: 检查蓝牙设备
echo "1. 检查已配对的蓝牙设备..."
curl -s "${API_URL}/bluetooth/paired" | python3 -m json.tool
echo ""
echo "请记下要使用的蓝牙设备地址（例如: 58:EA:1F:1A:9A:8B）"
echo ""

# 步骤 2: 配置播放列表
echo "2. 配置播放列表..."
echo "请根据实际情况修改以下音乐文件路径和蓝牙设备地址："
echo ""

cat << 'EOF' > /tmp/playlist_config.json
{
  "playlist": [
    "/home/orangepi/Videos/song1.mp3",
    "/home/orangepi/Videos/song2.mp3",
    "/home/orangepi/Videos/song3.mp3"
  ],
  "device_address": "58:EA:1F:1A:9A:8B"
}
EOF

echo "配置文件内容："
cat /tmp/playlist_config.json | python3 -m json.tool
echo ""

read -p "按 Enter 继续上传配置，或按 Ctrl+C 取消..."

curl -X POST "${API_URL}/playlist/update" \
  -H "Content-Type: application/json" \
  -d @/tmp/playlist_config.json | python3 -m json.tool

echo ""
echo ""

# 步骤 3: 查看播放列表状态
echo "3. 查看播放列表状态..."
curl -s "${API_URL}/playlist/status" | python3 -m json.tool
echo ""
echo ""

# 步骤 4: 配置定时任务
echo "4. 配置定时任务（每天早上 7:00 播放）..."
curl -X POST "${API_URL}/cron/update" \
  -H "Content-Type: application/json" \
  -d '{
    "enabled": true,
    "expression": "0 7 * * *",
    "command": "play_next_track"
  }' | python3 -m json.tool

echo ""
echo ""

# 步骤 5: 查看定时任务状态
echo "5. 查看定时任务状态..."
curl -s "${API_URL}/cron/status" | python3 -m json.tool
echo ""
echo ""

echo "=========================================="
echo "配置完成！"
echo "=========================================="
echo ""
echo "现在系统将在每天早上 7:00 自动播放播放列表中的歌曲。"
echo "每次播放后，会自动记录播放进度，下次播放时继续下一首。"
echo ""
echo "常用命令："
echo "  - 查看播放列表状态: curl ${API_URL}/playlist/status"
echo "  - 查看定时任务状态: curl ${API_URL}/cron/status"
echo "  - 手动测试播放: cd /home/orangepi/project/MyTodo/device_agent && python3 -m core.playlist_player"
echo ""
echo "如需修改定时表达式，参考 Cron 表达式格式："
echo "  - 每天早上 7:00:     0 7 * * *"
echo "  - 每天早上 6:30:     30 6 * * *"
echo "  - 每 2 小时:         0 */2 * * *"
echo "  - 周一到周五 7:00:   0 7 * * 1-5"
echo ""


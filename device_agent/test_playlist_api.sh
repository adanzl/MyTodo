#!/bin/bash

# 播放列表 API 测试脚本
# 演示如何使用播放列表相关的 API 接口

API_URL="http://localhost:5000"

echo "=========================================="
echo "播放列表 API 测试"
echo "=========================================="
echo ""

# 1. 配置播放列表
echo "1. 配置播放列表..."
curl -X POST "${API_URL}/playlist/update" \
  -H "Content-Type: application/json" \
  -d '{
    "playlist": [
      "/home/orangepi/Videos/song1.mp3",
      "/home/orangepi/Videos/song2.mp3",
      "/home/orangepi/Videos/song3.mp3"
    ],
    "device_address": "58:EA:1F:1A:9A:8B"
  }' | python3 -m json.tool

echo ""
echo ""

# 2. 查看播放列表状态
echo "2. 查看播放列表状态..."
curl -s "${API_URL}/playlist/status" | python3 -m json.tool

echo ""
echo ""

# 3. 播放当前歌曲
echo "3. 播放当前歌曲（第 1 首）..."
read -p "按 Enter 继续播放..."
curl -X POST "${API_URL}/playlist/play" | python3 -m json.tool

echo ""
echo ""
echo "⏸️  等待 3 秒..."
sleep 3

# 4. 播放下一首
echo "4. 播放下一首歌曲（第 2 首）..."
curl -X POST "${API_URL}/playlist/playNext" | python3 -m json.tool

echo ""
echo ""
echo "⏸️  等待 3 秒..."
sleep 3

# 5. 再播放下一首
echo "5. 再播放下一首歌曲（第 3 首）..."
curl -X POST "${API_URL}/playlist/playNext" | python3 -m json.tool

echo ""
echo ""
echo "⏸️  等待 3 秒..."
sleep 3

# 6. 再播放下一首（应该循环到第 1 首）
echo "6. 再播放下一首歌曲（循环到第 1 首）..."
curl -X POST "${API_URL}/playlist/playNext" | python3 -m json.tool

echo ""
echo ""

# 7. 查看最终状态
echo "7. 查看最终播放列表状态..."
curl -s "${API_URL}/playlist/status" | python3 -m json.tool

echo ""
echo ""
echo "=========================================="
echo "测试完成！"
echo "=========================================="
echo ""
echo "注意："
echo "  - 每次播放会在后台启动新的 mpg123 进程"
echo "  - 可以使用 'ps aux | grep mpg123' 查看播放进程"
echo "  - 可以使用 POST /media/stop 停止当前播放"
echo ""


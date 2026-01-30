#!/bin/bash

# 部署脚本：构建前端并复制到 static 目录

set -e  # 遇到错误立即退出

echo "🚀 开始部署前端项目..."

# 进入前端目录
cd "$(dirname "$0")/../frontend"

# 构建前端项目
echo "📦 正在构建前端项目..."
npm run build

# 检查构建是否成功
if [ ! -d "dist" ]; then
    echo "❌ 错误: 构建失败，dist 目录不存在"
    exit 1
fi

# 返回项目根目录
cd ..

# 复制 index.html
echo "📝 复制 index.html..."
cp -f frontend/dist/index.html static/index.html

# 复制 assets 目录
if [ -d "frontend/dist/assets" ]; then
    echo "📁 复制 assets 目录..."
    rm -rf static/assets
    cp -r frontend/dist/assets static/
    echo "✅ assets 目录已复制"
else
    echo "⚠️  未找到 assets 目录"
fi

# 复制 favicon.ico（如果存在）
if [ -f "frontend/dist/favicon.ico" ]; then
    echo "🎨 复制 favicon.ico..."
    cp -f frontend/dist/favicon.ico static/favicon.ico
fi

echo "🎉 部署完成！"


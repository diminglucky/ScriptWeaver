#!/bin/bash

echo "=================================="
echo "🚀 AI Story Creator Pro"
echo "=================================="

# 检查是否有旧进程
OLD_PID=$(ps aux | grep "python.*run_modern_app\|python.*start_app\|python.*启动应用" | grep -v grep | awk '{print $2}')

if [ ! -z "$OLD_PID" ]; then
    echo "⚠️  发现旧进程: $OLD_PID"
    echo "正在清理..."
    kill $OLD_PID 2>/dev/null
    sleep 1
fi

# 启动应用
echo "正在启动应用..."
python run_modern_app.py

echo "=================================="

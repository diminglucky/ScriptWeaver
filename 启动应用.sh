#!/bin/bash
# AI Story Creator Pro 快速启动脚本

echo "🎨 AI Story Creator Pro - 智能故事创作平台"
echo "=========================================="
echo ""
echo "正在启动应用..."
echo ""

# 检查Python版本
python_version=$(python --version 2>&1 | awk '{print $2}')
echo "✓ Python版本: $python_version"

# 检查依赖
if ! python -c "import tkinter" 2>/dev/null; then
    echo "❌ 错误: 未安装tkinter"
    echo "   请安装: brew install python-tk (macOS)"
    exit 1
fi

# 启动应用
echo ""
echo "✨ 启动现代化UI界面..."
echo ""

python run_modern_app.py

echo ""
echo "应用已关闭"


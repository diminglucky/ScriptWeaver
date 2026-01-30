#!/bin/bash
# 使用conda work环境启动AI Story Creator Pro

echo "🎨 AI Story Creator Pro - 智能故事创作平台"
echo "=========================================="
echo ""
echo "📦 激活conda work环境..."

# 激活conda环境
source ~/miniforge3/etc/profile.d/conda.sh
conda activate work

# 检查Python版本
echo "✓ Python版本: $(python --version)"
echo ""

# 检查关键依赖
echo "📚 检查依赖包..."
python -c "import openai; print('✓ openai:', openai.__version__)"
python -c "import faiss; print('✓ faiss-cpu: 已安装')"
python -c "import sentence_transformers; print('✓ sentence-transformers:', sentence_transformers.__version__)"
python -c "from PIL import Image; print('✓ Pillow: 已安装')"
python -c "import tkinter; print('✓ tkinter: 已安装')"
echo ""

# 启动应用
echo "✨ 启动现代化UI界面..."
echo "=========================================="
echo ""

python run_modern_app.py

echo ""
echo "应用已关闭"

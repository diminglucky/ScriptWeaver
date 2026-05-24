#!/bin/bash
# 使用conda work环境启动ScriptWeaver

echo "🎨 ScriptWeaver - 智能故事创作平台"
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

LAUNCH_PY="python"
if [[ "$(uname -s)" == "Darwin" ]]; then
  CUR_VER="$(python -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")' 2>/dev/null || true)"
  if [[ "${CUR_VER}" == "3.12" ]]; then
    if command -v /opt/homebrew/bin/python3.11 >/dev/null 2>&1; then
      LAUNCH_PY="/opt/homebrew/bin/python3.11"
      echo "⚠ 检测到当前环境 Python 3.12，自动切换到 ${LAUNCH_PY} 以避免 Tk 闪退。"
    elif command -v python3.11 >/dev/null 2>&1; then
      LAUNCH_PY="python3.11"
      echo "⚠ 检测到当前环境 Python 3.12，自动切换到 ${LAUNCH_PY} 以避免 Tk 闪退。"
    else
      echo "⚠ 当前是 Python 3.12 且未发现 Python 3.11，可能出现 Tk 闪退。"
      echo "  可先安装 Python 3.11，或设置 STORY_PYTHON=/path/to/python3.11。"
    fi
  fi
fi

"${LAUNCH_PY}" run_modern_app.py

echo ""
echo "应用已关闭"

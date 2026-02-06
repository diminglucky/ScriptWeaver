#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI Story Creator Pro - 启动脚本（避免死锁）
"""
import os
import sys
from pathlib import Path

# 设置环境变量（在导入任何其他模块之前）
os.environ.setdefault("TRANSFORMERS_NO_TF", "1")
os.environ.setdefault("USE_TF", "0")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

# 设置 UTF-8 编码
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# 添加项目根目录到路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

print("=" * 80)
print("🚀 AI Story Creator Pro")
print("=" * 80)

# 加载环境变量
from dotenv import load_dotenv
load_dotenv(override=True)

# 显示配置
outline_api = os.getenv("STORY_OUTLINE_GEN_API", "未设置")
story_api = os.getenv("STORY_STORY_GEN_API", "未设置")
print(f"📝 目录生成 API: {outline_api}")
print(f"📝 故事生成 API: {story_api}")
print("=" * 80)
print("正在启动应用...")

# 延迟导入，避免死锁
if __name__ == "__main__":
    # 在主线程中导入
    from src.gui.modern_app import ModernApp
    
    print("✅ 应用已加载，正在启动界面...")
    app = ModernApp()
    app.mainloop()

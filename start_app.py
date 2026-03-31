#!/usr/bin/env python3
import os
from dotenv import load_dotenv

# 强制加载环境变量
load_dotenv(override=True)

# 验证配置
outline_api = os.getenv("STORY_OUTLINE_GEN_API", "未设置")
story_api = os.getenv("STORY_STORY_GEN_API", "未设置")

print("=" * 70)
print("🚀 启动 AI Story Creator Pro")
print("=" * 70)
print(f"📝 目录生成 API: {outline_api}")
print(f"📝 故事生成 API: {story_api}")
print("=" * 70)

# 启动应用
from src.gui.modern_app import ModernApp

if __name__ == "__main__":
    app = ModernApp()
    app.mainloop()

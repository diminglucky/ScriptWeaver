#!/usr/bin/env python3
"""
启动现代化UI版本 - AI Story Creator Pro
"""
import os
import sys
from pathlib import Path

# 禁用不必要的警告
os.environ.setdefault("TRANSFORMERS_NO_TF", "1")
os.environ.setdefault("USE_TF", "0")

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def main():
    """主函数"""
    try:
        # 尝试导入现代化UI
        from src.gui.modern_app import ModernApp
        print("🚀 启动 AI Story Creator Pro (现代化UI版本)...")
        app = ModernApp()
        app.mainloop()
    except ImportError as e:
        print(f"⚠️ 无法加载现代化UI: {e}")
        print("正在回退到经典版本...")
        
        # 回退到经典版本
        from src.gui_app import App
        app = App()
        app.mainloop()

if __name__ == "__main__":
    main()

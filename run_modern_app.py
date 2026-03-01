#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
启动现代化UI版本 - AI Story Creator Pro
"""
import os
import sys
from pathlib import Path

# 设置Windows控制台UTF-8编码
if sys.platform == "win32":
    import io
    if hasattr(sys.stdout, "buffer"):
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    if hasattr(sys.stderr, "buffer"):
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# 禁用不必要的警告
os.environ.setdefault("TRANSFORMERS_NO_TF", "1")
os.environ.setdefault("USE_TF", "0")

# 添加项目根目录到Python路径
project_root = Path(__file__).resolve().parent
os.chdir(project_root)
sys.path.insert(0, str(project_root))

def main():
    """主函数"""
    try:
        # 尝试导入现代化UI
        from src.gui.modern_app import ModernApp
        print("[INFO] 启动 AI Story Creator Pro (现代化UI版本)...")
        app = ModernApp()
        app.mainloop()
    except Exception as e:
        print(f"[WARN] 无法加载现代化UI: {e}")
        print("[INFO] 正在回退到经典版本...")
        
        # 回退到经典版本
        from src.gui_app import App
        app = App()
        app.mainloop()

if __name__ == "__main__":
    main()

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
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# 禁用不必要的警告
os.environ.setdefault("TRANSFORMERS_NO_TF", "1")
os.environ.setdefault("USE_TF", "0")

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def main():
    """主函数"""
    try:
        # 使用现代化UI - 保留所有功能
        from src.gui.modern_app import ModernApp
        print("启动 AI Story Creator Pro...")
        print("窗口尺寸: 1500x850")
        print("设计风格: 精致 · 简约 · 专业")
        print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        app = ModernApp()
        app.mainloop()
    except ImportError as e:
        print(f"❌ 无法加载现代化UI: {e}")
        print("\n请检查以下内容:")
        print("1. 是否安装了所有依赖: pip install -r requirements.txt")
        print("2. 是否在正确的目录运行")
        print("3. 查看错误信息并修复")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n\n用户中断，正在退出...")
        sys.exit(0)
    except Exception as e:
        print(f"❌ 程序运行出错: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()


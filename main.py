#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI Story Creator Pro - 主程序入口
使用现代化UI
"""
from __future__ import annotations

import sys
from pathlib import Path
from dotenv import load_dotenv

# 添加项目根目录到路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.gui.modern_app import ModernApp


def main() -> None:
	"""主函数"""
	load_dotenv()
	print("🚀 启动 AI Story Creator Pro - Modern Edition")
	app = ModernApp()
	app.mainloop()


if __name__ == "__main__":
	main()

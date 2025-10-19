from __future__ import annotations

# 兼容入口：优先新架构，失败回退到modern_app
try:
	from src.gui.main_window import App  # 新的模块化主窗口
except Exception:
	# 回退到modern_app
	from src.gui.modern_app import ModernApp as App

__all__ = ["App"]

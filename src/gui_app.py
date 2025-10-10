from __future__ import annotations

# 兼容入口：优先新架构，失败回退到备份
try:
	from src.gui.main_window import App  # 新的模块化主窗口
except Exception:
	from src.gui_app_backup import App  # 回退到原始实现

__all__ = ["App"]

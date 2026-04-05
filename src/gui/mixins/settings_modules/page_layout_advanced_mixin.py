"""Advanced settings tab layout builders."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from ...theme import Theme


class SettingsPageLayoutAdvancedMixin:
    """Build advanced settings and about sections."""
    def _build_advanced_settings_tab(self, scrollable_frame: tk.Frame) -> None:
        """构建“高级”标签页内容。"""
        # ========== 7. 高级选项 ==========
        grp_advanced = ttk.LabelFrame(scrollable_frame, text="🔧 高级选项", padding=(15, 10))
        grp_advanced.pack(fill="x", padx=15, pady=(10, 10))
        
        advanced_options_frame = tk.Frame(grp_advanced, bg=Theme.BG_SECONDARY)
        advanced_options_frame.pack(fill="x", padx=8, pady=8)
        
        # 主题切换
        theme_frame = tk.Frame(advanced_options_frame, bg=Theme.BG_SECONDARY)
        theme_frame.pack(fill="x", pady=5)
        tk.Label(theme_frame, text="界面主题:", bg=Theme.BG_SECONDARY, fg=Theme.TEXT_PRIMARY, font=("", 11, "bold")).pack(side="left")
        tk.Button(theme_frame, text="🌙 深色主题", command=self._set_dark_theme, bg="#374151", fg=Theme.TEXT_PRIMARY,
                  relief=tk.FLAT, cursor="hand2", padx=10).pack(side="left", padx=(10, 5))
        tk.Button(theme_frame, text="☀️ 浅色主题", command=self._set_light_theme, bg="#F1F5F9", fg="#1E293B",
                  relief=tk.FLAT, cursor="hand2", padx=10).pack(side="left", padx=5)
        
        # 配置导入导出
        config_frame = tk.Frame(advanced_options_frame, bg=Theme.BG_SECONDARY)
        config_frame.pack(fill="x", pady=5)
        tk.Label(config_frame, text="配置管理:", bg=Theme.BG_SECONDARY, fg=Theme.TEXT_PRIMARY, font=("", 11, "bold")).pack(side="left")
        tk.Button(config_frame, text="📥 导入配置", command=self._import_config_ui, bg="#3B82F6", fg=Theme.TEXT_PRIMARY,
                  relief=tk.FLAT, cursor="hand2", padx=10).pack(side="left", padx=(10, 5))
        tk.Button(config_frame, text="📤 导出配置", command=self._export_config_ui, bg="#10B981", fg=Theme.TEXT_PRIMARY,
                  relief=tk.FLAT, cursor="hand2", padx=10).pack(side="left", padx=5)
        tk.Button(config_frame, text="📤 导出(含密钥)", command=self._export_config_with_keys, bg="#F59E0B", fg=Theme.TEXT_PRIMARY,
                  relief=tk.FLAT, cursor="hand2", padx=10).pack(side="left", padx=5)
        
        # 缓存管理
        cache_frame = tk.Frame(advanced_options_frame, bg=Theme.BG_SECONDARY)
        cache_frame.pack(fill="x", pady=5)
        tk.Label(cache_frame, text="缓存管理:", bg=Theme.BG_SECONDARY, fg=Theme.TEXT_PRIMARY, font=("", 11, "bold")).pack(side="left")
        tk.Button(cache_frame, text="🗑️ 清除缓存", command=self._clear_cache_ui, bg="#EF4444", fg=Theme.TEXT_PRIMARY,
                  relief=tk.FLAT, cursor="hand2", padx=10).pack(side="left", padx=(10, 5))
        self.cache_size_label = tk.Label(cache_frame, text="缓存大小: 计算中...", bg=Theme.BG_SECONDARY, fg=Theme.TEXT_SECONDARY)
        self.cache_size_label.pack(side="left", padx=10)
        self.after(500, self._update_cache_size)
        
        # 快捷键提示
        shortcut_frame = tk.Frame(advanced_options_frame, bg=Theme.BG_SECONDARY)
        shortcut_frame.pack(fill="x", pady=5)
        tk.Label(shortcut_frame, text="快捷键:", bg=Theme.BG_SECONDARY, fg=Theme.TEXT_PRIMARY, font=("", 11, "bold")).pack(side="left")
        tk.Button(shortcut_frame, text="⌨️ 查看快捷键", command=self._show_shortcuts_ui, bg="#6366F1", fg=Theme.TEXT_PRIMARY,
                  relief=tk.FLAT, cursor="hand2", padx=10).pack(side="left", padx=(10, 5))
        tk.Label(shortcut_frame, text="提示: Ctrl+T切换主题, Ctrl+S保存, F1帮助", bg=Theme.BG_SECONDARY, fg=Theme.TEXT_SECONDARY,
                 font=("", 9)).pack(side="left", padx=10)
        
        # ========== 7. 关于 ==========
        grp_about = ttk.LabelFrame(scrollable_frame, text="ℹ️ 关于", padding=(15, 10))
        grp_about.pack(fill="x", padx=15, pady=(10, 20))
        
        about_frame = tk.Frame(grp_about, bg=Theme.BG_SECONDARY)
        about_frame.pack(fill="x", padx=8, pady=8)
        
        tk.Label(about_frame, text="AI Story Creator Pro v2.0", bg=Theme.BG_SECONDARY, fg=Theme.TEXT_PRIMARY,
                 font=("", 14, "bold")).pack(anchor="w")
        tk.Label(about_frame, text="智能故事创作平台 - 支持多种AI提供商", bg=Theme.BG_SECONDARY, fg=Theme.TEXT_SECONDARY).pack(anchor="w", pady=2)
        tk.Label(about_frame, text="支持的AI: OpenAI, Gemini, Claude, DeepSeek, 通义, 文心, 智谱等", 
                 bg=Theme.BG_SECONDARY, fg=Theme.TEXT_SECONDARY, font=("", 10)).pack(anchor="w", pady=2)
    

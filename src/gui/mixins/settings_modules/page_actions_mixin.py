"""Settings page action handlers extracted from settings mixin."""

from __future__ import annotations

from tkinter import messagebox


class SettingsPageActionsMixin:
    """Handle settings page action callbacks and value loading."""

    def _set_dark_theme(self):
        """设置深色主题"""
        from ...theme import theme_manager
        theme_manager.set_dark()
        messagebox.showinfo("提示", "已切换到深色主题")
    
    def _set_light_theme(self):
        """设置浅色主题"""
        from ...theme import theme_manager
        theme_manager.set_light()
        messagebox.showinfo("提示", "已切换到浅色主题")
    
    def _import_config_ui(self):
        """导入配置UI"""
        if hasattr(self, 'import_config'):
            self.import_config()
    
    def _export_config_ui(self):
        """导出配置UI（不含密钥）"""
        if hasattr(self, 'export_config'):
            self.export_config(include_keys=False)
    
    def _export_config_with_keys(self):
        """导出配置（含密钥）"""
        if messagebox.askyesno("确认", "导出文件将包含API密钥，请注意保管！\n确定继续吗？"):
            if hasattr(self, 'export_config'):
                self.export_config(include_keys=True)
    
    def _clear_cache_ui(self):
        """清除缓存UI"""
        if messagebox.askyesno("确认", "确定要清除所有缓存吗？"):
            if hasattr(self, 'clear_cache'):
                self.clear_cache()
            self._update_cache_size()
    
    def _update_cache_size(self):
        """更新缓存大小显示"""
        try:
            from pathlib import Path
            cache_dir = Path("cache")
            if cache_dir.exists():
                total_size = sum(f.stat().st_size for f in cache_dir.rglob('*') if f.is_file())
                if total_size < 1024:
                    size_str = f"{total_size} B"
                elif total_size < 1024 * 1024:
                    size_str = f"{total_size / 1024:.1f} KB"
                else:
                    size_str = f"{total_size / (1024*1024):.1f} MB"
            else:
                size_str = "0 B"
            
            if hasattr(self, 'cache_size_label'):
                self.cache_size_label.config(text=f"缓存大小: {size_str}")
        except Exception:
            pass
    
    def _show_shortcuts_ui(self):
        """显示快捷键帮助"""
        if hasattr(self, '_show_shortcuts_help'):
            self._show_shortcuts_help()
        else:
            shortcuts_text = """快捷键列表:

文件操作:
  Ctrl+N: 新建项目
  Ctrl+O: 打开项目
  Ctrl+S: 保存项目
  Ctrl+E: 导出项目
  Ctrl+I: 导入项目

生成操作:
  Ctrl+G: 生成大纲
  Ctrl+Shift+G: 生成故事
  F5: 生成选中章节

视图切换:
  Ctrl+1: 项目页
  Ctrl+2: 故事页
  Ctrl+3: 图片页
  Ctrl+4: 设置页
  Ctrl+T: 切换主题

其他:
  F1: 显示帮助
  Ctrl+Z: 撤销
  Ctrl+Y: 重做"""
            messagebox.showinfo("快捷键帮助", shortcuts_text)
    
    def _open_kb_preview(self):
        """打开知识库预览"""
        if hasattr(self, 'open_kb_preview'):
            self.open_kb_preview()
    
    def _open_kb_manager(self):
        """打开知识库管理"""
        if hasattr(self, 'open_kb_manager'):
            self.open_kb_manager()
    
    def _load_settings_values(self):
        """加载当前配置值到设置页面"""
        # 从文件加载保存的配置
        if hasattr(self, '_load_api_config_from_file'):
            self._load_api_config_from_file()

        # 加载模型路由
        if hasattr(self, '_ensure_model_routing_loaded'):
            self._ensure_model_routing_loaded()
        
        # 加载故事API配置
        self._on_settings_provider_change()
        
        # 加载图片API配置
        self._on_settings_img_provider_change()

        # 加载模型路由到UI
        if hasattr(self, '_load_model_routing_to_ui'):
            self._load_model_routing_to_ui()

        # 加载快速 API 切换配置
        if hasattr(self, '_load_quick_api_switch'):
            self._load_quick_api_switch()

        if hasattr(self, "_update_story_template_desc"):
            self._update_story_template_desc()
        if hasattr(self, "_update_story_template_strategy_desc"):
            self._update_story_template_strategy_desc()
        if hasattr(self, "_update_story_creativity_mode_desc"):
            self._update_story_creativity_mode_desc()

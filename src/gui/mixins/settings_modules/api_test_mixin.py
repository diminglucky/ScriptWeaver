"""Settings API test helpers extracted from settings mixin."""

from __future__ import annotations

import threading
from tkinter import END, messagebox


class SettingsApiTestMixin:
    """Run async connectivity checks for story/image API settings."""

    def _test_story_api(self):
        """测试故事API连接"""
        from src.utils.text import try_chat_api
        
        key = self.settings_api_key.get().strip()
        base_url = self.settings_base_url.get().strip()
        model = self._get_current_story_model()
        provider = self.settings_api_provider.get()
        
        if not key:
            messagebox.showwarning("提示", "请先填写API Key")
            return
        
        def ui_call(func, *args, **kwargs):
            if hasattr(self, '_ui'):
                return self._ui(func, *args, **kwargs)
            return func(*args, **kwargs)
        
        def task():
            ui_call(self.settings_log.insert, END, f"\n🔍 测试 {provider} API...\n")
            ui_call(self.settings_log.insert, END, f"   模型: {model}\n")
            ui_call(self.settings_log.insert, END, f"   Base URL: {base_url}\n")
            ui_call(self.settings_log.see, END)
            
            ok, msg = try_chat_api(key, base_url, model)
            if ok:
                ui_call(self.settings_log.insert, END, "✅ 连接成功!\n")
                ui_call(self.settings_log.insert, END, "🔄 正在获取模型列表...\n")
                ui_call(self.settings_log.see, END)
                # 测试成功后刷新模型列表
                self._refresh_models_for_provider(provider, key, base_url, log_to_settings=True)
            else:
                ui_call(self.settings_log.insert, END, f"❌ 连接失败: {msg}\n")
                ui_call(self.settings_log.see, END)
        
        threading.Thread(target=task, daemon=True).start()
    
    def _test_img_api(self):
        """测试图片API连接"""
        from src.utils.text import try_image_api
        
        key = self.settings_img_api_key.get().strip()
        base_url = self.settings_img_base_url.get().strip()
        model = self._get_current_img_model()
        provider = self.settings_img_provider.get()
        
        if not key:
            messagebox.showwarning("提示", "请先填写API Key")
            return

        def ui_call(func, *args, **kwargs):
            if hasattr(self, '_ui'):
                return self._ui(func, *args, **kwargs)
            return func(*args, **kwargs)
        
        def task():
            ui_call(self.settings_log.insert, END, f"\n🔍 测试 {provider} 图片API...\n")
            ui_call(self.settings_log.insert, END, f"   模型: {model}\n")
            ui_call(self.settings_log.see, END)
            
            ok, msg = try_image_api(key, base_url, model)
            if ok:
                ui_call(self.settings_log.insert, END, f"✅ 连接成功: {msg}\n")
            else:
                ui_call(self.settings_log.insert, END, f"❌ 连接失败: {msg}\n")
            ui_call(self.settings_log.see, END)
        
        threading.Thread(target=task, daemon=True).start()


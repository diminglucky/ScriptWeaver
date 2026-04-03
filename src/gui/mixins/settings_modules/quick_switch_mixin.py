"""Quick API switch helpers extracted from settings mixin."""

from __future__ import annotations

import os
from tkinter import END, messagebox


class SettingsQuickSwitchMixin:
    """Save/load quick story/image provider switches."""

    def _save_quick_api_switch(self):
        """保存快速 API 切换配置"""
        try:
            from dotenv import set_key

            env_path = self._resolve_env_path()
            
            # 保存故事生成 API 选择
            story_api = self.quick_story_api.get()
            set_key(str(env_path), "STORY_OUTLINE_GEN_API", story_api)
            set_key(str(env_path), "STORY_STORY_GEN_API", story_api)
            self._save_story_env_payload(env_path)
            
            # 保存图片生成 API 选择
            image_api = self.quick_image_api.get()
            set_key(str(env_path), "IMAGE_GEN_API", image_api)
            
            # 同步到其他页面的变量
            if hasattr(self, 'outline_gen_api'):
                self.outline_gen_api.set(story_api)
            if hasattr(self, 'story_gen_api'):
                self.story_gen_api.set(story_api)
            
            self.settings_log.insert(END, f"\n✅ API 选择已保存\n")
            self.settings_log.insert(END, f"   故事生成: {story_api}\n")
            self.settings_log.insert(END, f"   图片生成: {image_api}\n")
            self.settings_log.see(END)
            
            messagebox.showinfo("成功", f"API 选择已保存！\n\n故事生成: {story_api}\n图片生成: {image_api}\n\n重启应用后生效")
        except Exception as e:
            messagebox.showerror("错误", f"保存失败: {str(e)}")
    
    def _load_quick_api_switch(self):
        """加载快速 API 切换配置"""
        try:
            from dotenv import load_dotenv
            
            # Keep runtime/env overrides (e.g. tests or launcher env), and use .env as fallback only.
            load_dotenv(override=False)
            
            # 加载故事生成 API
            story_api = os.getenv("STORY_OUTLINE_GEN_API", "DeepSeek")
            if hasattr(self, 'quick_story_api'):
                self.quick_story_api.set(story_api)
            if hasattr(self, 'settings_api_provider') and hasattr(self, 'api_providers'):
                if story_api in self.api_providers:
                    self.settings_api_provider.set(story_api)
            if hasattr(self, 'api_preset') and hasattr(self, 'api_presets'):
                if story_api in self.api_presets:
                    self.api_preset.set(story_api)
            self._apply_story_env_preferences_from_env()
            
            # 加载图片生成 API
            image_api = os.getenv("IMAGE_GEN_API", "") or os.getenv("IMG_API_PRESET", "OpenAI (DALL-E)")
            if hasattr(self, 'quick_image_api'):
                self.quick_image_api.set(image_api)
            if hasattr(self, 'settings_img_provider') and hasattr(self, 'img_api_providers'):
                if image_api in self.img_api_providers:
                    self.settings_img_provider.set(image_api)
            if hasattr(self, 'img_api_preset') and hasattr(self, 'img_api_presets'):
                if image_api in self.img_api_presets:
                    self.img_api_preset.set(image_api)
            if hasattr(self, 'char_draw_api_var') and image_api:
                try:
                    self.char_draw_api_var.set(image_api)
                except Exception:
                    pass
            if hasattr(self, '_sync_img_runtime_from_config'):
                self._sync_img_runtime_from_config(image_api)
            
            # 更新下拉框选项
            if hasattr(self, 'api_providers') and hasattr(self, 'combo_quick_story_api'):
                api_list = list(self.api_providers.keys())
                self.combo_quick_story_api['values'] = api_list
            
            if hasattr(self, 'img_api_providers') and hasattr(self, 'combo_quick_image_api'):
                img_api_list = list(self.img_api_providers.keys())
                self.combo_quick_image_api['values'] = img_api_list
                if hasattr(self, 'combo_char_draw_api'):
                    self.combo_char_draw_api['values'] = img_api_list
                    if hasattr(self, 'char_draw_api_var'):
                        current_char_api = self.char_draw_api_var.get().strip()
                        if image_api in img_api_list:
                            self.char_draw_api_var.set(image_api)
                        elif img_api_list and current_char_api not in img_api_list:
                            self.char_draw_api_var.set(img_api_list[0])

            # 刷新设置页输入框显示，避免界面仍显示默认 OpenAI
            if hasattr(self, '_on_settings_provider_change'):
                self._on_settings_provider_change()
            if hasattr(self, '_on_settings_img_provider_change'):
                self._on_settings_img_provider_change()
            
            print(f"[OK] 已加载快速 API 切换: 故事={story_api}, 图片={image_api}")
        except Exception as e:
            print(f"[WARN] 加载快速 API 切换失败: {e}")

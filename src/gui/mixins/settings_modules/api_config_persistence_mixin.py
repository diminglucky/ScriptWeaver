"""API config persistence helpers extracted from settings mixin."""

from __future__ import annotations

import os
from pathlib import Path
from tkinter import END, messagebox

from dotenv import load_dotenv


class SettingsApiConfigPersistenceMixin:
    """Persist/load story and image API settings from files/env."""

    def _save_story_api_settings(self):
        """保存故事API配置"""
        provider_name = self.settings_api_provider.get()
        model = self._get_current_story_model()
        key = self.settings_api_key.get().strip()
        base_url = self.settings_base_url.get().strip()
        
        # 更新provider配置
        if hasattr(self, 'api_providers') and provider_name in self.api_providers:
            self.api_providers[provider_name]["key"] = key
            self.api_providers[provider_name]["base_url"] = base_url
        
        # 同步更新api_presets
        if hasattr(self, 'api_presets'):
            self.api_presets[provider_name] = {
                "key": key,
                "base_url": base_url,
                "model": model
            }

        # 持久化故事路由与当前提供商，确保重启后无需再次切换
        try:
            import hashlib
            from dotenv import set_key

            env_path = self._resolve_env_path()

            if any(ord(c) > 127 for c in provider_name):
                hash_suffix = hashlib.md5(provider_name.encode()).hexdigest()[:8]
                safe_preset_name = f"CUSTOM_{hash_suffix}"
            else:
                safe_preset_name = provider_name.replace(" ", "_").replace("(", "").replace(")", "").replace("-", "_")

            set_key(str(env_path), "API_PRESET", provider_name)
            set_key(str(env_path), "STORY_OUTLINE_GEN_API", provider_name)
            set_key(str(env_path), "STORY_STORY_GEN_API", provider_name)
            set_key(str(env_path), f"STORY_{safe_preset_name}_KEY", key)
            set_key(str(env_path), f"STORY_{safe_preset_name}_BASE_URL", base_url)
            set_key(str(env_path), f"STORY_{safe_preset_name}_MODEL", model)
            self._save_story_env_payload(env_path)

            if hasattr(self, 'quick_story_api'):
                self.quick_story_api.set(provider_name)
            if hasattr(self, 'outline_gen_api'):
                self.outline_gen_api.set(provider_name)
            if hasattr(self, 'story_gen_api'):
                self.story_gen_api.set(provider_name)
        except Exception as e:
            self.settings_log.insert(END, f"⚠ 保存故事提供商到 .env 失败: {e}\n")
        
        # 保存到文件
        self._save_api_config_to_file()
        
        self.settings_log.insert(END, f"✅ 故事API配置已保存: {provider_name} / {model}\n")
        self.settings_log.see(END)
        messagebox.showinfo("成功", f"配置已保存\n提供商: {provider_name}\n模型: {model}")
    
    def _save_img_api_settings(self):
        """保存图片API配置"""
        provider_name = self.settings_img_provider.get()
        model = self._get_current_img_model()
        key = self.settings_img_api_key.get().strip()
        base_url = self.settings_img_base_url.get().strip()
        
        # 更新provider配置
        if hasattr(self, 'img_api_providers') and provider_name in self.img_api_providers:
            self.img_api_providers[provider_name]["key"] = key
            # Always persist base_url so third-party endpoints survive restart
            self.img_api_providers[provider_name]["base_url"] = base_url
            if provider_name == "自定义":
                self.img_api_providers[provider_name]["base_url"] = base_url
        
        # 同步更新img_api_presets
        if hasattr(self, 'img_api_presets'):
            provider_type = "openai"
            if hasattr(self, 'img_api_providers') and provider_name in self.img_api_providers:
                provider_type = self.img_api_providers[provider_name].get("provider", "openai")
            self.img_api_presets[provider_name] = {
                "key": key,
                "base_url": base_url,
                "model": model,
                "provider": provider_type
            }

        # Persist current image provider selection for next launch
        try:
            from dotenv import set_key

            env_path = self._resolve_env_path()
            set_key(str(env_path), "IMAGE_GEN_API", provider_name)
            set_key(str(env_path), "IMG_API_PRESET", provider_name)
            if hasattr(self, 'quick_image_api'):
                self.quick_image_api.set(provider_name)
            if hasattr(self, 'img_api_preset'):
                self.img_api_preset.set(provider_name)
        except Exception as e:
            self.settings_log.insert(END, f"⚠ 保存图片提供商到 .env 失败: {e}\n")
        
        # 保存到文件
        self._save_api_config_to_file()

        # 同步到运行时变量，确保图片生成功能可直接使用
        self._sync_img_runtime_from_settings(provider_name)
        
        self.settings_log.insert(END, f"✅ 图片API配置已保存: {provider_name} / {model}\n")
        self.settings_log.see(END)
        messagebox.showinfo("成功", f"配置已保存\n提供商: {provider_name}\n模型: {model}")
    
    def _save_api_config_to_file(self):
        """保存API配置到文件"""
        try:
            import json
            from pathlib import Path
            
            # 保存故事API配置
            story_config = {}
            if hasattr(self, 'api_providers'):
                for name, config in self.api_providers.items():
                    if config.get("key"):  # 只保存有key的配置
                        # 获取当前选中的模型（如果是当前provider）
                        current_model = None
                        if hasattr(self, 'settings_api_provider') and self.settings_api_provider.get() == name:
                            current_model = self._get_current_story_model()
                        
                        story_config[name] = {
                            "key": config["key"],
                            "base_url": config["base_url"],
                            "models": config.get("models", [])
                        }
                        
                        # 保存当前选中的模型
                        if current_model:
                            story_config[name]["model"] = current_model
            
            if story_config:
                with open("custom_api_presets.json", 'w', encoding='utf-8') as f:
                    json.dump(story_config, f, ensure_ascii=False, indent=2)
            
            # 保存图片API配置
            img_config = {}
            if hasattr(self, 'img_api_providers'):
                for name, config in self.img_api_providers.items():
                    if config.get("key"):  # 只保存有key的配置
                        # 获取当前选中的模型（如果是当前provider）
                        current_model = None
                        if hasattr(self, 'settings_img_provider') and self.settings_img_provider.get() == name:
                            current_model = self._get_current_img_model()
                        
                        img_config[name] = {
                            "key": config["key"],
                            "base_url": config["base_url"],
                            "models": config.get("models", []),
                            "provider": config.get("provider", "openai")
                        }
                        
                        # 保存当前选中的模型
                        if current_model:
                            img_config[name]["model"] = current_model
                        if config.get("secret_key"):
                            img_config[name]["secret_key"] = config.get("secret_key")
            
            if img_config:
                with open("custom_image_api_presets.json", 'w', encoding='utf-8') as f:
                    json.dump(img_config, f, ensure_ascii=False, indent=2)
            
            print("[OK] API配置已保存到文件")
        except Exception as e:
            print(f"[ERROR] 保存配置失败: {e}")
            messagebox.showerror("错误", f"保存配置失败: {str(e)}")
    
    def _load_api_config_from_file(self):
        """从文件加载API配置"""
        try:
            from pathlib import Path
            story_config = self._load_json_config(Path("custom_api_presets.json"))
            if story_config:
                self._apply_story_api_config(story_config)
                print(f"[OK] 已加载 {len(story_config)} 个故事API配置")

            img_config = self._load_json_config(Path("custom_image_api_presets.json"))
            if img_config:
                self._apply_image_api_config(img_config)
                print(f"[OK] 已加载 {len(img_config)} 个图片API配置")

            # 启动时自动同步图片API到运行时（即使未打开设置页）
            if hasattr(self, "_sync_img_runtime_from_config"):
                self._sync_img_runtime_from_config()
            self._api_config_from_file_loaded = True
                
        except Exception as e:
            print(f"[WARN] 加载配置失败: {e}")

    def _load_json_config(self, file_path) -> dict:
        """加载 JSON 配置文件。不存在时返回空字典。"""
        if not file_path.exists():
            return {}
        import json

        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)

    @staticmethod
    def _infer_image_provider(name: str) -> str:
        lower = name.lower()
        if "混元" in name or "hunyuan" in lower:
            return "hunyuan"
        return "openai"

    def _apply_story_api_config(self, story_config: dict) -> None:
        for name, config in story_config.items():
            key = config.get("key", "")
            base_url = config.get("base_url", "")
            model = config.get("model", "")
            models = config.get("models", [])
            if hasattr(self, "api_providers") and name in self.api_providers:
                self.api_providers[name]["key"] = key
                if base_url:
                    self.api_providers[name]["base_url"] = base_url
                if models:
                    self.api_providers[name]["models"] = models
            if hasattr(self, "api_presets"):
                if name not in self.api_presets:
                    self.api_presets[name] = {}
                self.api_presets[name]["key"] = key
                self.api_presets[name]["base_url"] = base_url
                if model:
                    self.api_presets[name]["model"] = model

    def _apply_image_api_config(self, img_config: dict) -> None:
        for name, config in img_config.items():
            key = config.get("key", "")
            base_url = config.get("base_url", "")
            model = config.get("model", "")
            models = config.get("models", [])
            provider = config.get("provider", "") or self._infer_image_provider(name)
            secret_key = config.get("secret_key", "")
            if hasattr(self, "img_api_providers") and name in self.img_api_providers:
                self.img_api_providers[name]["key"] = key
                if base_url:
                    self.img_api_providers[name]["base_url"] = base_url
                if models:
                    self.img_api_providers[name]["models"] = models
                self.img_api_providers[name]["provider"] = provider
                if secret_key:
                    self.img_api_providers[name]["secret_key"] = secret_key
            if hasattr(self, "img_api_presets"):
                if name not in self.img_api_presets:
                    self.img_api_presets[name] = {}
                self.img_api_presets[name]["key"] = key
                self.img_api_presets[name]["base_url"] = base_url
                if model:
                    self.img_api_presets[name]["model"] = model
                self.img_api_presets[name]["provider"] = provider
                if secret_key:
                    self.img_api_presets[name]["secret_key"] = secret_key
    

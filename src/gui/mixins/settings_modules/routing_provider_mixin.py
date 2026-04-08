"""Model routing/provider helpers extracted from settings mixin."""

from __future__ import annotations

import os
import re
import threading
from tkinter import END, messagebox
from typing import Optional

from ...theme import Theme
from ..config_modules.model_routing import MODEL_ROUTING_TASKS


class SettingsRoutingProviderMixin:
    """Model routing, provider switching, and model list refresh helpers."""

    def _load_model_routing_from_file(self) -> None:
        """从文件加载模型路由配置"""
        try:
            import json
            from pathlib import Path

            path = Path("model_routing.json")
            if not path.exists():
                self.model_routing = {}
                self.model_routing_meta = {}
                self._model_routing_loaded = True
                return

            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                meta = data.get("__meta__", {})
                self.model_routing_meta = meta if isinstance(meta, dict) else {}
                self.model_routing = {
                    k: v
                    for k, v in data.items()
                    if k != "__meta__" and isinstance(v, dict)
                }
            else:
                self.model_routing = {}
                self.model_routing_meta = {}
            self._model_routing_loaded = True
        except Exception:
            self.model_routing = {}
            self.model_routing_meta = {}
            self._model_routing_loaded = True

    def _save_model_routing_to_file(self) -> None:
        """保存模型路由配置到文件"""
        try:
            import json

            routing = self.model_routing if isinstance(getattr(self, "model_routing", {}), dict) else {}
            payload = dict(routing)
            meta = self.model_routing_meta if isinstance(getattr(self, "model_routing_meta", {}), dict) else {}
            if meta:
                payload["__meta__"] = meta
            with open("model_routing.json", "w", encoding="utf-8") as f:
                json.dump(payload, f, ensure_ascii=False, indent=2)
        except Exception:
            # 路由保存失败不应阻断主流程
            pass

    def _ensure_model_routing_loaded(self) -> None:
        """确保模型路由已加载并包含默认任务键"""
        if getattr(self, "_model_routing_loaded", False):
            if not isinstance(getattr(self, "model_routing", None), dict):
                self.model_routing = {}
            if not isinstance(getattr(self, "model_routing_meta", None), dict):
                self.model_routing_meta = {}
            return

        self._load_model_routing_from_file()
        if not isinstance(getattr(self, "model_routing", None), dict):
            self.model_routing = {}
        if not isinstance(getattr(self, "model_routing_meta", None), dict):
            self.model_routing_meta = {}

        for task_key, _label in MODEL_ROUTING_TASKS:
            if task_key not in self.model_routing:
                self.model_routing[task_key] = {"provider": "", "model": ""}

        self._model_routing_loaded = True

    def _get_task_route(self, task_key: str) -> dict:
        """获取任务路由配置"""
        self._ensure_model_routing_loaded()
        route = self.model_routing.get(task_key, {}) if isinstance(self.model_routing, dict) else {}
        return route if isinstance(route, dict) else {}

    def _resolve_task_api(self, task_key: str, fallback_provider: Optional[str] = None, fallback_model: Optional[str] = None) -> dict:
        """解析任务应使用的 API 配置（provider/key/base_url/model）"""
        self._ensure_model_routing_loaded()

        route = self._get_task_route(task_key)
        provider = (route.get("provider", "") if isinstance(route, dict) else "").strip()
        if not provider:
            provider = (fallback_provider or "").strip()
        if not provider and hasattr(self, "settings_api_provider"):
            provider = self.settings_api_provider.get().strip()
        if not provider and hasattr(self, "api_preset"):
            provider = self.api_preset.get().strip()
        if not provider:
            provider = "DeepSeek"

        provider_cfg = {}
        if hasattr(self, "api_providers") and provider in self.api_providers:
            provider_cfg = self.api_providers.get(provider, {}) or {}
        elif hasattr(self, "api_presets") and provider in self.api_presets:
            provider_cfg = self.api_presets.get(provider, {}) or {}

        key = str(provider_cfg.get("key", "") or "").strip()
        base_url = str(provider_cfg.get("base_url", "") or "").strip()

        # Backward compatibility: allow legacy DeepSeek env vars when routing key is empty.
        if provider == "DeepSeek":
            if not key:
                key = os.getenv("DEEPSEEK_API_KEY", "").strip()
            if not base_url:
                base_url = os.getenv("DEEPSEEK_BASE_URL", "").strip()

        route_model = ""
        if isinstance(route, dict):
            route_model = str(route.get("model", "") or "").strip()
        if hasattr(self, "_strip_model_label"):
            route_model = self._strip_model_label(route_model)

        model = route_model
        if not model:
            cfg_model = str(provider_cfg.get("model", "") or "").strip()
            if hasattr(self, "_strip_model_label"):
                cfg_model = self._strip_model_label(cfg_model)
            model = cfg_model
        if not model:
            models = provider_cfg.get("models", []) if isinstance(provider_cfg, dict) else []
            if isinstance(models, list) and models:
                first_model = str(models[0]).strip()
                model = self._strip_model_label(first_model) if hasattr(self, "_strip_model_label") else first_model
        if not model:
            model = self._strip_model_label((fallback_model or "").strip()) if hasattr(self, "_strip_model_label") else (fallback_model or "").strip()
        if not model and provider == "DeepSeek":
            model = os.getenv("DEEPSEEK_MODEL", "").strip()
        if not model:
            model = "deepseek-chat"

        return {
            "provider": provider,
            "key": key,
            "base_url": base_url,
            "model": model,
        }

    def _strip_model_label(self, model: str) -> str:
        """去除模型前缀标签（📝 文本 / 🖼️ 图像）"""
        if not model:
            return ""
        m = str(model).strip()
        # 去掉 emoji 与文字前缀
        m = re.sub(r'^(📝|🖼️)\s*', '', m)
        m = re.sub(r'^(文本|图像|图片)\s*', '', m)
        m = re.sub(r'^[\|\-·:：]\s*', '', m)
        return m.strip()

    def _decorate_model_value(self, model: str, kind: str) -> str:
        """为模型值添加可读前缀"""
        raw = self._strip_model_label(model)
        if not raw:
            return ""
        prefix = "🖼️ 图像" if kind == "image" else "📝 文本"
        return f"{prefix} {raw}"

    def _decorate_model_list(self, models, kind: str):
        """批量为模型列表添加前缀"""
        if not models:
            return []
        return [self._decorate_model_value(m, kind) for m in models if str(m).strip()]

    def _models_need_refresh(self, models) -> bool:
        """判断模型列表是否需要刷新"""
        if not models:
            return True
        cleaned = []
        for m in models:
            if isinstance(m, str) and m.strip():
                cleaned.append(m.strip())
        if not cleaned:
            return True
        if len(cleaned) == 1 and cleaned[0].lower() == "default":
            return True
        return False

    def _fetch_models_from_api(self, api_key: str, base_url: str):
        """从 API 获取模型列表"""
        try:
            import requests
            
            base = (base_url or "").strip().rstrip("/")
            if not base:
                return [], "Base URL 为空"
            
            candidates = []
            if base.endswith("/v1"):
                candidates.append(f"{base}/models")
            else:
                candidates.append(f"{base}/v1/models")
                candidates.append(f"{base}/models")
            
            headers = {
                "Authorization": f"Bearer {api_key}",
                "User-Agent": "Mozilla/5.0"
            }
            
            last_error = None
            for url in candidates:
                try:
                    resp = requests.get(url, headers=headers, timeout=10)
                    if resp.status_code != 200:
                        last_error = f"{resp.status_code}"
                        continue
                    result = resp.json()
                    
                    def _extract(items):
                        out = []
                        for item in items:
                            if isinstance(item, dict):
                                mid = item.get("id") or item.get("name")
                            elif isinstance(item, str):
                                mid = item
                            else:
                                mid = None
                            if mid:
                                out.append(str(mid))
                        return out
                    
                    models = []
                    if isinstance(result, dict):
                        if isinstance(result.get("data"), list):
                            models = _extract(result.get("data", []))
                        elif isinstance(result.get("models"), list):
                            models = _extract(result.get("models", []))
                        elif isinstance(result.get("result"), list):
                            models = _extract(result.get("result", []))
                    elif isinstance(result, list):
                        models = _extract(result)
                    
                    # 去重保持顺序
                    seen = set()
                    unique = []
                    for m in models:
                        if m not in seen:
                            seen.add(m)
                            unique.append(m)
                    
                    if unique:
                        return unique, None
                    last_error = "响应未包含模型列表"
                except Exception as e:
                    last_error = str(e)
                    continue
            return [], last_error or "请求失败"
        except Exception as e:
            return [], str(e)

    def _refresh_models_for_provider(self, provider: str, api_key: str, base_url: str, log_to_settings: bool = False) -> None:
        """刷新指定提供商的模型列表，并更新界面"""
        if not provider or not api_key or not base_url:
            return
        if not hasattr(self, "_model_fetching"):
            self._model_fetching = set()
        if provider in self._model_fetching:
            return
        self._model_fetching.add(provider)
        
        def ui_call(func, *args, **kwargs):
            if hasattr(self, '_ui'):
                return self._ui(func, *args, **kwargs)
            return func(*args, **kwargs)
        
        def task():
            try:
                models, err = self._fetch_models_from_api(api_key, base_url)
                
                if models:
                    def apply_models():
                        if hasattr(self, 'api_providers') and provider in self.api_providers:
                            self.api_providers[provider]["models"] = models
                            # 同步内存中的 key/base_url，方便后续使用
                            self.api_providers[provider]["key"] = api_key
                            self.api_providers[provider]["base_url"] = base_url
                        
                        # 更新设置页的模型下拉框
                        if (
                            hasattr(self, 'settings_api_provider')
                            and self.settings_api_provider.get() == provider
                            and hasattr(self, 'settings_combo_model')
                        ):
                            display_models = self._decorate_model_list(models, "text")
                            self.settings_combo_model['values'] = display_models or [""]
                            current = self.settings_model_var.get().strip()
                            raw_current = self._strip_model_label(current)
                            if not raw_current and models:
                                if display_models:
                                    self.settings_model_var.set(display_models[0])
                            elif raw_current in models:
                                decorated = self._decorate_model_value(raw_current, "text")
                                if current != decorated:
                                    self.settings_model_var.set(decorated)
                        
                        # 更新模型路由的模型下拉框
                        if hasattr(self, 'model_route_vars'):
                            for _task_key, route_ui in self.model_route_vars.items():
                                if route_ui["provider_var"].get() == provider:
                                    task_key = route_ui.get("task_key", "")
                                    kind = "image" if str(task_key).startswith("image_") else "text"
                                    display_models = self._decorate_model_list(models, kind)
                                    route_ui["combo_model"]['values'] = display_models or [""]
                                    current = route_ui["model_var"].get().strip()
                                    raw_current = self._strip_model_label(current)
                                    if not raw_current and models:
                                        if display_models:
                                            route_ui["model_var"].set(display_models[0])
                                    elif raw_current in models:
                                        decorated = self._decorate_model_value(raw_current, kind)
                                        if current != decorated:
                                            route_ui["model_var"].set(decorated)
                        
                        if log_to_settings and hasattr(self, 'settings_log'):
                            self.settings_log.insert(END, f"✅ 已加载 {len(models)} 个模型\n")
                            self.settings_log.see(END)
                    
                    ui_call(apply_models)
                else:
                    if log_to_settings and hasattr(self, 'settings_log'):
                        ui_call(self.settings_log.insert, END, f"⚠️ 获取模型列表失败: {err or '未知错误'}\n")
                        ui_call(self.settings_log.see, END)
            finally:
                try:
                    self._model_fetching.discard(provider)
                except Exception:
                    pass
        
        threading.Thread(target=task, daemon=True).start()

    def _on_route_provider_change(self, task_key: str) -> None:
        """模型路由提供商切换"""
        if not hasattr(self, 'model_route_vars'):
            return
        route_ui = self.model_route_vars.get(task_key)
        if not route_ui:
            return
        provider = route_ui["provider_var"].get()
        models = []
        provider_cfg = None
        if hasattr(self, 'api_providers') and provider in self.api_providers:
            provider_cfg = self.api_providers[provider]
            models = provider_cfg.get("models", [])
        elif hasattr(self, 'api_presets') and provider in self.api_presets:
            saved_model = self.api_presets[provider].get("model", "")
            if saved_model:
                models = [saved_model]
        combo_model = route_ui["combo_model"]
        task_key = route_ui.get("task_key", "")
        kind = "image" if str(task_key).startswith("image_") else "text"
        display_models = self._decorate_model_list(models, kind)
        combo_model['values'] = display_models or [""]
        # 如果当前模型不在列表中，保持用户输入
        current_model = route_ui["model_var"].get().strip()
        raw_current = self._strip_model_label(current_model)
        if not raw_current and models:
            if display_models:
                route_ui["model_var"].set(display_models[0])
        elif raw_current in models:
            decorated = self._decorate_model_value(raw_current, kind)
            if current_model != decorated:
                route_ui["model_var"].set(decorated)

        # 如果模型列表为空或占位，尝试从 API 获取
        if self._models_need_refresh(models):
            key = ""
            base_url = ""
            if provider_cfg:
                key = provider_cfg.get("key", "")
                base_url = provider_cfg.get("base_url", "")
            # 如果当前设置页正好是该 provider，优先用用户输入的 key/base_url
            if hasattr(self, 'settings_api_provider') and self.settings_api_provider.get() == provider:
                key = self.settings_api_key.get().strip() or key
                base_url = self.settings_base_url.get().strip() or base_url
            if key and base_url:
                self._refresh_models_for_provider(provider, key, base_url, log_to_settings=False)

    def _load_model_routing_to_ui(self) -> None:
        """将模型路由加载到设置界面"""
        if not hasattr(self, 'model_route_vars'):
            return
        # 确保路由已加载
        if hasattr(self, '_ensure_model_routing_loaded'):
            self._ensure_model_routing_loaded()
        advanced_mode = bool(getattr(self, "model_routing_meta", {}).get("advanced_mode", False))
        self._toggle_model_routing_advanced_ui(advanced_mode)
        for task_key, _label in MODEL_ROUTING_TASKS:
            route = self._get_task_route(task_key) if hasattr(self, '_get_task_route') else {}
            route_ui = self.model_route_vars.get(task_key)
            if not route_ui:
                continue
            provider = route.get("provider", "") or (self.settings_api_provider.get() if hasattr(self, 'settings_api_provider') else "DeepSeek")
            model = route.get("model", "")
            route_ui["provider_var"].set(provider)
            # 更新模型列表
            self._on_route_provider_change(task_key)
            if model:
                kind = "image" if str(task_key).startswith("image_") else "text"
                route_ui["model_var"].set(self._decorate_model_value(model, kind))

    def _save_model_routing_settings(self) -> None:
        """保存模型路由配置"""
        if not hasattr(self, 'model_route_vars'):
            return
        if not hasattr(self, 'model_routing'):
            self.model_routing = {}
        if not hasattr(self, "model_routing_meta") or not isinstance(self.model_routing_meta, dict):
            self.model_routing_meta = {}
        self.model_routing_meta["advanced_mode"] = bool(
            self.model_route_advanced_var.get() if hasattr(self, "model_route_advanced_var") else False
        )
        for task_key, _label in MODEL_ROUTING_TASKS:
            route_ui = self.model_route_vars.get(task_key)
            if not route_ui:
                continue
            provider = route_ui["provider_var"].get().strip()
            model = self._strip_model_label(route_ui["model_var"].get().strip())
            self.model_routing[task_key] = {
                "provider": provider,
                "model": model,
            }
        self._model_routing_loaded = True
        if hasattr(self, '_save_model_routing_to_file'):
            self._save_model_routing_to_file()
        if hasattr(self, 'settings_log'):
            self.settings_log.insert(END, "✅ 模型路由配置已保存\n")
            self.settings_log.see(END)
        messagebox.showinfo("成功", "模型路由已保存")

    def _toggle_model_routing_advanced_ui(self, enabled: Optional[bool] = None) -> None:
        """切换模型路由高级视图（默认隐藏复杂配置）"""
        if enabled is None:
            enabled = bool(self.model_route_advanced_var.get()) if hasattr(self, "model_route_advanced_var") else False
        enabled = bool(enabled)
        if hasattr(self, "model_route_advanced_var"):
            self.model_route_advanced_var.set(enabled)
        if hasattr(self, "model_routing_advanced_frame"):
            if enabled:
                self.model_routing_advanced_frame.grid()
            else:
                self.model_routing_advanced_frame.grid_remove()
        if hasattr(self, "model_route_mode_hint_label"):
            if enabled:
                self.model_route_mode_hint_label.config(
                    text="当前：高级模式（可为每个功能单独设置模型）",
                    fg="#F59E0B",
                )
            else:
                self.model_route_mode_hint_label.config(
                    text="当前：简洁模式（默认用主模型；需要时再打开高级模式）",
                    fg=Theme.TEXT_SECONDARY,
                )

    def _on_model_route_mode_toggle(self) -> None:
        """高级模式开关变更"""
        self._toggle_model_routing_advanced_ui()
        if not hasattr(self, "model_routing_meta") or not isinstance(self.model_routing_meta, dict):
            self.model_routing_meta = {}
        self.model_routing_meta["advanced_mode"] = bool(
            self.model_route_advanced_var.get() if hasattr(self, "model_route_advanced_var") else False
        )
        if hasattr(self, "_save_model_routing_to_file"):
            self._save_model_routing_to_file()

    def _apply_story_model_to_text_routes(self) -> None:
        """使用主模型快速覆盖所有文本任务路由"""
        if not hasattr(self, "model_route_vars"):
            return

        provider = ""
        if hasattr(self, "settings_api_provider"):
            provider = self.settings_api_provider.get().strip()
        if not provider and hasattr(self, "quick_story_api"):
            provider = self.quick_story_api.get().strip()
        if not provider and hasattr(self, "api_preset"):
            provider = self.api_preset.get().strip()
        if not provider and hasattr(self, "api_providers") and self.api_providers:
            provider = list(self.api_providers.keys())[0]

        model = ""
        if hasattr(self, "story_model_var"):
            model = self._strip_model_label(self.story_model_var.get().strip())
        if not model and hasattr(self, "settings_model_var"):
            model = self._strip_model_label(self.settings_model_var.get().strip())
        if not model and provider and hasattr(self, "api_providers") and provider in self.api_providers:
            model = self._strip_model_label(str(self.api_providers[provider].get("model", "") or ""))

        if not provider:
            messagebox.showwarning("提示", "未找到可用的故事提供商，请先在设置页配置故事 API")
            return
        if not model:
            messagebox.showwarning("提示", "未找到可用的主模型，请先在故事页或设置页选择模型")
            return

        updated = 0
        for task_key, _label in MODEL_ROUTING_TASKS:
            if str(task_key).startswith("image_"):
                continue
            route_ui = self.model_route_vars.get(task_key)
            if not route_ui:
                continue
            route_ui["provider_var"].set(provider)
            self._on_route_provider_change(task_key)
            route_ui["model_var"].set(self._decorate_model_value(model, "text"))
            updated += 1

        if hasattr(self, "settings_log"):
            self.settings_log.insert(
                END,
                f"✅ 已同步主模型到 {updated} 个文本任务: {provider} / {model}\n",
            )
            self.settings_log.see(END)
    
    def _on_settings_provider_change(self, event=None):
        """故事API提供商切换 - 更新模型列表"""
        provider_name = self.settings_api_provider.get()
        print(f"[INFO] 切换到提供商: {provider_name}")
        
        if hasattr(self, 'api_providers') and provider_name in self.api_providers:
            provider = self.api_providers[provider_name]
            
            # 更新模型下拉框的选项列表
            models = provider.get("models", ["default"])
            display_models = self._decorate_model_list(models, "text")
            self.settings_combo_model['values'] = display_models or [""]
            print(f"   可用模型: {models}")
            
            # 用户切换提供商时，若模型列表为空则尝试拉取
            if event is not None and self._models_need_refresh(models):
                key = provider.get("key", "")
                base_url = provider.get("base_url", "")
                if key and base_url:
                    self._refresh_models_for_provider(provider_name, key, base_url, log_to_settings=False)
            
            # 尝试从 api_presets 加载已保存的模型
            saved_model = None
            if hasattr(self, 'api_presets') and provider_name in self.api_presets:
                saved_model = self.api_presets[provider_name].get("model", "")
                print(f"   已保存的模型: {saved_model}")
            
            # 如果有保存的模型，使用保存的；否则使用列表第一个
            if saved_model:
                raw_saved = self._strip_model_label(saved_model)
                self.settings_model_var.set(self._decorate_model_value(raw_saved, "text"))
                print(f"   [OK] 设置模型为: {raw_saved}")
            else:
                default_model = models[0] if models else ""
                self.settings_model_var.set(self._decorate_model_value(default_model, "text"))
                print(f"   [WARN] 使用默认模型: {default_model}")
            
            # 自定义提供商时，优先填充自定义模型输入框
            if provider_name == "自定义" and hasattr(self, 'settings_custom_model'):
                current_custom = self.settings_custom_model.get().strip()
                if not current_custom and saved_model:
                    self.settings_custom_model.delete(0, END)
                    self.settings_custom_model.insert(0, saved_model)
            
            # 强制刷新 Combobox 显示
            if hasattr(self, 'settings_combo_model'):
                self.settings_combo_model.update()
            
            # 更新Base URL
            self.settings_base_url.delete(0, END)
            self.settings_base_url.insert(0, provider.get("base_url", ""))
            
            # 加载已保存的API Key
            self.settings_api_key.delete(0, END)
            self.settings_api_key.insert(0, provider.get("key", ""))
    
    def _on_settings_img_provider_change(self, event=None):
        """图片API提供商切换 - 更新模型列表"""
        provider_name = self.settings_img_provider.get()
        if hasattr(self, 'img_api_providers') and provider_name in self.img_api_providers:
            provider = self.img_api_providers[provider_name]
            
            # 更新模型下拉框的选项列表
            models = provider.get("models", ["default"])
            display_models = self._decorate_model_list(models, "image")
            self.settings_combo_img_model['values'] = display_models or [""]
            
            # 尝试从 img_api_presets 加载已保存的模型
            saved_model = None
            if hasattr(self, 'img_api_presets') and provider_name in self.img_api_presets:
                saved_model = self.img_api_presets[provider_name].get("model", "")
            
            # 如果有保存的模型，使用保存的；否则使用列表第一个
            if saved_model:
                raw_saved = self._strip_model_label(saved_model)
                self.settings_img_model_var.set(self._decorate_model_value(raw_saved, "image"))
            else:
                default_model = models[0] if models else ""
                self.settings_img_model_var.set(self._decorate_model_value(default_model, "image"))
            
            # 自定义提供商时，优先填充自定义模型输入框
            if provider_name == "自定义" and hasattr(self, 'settings_img_custom_model'):
                current_custom = self.settings_img_custom_model.get().strip()
                if not current_custom and saved_model:
                    self.settings_img_custom_model.delete(0, END)
                    self.settings_img_custom_model.insert(0, saved_model)
            
            # 更新Base URL
            self.settings_img_base_url.delete(0, END)
            self.settings_img_base_url.insert(0, provider.get("base_url", ""))
            
            # 加载已保存的API Key
            self.settings_img_api_key.delete(0, END)
            self.settings_img_api_key.insert(0, provider.get("key", ""))

            # 同步运行时图片API配置
            self._sync_img_runtime_from_settings(provider_name)
    
    def _toggle_key_visibility(self):
        """切换API Key显示/隐藏"""
        if self.show_key_var.get():
            self.settings_api_key.config(show="")
        else:
            self.settings_api_key.config(show="•")
    
    def _toggle_img_key_visibility(self):
        """切换图片API Key显示/隐藏"""
        if self.show_img_key_var.get():
            self.settings_img_api_key.config(show="")
        else:
            self.settings_img_api_key.config(show="•")

    def _sync_img_runtime_from_settings(self, provider_name: str | None = None) -> None:
        """将设置页图片API配置同步到运行时变量"""
        try:
            name = provider_name or (self.settings_img_provider.get().strip() if hasattr(self, 'settings_img_provider') else "")
            key = self.settings_img_api_key.get().strip() if hasattr(self, 'settings_img_api_key') else ""
            base_url = self.settings_img_base_url.get().strip() if hasattr(self, 'settings_img_base_url') else ""
            model = self._get_current_img_model() if hasattr(self, '_get_current_img_model') else ""

            if hasattr(self, 'img_api_key'):
                self.img_api_key.set(key)
            if hasattr(self, 'img_base_url'):
                self.img_base_url.set(base_url)
            if hasattr(self, 'img_model'):
                self.img_model.set(model)

            if hasattr(self, 'img_api_type'):
                api_type = None
                if hasattr(self, 'img_api_providers') and name in self.img_api_providers:
                    api_type = self.img_api_providers[name].get("provider")
                if not api_type:
                    lower = name.lower()
                    if "混元" in name or "hunyuan" in lower:
                        api_type = "hunyuan"
                    else:
                        api_type = "openai"
                self.img_api_type.set(api_type)
        except Exception:
            pass

    def _sync_img_runtime_from_config(self, provider_name: str | None = None) -> None:
        """从已加载的配置中同步图片API到运行时（无需打开设置页）"""
        try:
            import os
            name = provider_name or ""
            if not name:
                name = os.getenv("IMAGE_GEN_API", "") or os.getenv("IMG_API_PRESET", "")
            if not name and hasattr(self, 'settings_img_provider'):
                name = self.settings_img_provider.get().strip()

            config = None
            if hasattr(self, 'img_api_providers') and name in self.img_api_providers:
                config = self.img_api_providers[name]
            elif hasattr(self, 'img_api_presets') and name in self.img_api_presets:
                config = self.img_api_presets[name]
            elif hasattr(self, 'img_api_providers'):
                for _name, cfg in self.img_api_providers.items():
                    if cfg.get("key"):
                        name = _name
                        config = cfg
                        break

            if not config:
                return

            key = (config.get("key") or "").strip()
            base_url = (config.get("base_url") or "").strip()
            model = self._strip_model_label(config.get("model", "")) if hasattr(self, '_strip_model_label') else (config.get("model", "") or "")

            if hasattr(self, 'img_api_key'):
                self.img_api_key.set(key)
            if hasattr(self, 'img_base_url'):
                self.img_base_url.set(base_url)
            if hasattr(self, 'img_model'):
                self.img_model.set(model)

            if hasattr(self, 'img_api_type'):
                api_type = config.get("provider")
                if not api_type:
                    lower = name.lower()
                    if "混元" in name or "hunyuan" in lower:
                        api_type = "hunyuan"
                    else:
                        api_type = "openai"
                self.img_api_type.set(api_type)
        except Exception:
            pass
    
    def _get_current_story_model(self):
        """获取当前选择的故事模型"""
        # 直接从模型下拉框获取（现在支持手动输入）
        model = self._strip_model_label(self.settings_model_var.get().strip())
        
        custom_model = ""
        if hasattr(self, 'settings_custom_model'):
            custom_model = self._strip_model_label(self.settings_custom_model.get().strip())
        
        provider = self.settings_api_provider.get().strip() if hasattr(self, 'settings_api_provider') else ""
        if provider == "自定义":
            return custom_model or model or "gpt-3.5-turbo"
        
        return model or custom_model or "gpt-3.5-turbo"  # 默认值
    
    def _get_current_img_model(self):
        """获取当前选择的图片模型"""
        # 直接从模型下拉框获取（现在支持手动输入）
        model = self._strip_model_label(self.settings_img_model_var.get().strip())
        
        custom_model = ""
        if hasattr(self, 'settings_img_custom_model'):
            custom_model = self._strip_model_label(self.settings_img_custom_model.get().strip())
        
        provider = self.settings_img_provider.get().strip() if hasattr(self, 'settings_img_provider') else ""
        if provider == "自定义":
            return custom_model or model or "dall-e-3"
        
        return model or custom_model or "dall-e-3"  # 默认值
    

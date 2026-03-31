"""Config import/export helpers extracted from enhancements mixin."""

import json
from datetime import datetime
from tkinter import filedialog, messagebox


class ConfigExportMixin:
    """Import/export app config as JSON."""

    @staticmethod
    def _version_tuple(raw_version: str):
        parts = str(raw_version or "").split(".")
        out = []
        for part in parts:
            try:
                out.append(int(part))
            except Exception:
                out.append(0)
        while len(out) < 3:
            out.append(0)
        return tuple(out[:3])

    def export_config(self, include_keys: bool = False):
        config = {
            "version": "2.0",
            "export_time": datetime.now().isoformat(),
            "settings": {
                "temperature": self.temperature.get() if hasattr(self, "temperature") else 0.7,
                "top_k": self.top_k.get() if hasattr(self, "top_k") else 6,
                "target_chars": self.target_chars.get() if hasattr(self, "target_chars") else 1800,
                "rag_min_score": self.rag_min_score.get() if hasattr(self, "rag_min_score") else 0.12,
            },
            "api_providers": {},
            "img_api_providers": {},
        }

        if hasattr(self, "api_providers"):
            for name, provider in self.api_providers.items():
                config["api_providers"][name] = {
                    "base_url": provider.get("base_url", ""),
                    "models": provider.get("models", []),
                }
                if include_keys:
                    config["api_providers"][name]["key"] = provider.get("key", "")

        if hasattr(self, "img_api_providers"):
            for name, provider in self.img_api_providers.items():
                config["img_api_providers"][name] = {
                    "base_url": provider.get("base_url", ""),
                    "models": provider.get("models", []),
                    "provider": provider.get("provider", "openai"),
                }
                if include_keys:
                    config["img_api_providers"][name]["key"] = provider.get("key", "")

        file_path = filedialog.asksaveasfilename(
            title="导出配置",
            defaultextension=".json",
            filetypes=[("JSON文件", "*.json"), ("所有文件", "*.*")],
            initialname=f"config_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
        )

        if file_path:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            messagebox.showinfo("成功", f"配置已导出到:\n{file_path}")

    def import_config(self):
        file_path = filedialog.askopenfilename(
            title="导入配置",
            filetypes=[("JSON文件", "*.json"), ("所有文件", "*.*")],
        )

        if not file_path:
            return

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                config = json.load(f)

            if self._version_tuple(config.get("version", "1.0")) < self._version_tuple("2.0"):
                messagebox.showwarning("警告", "配置文件版本较旧，部分设置可能无法导入")

            if "settings" in config:
                settings = config["settings"]
                if hasattr(self, "temperature"):
                    self.temperature.set(settings.get("temperature", 0.7))
                if hasattr(self, "top_k"):
                    self.top_k.set(settings.get("top_k", 6))
                if hasattr(self, "target_chars"):
                    self.target_chars.set(settings.get("target_chars", 1800))
                if hasattr(self, "rag_min_score"):
                    try:
                        raw_rag = float(settings.get("rag_min_score", 0.12))
                    except Exception:
                        raw_rag = 0.12
                    self.rag_min_score.set(max(0.0, min(1.0, raw_rag)))

            if "api_providers" in config and hasattr(self, "api_providers"):
                for name, provider in config["api_providers"].items():
                    if name in self.api_providers:
                        if provider.get("base_url"):
                            self.api_providers[name]["base_url"] = provider["base_url"]
                        if provider.get("models"):
                            self.api_providers[name]["models"] = provider["models"]
                        if provider.get("key"):
                            self.api_providers[name]["key"] = provider["key"]

            if "img_api_providers" in config and hasattr(self, "img_api_providers"):
                for name, provider in config["img_api_providers"].items():
                    if name in self.img_api_providers:
                        if provider.get("base_url"):
                            self.img_api_providers[name]["base_url"] = provider["base_url"]
                        if provider.get("models"):
                            self.img_api_providers[name]["models"] = provider["models"]
                        if provider.get("provider"):
                            self.img_api_providers[name]["provider"] = provider["provider"]
                        if provider.get("key"):
                            self.img_api_providers[name]["key"] = provider["key"]

            messagebox.showinfo("成功", "配置导入成功！")
            if hasattr(self, "_load_settings_values"):
                self._load_settings_values()

        except Exception as e:
            messagebox.showerror("错误", f"导入配置失败:\n{e}")

"""
现代化UI主窗口 - 使用原有Mixin功能，应用现代化主题
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
import logging
import os
from pathlib import Path
from datetime import datetime

try:
    from dotenv import load_dotenv
except Exception:  # pragma: no cover - optional dependency
    def load_dotenv(*args, **kwargs):
        return False

from .theme import Theme, Styles, Icons, theme_manager
from .modern_ui_mixin import ModernUiMixin
from .mixins.story_modules import StoryMixin
from .mixins.image_modules import ImageMixin
from .mixins.director_mixin import DirectorMixin
from .mixins.project_mixin import ProjectMixin
from .mixins.config_modules import ConfigMixin
from .mixins.kb_mixin import KbMixin
from .mixins.ui_mixin import UiMixin
from .mixins.settings_refactored import SettingsMixin
from .mixins.enhancements_refactored import EnhancementsMixin
from .mixins.kb_enhancements import KBEnhancementsMixin
from .mixins.async_utils import PerformanceMixin
from .helpers.story_templates import (
    DEFAULT_STORY_TEMPLATE_KEY,
    DEFAULT_STORY_TEMPLATE_STRATEGY,
    normalize_story_template_strategy,
)
from .helpers.story_creativity import (
    DEFAULT_STORY_CREATIVITY_MODE,
    normalize_story_creativity_mode,
)

logger = logging.getLogger(__name__)


class ModernApp(
    tk.Tk,
    ModernUiMixin,
    ProjectMixin,
    StoryMixin,
    ImageMixin,
    DirectorMixin,
    KbMixin,
    ConfigMixin,
    UiMixin,
    SettingsMixin,
    EnhancementsMixin,
    KBEnhancementsMixin,
    PerformanceMixin,
):
    """现代化专业UI应用 - 整合所有原有功能"""
    
    def __init__(self):
        super().__init__()
        
        # 窗口配置
        self.title("AI Story Creator Pro - 智能故事创作平台")
        self.geometry("1400x900")
        self.minsize(1200, 700)
        
        # 设置窗口背景色
        self.configure(bg=Theme.BG_PRIMARY)
        
        # 加载环境变量
        load_dotenv()
        
        # 初始化所有必需的变量（原有功能需要）
        self._init_variables()
        self._setup_target_chars_autosave()
        
        # 应用现代化样式
        self._setup_modern_styles()
        
        # 创建现代化的顶部栏
        self._create_modern_header()
        
        # 调用原有的UI构建方法（来自UiMixin）
        # 这会创建完整的notebook和所有页面
        self._build_ui()
        self._setup_story_preferences_autosave_post_ui()
        
        # 应用现代化主题到现有组件
        self._apply_modern_theme()
        
        # 创建现代化状态栏
        self._create_modern_status_bar()
        
        # 更新时间显示
        self._update_time()
        
        # 初始化增强功能
        self._init_enhancements()
        
        # 初始化性能优化
        self._init_performance()
        
        # 注册主题变更回调
        theme_manager.register_callback(self._on_theme_change)
        
        # 启动后自动加载配置（单入口，避免多次 after 导致 UI 值跳动）
        self.after(100, self._startup_load_configs)
        self.protocol("WM_DELETE_WINDOW", self._on_app_close)

    def _setup_target_chars_autosave(self) -> None:
        """Setup auto-persist for story preferences."""
        self._target_chars_save_job = None
        self._target_chars_last_saved = None
        self._story_prefs_save_job = None
        self._story_prefs_trace_installed = False
        self._story_prefs_prompt_binding_installed = False
        self._story_prefs_last_saved: dict[str, str] = {}
        try:
            self._install_story_pref_var_traces()
            self._persist_story_preferences_to_env()
        except Exception as e:
            logger.debug("setup story preference autosave failed: %s", e)

    def _on_target_chars_changed(self, *_args) -> None:
        """Debounce writes when story preference vars change."""
        try:
            if self._story_prefs_save_job is not None:
                self.after_cancel(self._story_prefs_save_job)
            self._story_prefs_save_job = self.after(400, self._persist_story_preferences_to_env)
        except Exception as e:
            logger.debug("schedule story preference persist failed: %s", e)

    def _install_story_pref_var_traces(self) -> None:
        if self._story_prefs_trace_installed:
            return
        var_names = [
            "target_chars",
            "category",
            "style",
            "top_k",
            "temperature",
            "model_only",
            "rag_min_score",
            "story_outline_alignment_strict",
            "story_outline_alignment_max_attempts",
            "data_dir",
            "index_dir",
        ]
        for name in var_names:
            var = getattr(self, name, None)
            if var is None or not hasattr(var, "trace_add"):
                continue
            try:
                var.trace_add("write", self._on_target_chars_changed)
            except Exception as e:
                logger.debug("trace_add failed for %s: %s", name, e)
        self._story_prefs_trace_installed = True

    def _setup_story_preferences_autosave_post_ui(self) -> None:
        """Install post-UI autosave hooks (prompt/model widgets)."""
        if hasattr(self, "story_model_var") and hasattr(self.story_model_var, "trace_add"):
            try:
                self.story_model_var.trace_add("write", self._on_target_chars_changed)
            except Exception as e:
                logger.debug("trace story_model_var failed: %s", e)
        if hasattr(self, "prompt_text") and not self._story_prefs_prompt_binding_installed:
            try:
                self.prompt_text.bind("<KeyRelease>", self._on_prompt_text_changed, add="+")
                self.prompt_text.bind("<FocusOut>", self._on_prompt_text_changed, add="+")
                self._story_prefs_prompt_binding_installed = True
                self._restore_story_requirement_from_env()
            except Exception as e:
                logger.debug("bind prompt_text autosave failed: %s", e)
        self._restore_story_model_from_env()

    def _on_prompt_text_changed(self, _event=None) -> None:
        self._on_target_chars_changed()

    def _restore_story_requirement_from_env(self) -> None:
        if not hasattr(self, "prompt_text"):
            return
        saved = (os.getenv("STORY_REQUIREMENT", "") or "").strip()
        if not saved:
            return
        try:
            self.prompt_text.delete("1.0", "end")
            self.prompt_text.insert("1.0", saved)
            self.prompt_text.tag_remove("placeholder", "1.0", "end")
        except Exception as e:
            logger.debug("restore story requirement failed: %s", e)

    def _restore_story_model_from_env(self) -> None:
        saved_model = (os.getenv("STORY_UI_MODEL", "") or "").strip()
        if not saved_model or not hasattr(self, "story_model_var"):
            return
        try:
            self.story_model_var.set(saved_model)
        except Exception as e:
            logger.debug("restore story model failed: %s", e)

    def _read_story_requirement(self) -> str:
        if not hasattr(self, "prompt_text"):
            return ""
        try:
            if hasattr(self, "_get_prompt_content"):
                return str(self._get_prompt_content() or "").strip()
            raw = self.prompt_text.get("1.0", "end-1c").strip()
            if raw.startswith("例如："):
                return ""
            return raw
        except Exception:
            return ""

    def _persist_story_preferences_to_env(self) -> None:
        """Write story preferences to .env."""
        try:
            from dotenv import find_dotenv, set_key

            target_chars = 1800
            try:
                target_chars = int(self.target_chars.get())
            except Exception:
                target_chars = 1800
            target_chars = max(500, min(30000, target_chars))

            top_k = 6
            try:
                top_k = int(self.top_k.get())
            except Exception:
                top_k = 6
            top_k = max(1, min(20, top_k))

            temperature = 0.7
            try:
                temperature = float(self.temperature.get())
            except Exception:
                temperature = 0.7
            temperature = max(0.0, min(1.5, temperature))

            rag_min_score = 0.12
            try:
                rag_min_score = float(self.rag_min_score.get())
            except Exception:
                rag_min_score = 0.12
            rag_min_score = max(0.0, min(1.0, rag_min_score))

            model_only = False
            try:
                model_only = bool(self.model_only.get())
            except Exception:
                model_only = False

            payload = {
                "TARGET_CHARS": str(target_chars),
                "TOP_K": str(top_k),
                "TEMPERATURE": f"{temperature:.2f}",
                "MODEL_ONLY": "1" if model_only else "0",
                "RAG_MIN_SCORE": f"{rag_min_score:.2f}",
                "STORY_OUTLINE_ALIGNMENT_STRICT": "1"
                if bool(self.story_outline_alignment_strict.get())
                else "0",
                "STORY_OUTLINE_ALIGNMENT_MAX_ATTEMPTS": str(
                    max(1, min(4, int(self.story_outline_alignment_max_attempts.get())))
                ),
                "STORY_CATEGORY": str(self.category.get() if hasattr(self, "category") else "").strip(),
                "STORY_STYLE": str(self.style.get() if hasattr(self, "style") else "").strip(),
                "STORY_REQUIREMENT": self._read_story_requirement(),
                "STORY_UI_MODEL": str(self.story_model_var.get() if hasattr(self, "story_model_var") else "").strip(),
                "DATA_DIR": str(self.data_dir.get() if hasattr(self, "data_dir") else "").strip(),
                "INDEX_DIR": str(self.index_dir.get() if hasattr(self, "index_dir") else "").strip(),
            }

            env_path_str = find_dotenv(usecwd=True)
            env_path = Path(env_path_str) if env_path_str else Path.cwd() / ".env"
            env_path.touch(exist_ok=True)
            for key, value in payload.items():
                if self._story_prefs_last_saved.get(key) == value:
                    continue
                set_key(str(env_path), key, value)
                self._story_prefs_last_saved[key] = value

            self._target_chars_last_saved = target_chars
        except Exception as e:
            logger.debug("persist story preferences failed: %s", e)

    def _on_app_close(self):
        """Persist user preferences before exiting."""
        try:
            self._persist_story_preferences_to_env()
        except Exception as e:
            logger.debug("persist on close failed: %s", e)
        self.destroy()

    def _startup_load_configs(self):
        """启动时统一加载配置"""
        try:
            if not getattr(self, "_api_config_from_file_loaded", False):
                self._load_api_config_from_file()  # 先从 JSON 文件加载（仅一次）
            self._auto_load_api_config()       # 再从 .env 加载（可能覆盖）
            self._auto_load_story_api_selection()
            if hasattr(self, "_auto_restore_last_project_on_startup"):
                self._auto_restore_last_project_on_startup()
        except Exception as e:
            logger.warning("startup config load failed: %s", e)
    
    def _on_theme_change(self, new_theme):
        """主题变更回调"""
        # 重新应用样式
        self._setup_modern_styles()
        self.configure(bg=Theme.BG_PRIMARY)
        if hasattr(self, '_apply_modern_theme'):
            self._apply_modern_theme()
    
    def _init_variables(self):
        """初始化所有必需的变量"""
        self._init_path_variables()
        self._init_story_api_variables()
        self._init_generation_parameter_variables()
        self._init_runtime_state_variables()
        self.api_providers = self._normalize_story_provider_map(
            self._build_default_story_provider_map()
        )
        self.api_presets = self._build_story_api_presets(self.api_providers)
        self.img_api_providers = self._normalize_image_provider_map(
            self._build_default_image_provider_map()
        )
        self.img_api_presets = self._build_image_api_presets(self.img_api_providers)

    @staticmethod
    def _read_env_text(name: str, default: str = "") -> str:
        return (os.getenv(name, default) or default).strip() or default

    @staticmethod
    def _read_env_int(name: str, default: int, min_value: int, max_value: int) -> int:
        raw = (os.getenv(name, str(default)) or str(default)).strip()
        try:
            value = int(raw)
        except Exception:
            value = default
        return max(min_value, min(max_value, value))

    @staticmethod
    def _read_env_float(name: str, default: float, min_value: float, max_value: float) -> float:
        raw = (os.getenv(name, str(default)) or str(default)).strip()
        try:
            value = float(raw)
        except Exception:
            value = default
        return max(min_value, min(max_value, value))

    @staticmethod
    def _read_env_bool(name: str, default: bool = False) -> bool:
        raw_default = "1" if default else "0"
        raw = (os.getenv(name, raw_default) or raw_default).strip().lower()
        return raw in {"1", "true", "yes", "on"}

    def _init_path_variables(self) -> None:
        """初始化知识库路径变量。"""
        saved_data_dir = self._read_env_text("DATA_DIR")
        saved_index_dir = self._read_env_text("INDEX_DIR")
        self.data_dir = tk.StringVar(value=saved_data_dir or str(Path("data").resolve()))
        self.index_dir = tk.StringVar(value=saved_index_dir or str(Path("index").resolve()))

    def _init_story_api_variables(self) -> None:
        """初始化主故事 API 相关变量。"""
        self.api_key = tk.StringVar(value=os.getenv("DEEPSEEK_API_KEY", ""))
        self.base_url = tk.StringVar(
            value=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")
        )
        self.model = tk.StringVar(value=os.getenv("DEEPSEEK_MODEL", "deepseek-chat"))
        self.api_preset = tk.StringVar(value="DeepSeek")

    def _init_generation_parameter_variables(self) -> None:
        """初始化故事生成参数变量。"""
        self.top_k = tk.IntVar(value=self._read_env_int("TOP_K", 6, 1, 20))
        self.temperature = tk.DoubleVar(
            value=self._read_env_float("TEMPERATURE", 0.7, 0.0, 1.5)
        )
        self.rag_min_score = tk.DoubleVar(
            value=self._read_env_float("RAG_MIN_SCORE", 0.12, 0.0, 1.0)
        )
        self.category = tk.StringVar(value=self._read_env_text("STORY_CATEGORY", "职场"))
        self.style = tk.StringVar(
            value=self._read_env_text(
                "STORY_STYLE",
                "情感起伏/反转/细节描写/有画面感/口语化",
            )
        )
        self.target_chars = tk.IntVar(
            value=self._read_env_int("TARGET_CHARS", 1800, 500, 30000)
        )
        self.story_template_key = tk.StringVar(
            value=self._read_env_text("STORY_TEMPLATE_KEY", DEFAULT_STORY_TEMPLATE_KEY)
        )
        self.story_template_strategy = tk.StringVar(
            value=normalize_story_template_strategy(
                self._read_env_text(
                    "STORY_TEMPLATE_STRATEGY",
                    DEFAULT_STORY_TEMPLATE_STRATEGY,
                )
            )
        )
        self.story_creativity_mode = tk.StringVar(
            value=normalize_story_creativity_mode(
                self._read_env_text(
                    "STORY_CREATIVITY_MODE",
                    DEFAULT_STORY_CREATIVITY_MODE,
                )
            )
        )
        self.story_quality_review_enabled = tk.BooleanVar(
            value=self._read_env_bool("STORY_QUALITY_REVIEW", True)
        )
        self.story_quality_min_avg = tk.DoubleVar(
            value=self._read_env_float("STORY_QUALITY_MIN_AVG", 7.4, 1.0, 10.0)
        )
        self.story_quality_min_dim = tk.DoubleVar(
            value=self._read_env_float("STORY_QUALITY_MIN_DIM", 6.8, 1.0, 10.0)
        )
        self.story_outline_alignment_strict = tk.BooleanVar(
            value=self._read_env_bool("STORY_OUTLINE_ALIGNMENT_STRICT", True)
        )
        self.story_outline_alignment_max_attempts = tk.IntVar(
            value=self._read_env_int("STORY_OUTLINE_ALIGNMENT_MAX_ATTEMPTS", 2, 1, 4)
        )
        self.model_only = tk.BooleanVar(value=self._read_env_bool("MODEL_ONLY", False))

    def _init_runtime_state_variables(self) -> None:
        """初始化项目与生成运行态变量。"""
        self.current_outline: str | None = None
        from src.project_manager import ProjectManager
        self.project_manager = ProjectManager()
        self.current_project = None
        self.parsed_sections: list[dict] = []
        self.generated_content: str = ""
        self.story_memory_ledger: list[dict] = []
        self.chapter_quality_reports: list[dict] = []

    def _build_default_story_provider_map(self) -> dict:
        """返回默认故事 API 提供商配置。"""
        return {
            "OpenAI": {
                "base_url": "https://api.openai.com/v1",
                "models": ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "gpt-4", "gpt-3.5-turbo", "o1-preview", "o1-mini"],
                "key": ""
            },
            "Google Gemini": {
                "base_url": "https://generativelanguage.googleapis.com/v1beta/openai",
                "models": ["gemini-2.0-flash-exp", "gemini-1.5-pro", "gemini-1.5-flash", "gemini-1.0-pro"],
                "key": ""
            },
            "Anthropic Claude": {
                "base_url": "https://api.anthropic.com/v1",
                "models": ["claude-3-5-sonnet-20241022", "claude-3-5-haiku-20241022", "claude-3-opus-20240229", "claude-3-sonnet-20240229"],
                "key": ""
            },
            "DeepSeek": {
                "base_url": "https://api.deepseek.com",
                "models": ["deepseek-chat", "deepseek-reasoner", "deepseek-coder"],
                "key": ""
            },
            "Moonshot (月之暗面)": {
                "base_url": "https://api.moonshot.cn/v1",
                "models": ["moonshot-v1-128k", "moonshot-v1-32k", "moonshot-v1-8k"],
                "key": ""
            },
            "智谱AI (GLM)": {
                "base_url": "https://open.bigmodel.cn/api/paas/v4",
                "models": ["glm-4-plus", "glm-4", "glm-4-air", "glm-4-flash", "glm-4-long"],
                "key": ""
            },
            "阿里通义 (Qwen)": {
                "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
                "models": ["qwen-max", "qwen-plus", "qwen-turbo", "qwen-long", "qwen2.5-72b-instruct"],
                "key": ""
            },
            "百度文心": {
                "base_url": "https://aip.baidubce.com/rpc/2.0/ai_custom/v1/wenxinworkshop",
                "models": ["ernie-4.0-8k", "ernie-4.0-turbo-8k", "ernie-3.5-8k"],
                "key": ""
            },
            "硅基流动 (SiliconFlow)": {
                "base_url": "https://api.siliconflow.cn/v1",
                "models": ["Qwen/Qwen2.5-72B-Instruct", "deepseek-ai/DeepSeek-V3", "Pro/Qwen/Qwen2.5-7B-Instruct"],
                "key": ""
            },
            "Groq": {
                "base_url": "https://api.groq.com/openai/v1",
                "models": ["llama-3.3-70b-versatile", "llama-3.1-8b-instant", "mixtral-8x7b-32768", "gemma2-9b-it"],
                "key": ""
            },
            "零一万物 (01.AI)": {
                "base_url": "https://api.lingyiwanwu.com/v1",
                "models": ["yi-lightning", "yi-large", "yi-medium", "yi-spark"],
                "key": ""
            },
            "自定义": {
                "base_url": "",
                "models": [
                    "claude-sonnet-4-5",
                    "claude-sonnet-4-5-20250929",
                    "claude-sonnet-4",
                    "claude-sonnet-4-20250514",
                    "claude-3-7-sonnet-20250219",
                    "gemini-3-pro-preview",
                    "gemini-3-flash-preview",
                    "gemini-2.5-pro",
                    "gemini-2.5-flash",
                    "gemini-2.5-flash-lite",
                    "gemini-2.0-flash",
                    "gemini-3-pro-image",
                    "gpt-4o",
                    "gpt-4o-mini",
                    "gpt-3.5-turbo",
                    "custom-model"
                ],
                "key": ""
            }
        }

    @staticmethod
    def _build_story_api_presets(provider_map: dict) -> dict:
        """从 provider map 生成兼容旧代码的故事 API presets。"""
        presets = {}
        for name, config in provider_map.items():
            presets[name] = {
                "base_url": config["base_url"],
                "model": config["models"][0],
                "key": config["key"]
            }
        return presets

    def _build_default_image_provider_map(self) -> dict:
        """返回默认图片 API 提供商配置。"""
        return {
            "OpenAI (DALL-E)": {
                "base_url": "https://api.openai.com/v1",
                "models": ["dall-e-3", "dall-e-2"],
                "key": "",
                "provider": "openai",
            },
            "V-API (Flux)": {
                "base_url": "https://api.v-api.ai/v1",
                "models": ["flux-1.1-pro", "flux-1-schnell", "flux-1-dev"],
                "key": "",
                "provider": "openai",
            },
            "硅基流动 (图片)": {
                "base_url": "https://api.siliconflow.cn/v1",
                "models": ["black-forest-labs/FLUX.1-schnell", "stabilityai/stable-diffusion-3-medium"],
                "key": "",
                "provider": "openai",
            },
            "腾讯混元": {
                "base_url": "",
                "models": ["hunyuan"],
                "key": "",
                "provider": "hunyuan",
            },
            "自定义": {
                "base_url": "",
                "models": ["custom-model"],
                "key": "",
                "provider": "openai",
            }
        }

    @staticmethod
    def _build_image_api_presets(provider_map: dict) -> dict:
        """从 provider map 生成兼容旧代码的图片 API presets。"""
        presets = {}
        for name, config in provider_map.items():
            presets[name] = {
                "base_url": config["base_url"],
                "model": config["models"][0],
                "key": config["key"],
                "provider": config.get("provider", "openai"),
            }
        return presets
    
    @staticmethod
    def _normalize_story_provider_map(provider_map: dict) -> dict:
        """Normalize legacy/garbled story provider labels into canonical names."""
        normalized = {}
        for raw_name, cfg in (provider_map or {}).items():
            if not isinstance(cfg, dict):
                continue
            base = str(cfg.get("base_url", "")).lower()
            models = list(cfg.get("models", []) or [])
            raw_name_text = str(raw_name or "")
            raw_name_lower = raw_name_text.lower()
            is_custom_alias = (
                "custom" in raw_name_lower
                or "自定义" in raw_name_text
                or "鑷畾涔?" in raw_name_text
                or "閼奉亜鐣炬稊?" in raw_name_text
            )
            if "api.deepseek.com" in base:
                name = "DeepSeek"
            elif "api.openai.com" in base:
                name = "OpenAI"
            elif "azure.com" in base:
                name = "Azure OpenAI"
            elif "moonshot.cn" in base:
                name = "Moonshot (Kimi)"
            elif "bigmodel.cn" in base:
                name = "Zhipu AI (GLM)"
            elif "dashscope.aliyuncs.com" in base:
                name = "Alibaba Qwen"
            elif "baidubce.com" in base:
                name = "Baidu ERNIE"
            elif "siliconflow.cn" in base:
                name = "SiliconFlow"
            elif "lingyiwanwu.com" in base:
                name = "01.AI"
            elif not base and ("custom-model" in models or is_custom_alias):
                name = "Custom"
            else:
                name = raw_name

            current = normalized.get(name)
            if current is None:
                normalized[name] = cfg
            else:
                if not current.get("key") and cfg.get("key"):
                    current["key"] = cfg["key"]
                merged_models = list(current.get("models", []) or [])
                for model in models:
                    if model not in merged_models:
                        merged_models.append(model)
                current["models"] = merged_models
        return normalized

    @staticmethod
    def _normalize_image_provider_map(provider_map: dict) -> dict:
        """Normalize legacy/garbled image provider labels into canonical names."""
        normalized = {}
        for raw_name, cfg in (provider_map or {}).items():
            if not isinstance(cfg, dict):
                continue
            base = str(cfg.get("base_url", "")).lower()
            provider = str(cfg.get("provider", "openai")).lower()
            models = list(cfg.get("models", []) or [])
            raw_name_text = str(raw_name or "")
            raw_name_lower = raw_name_text.lower()
            is_custom_alias = (
                "custom" in raw_name_lower
                or "自定义" in raw_name_text
                or "鑷畾涔?" in raw_name_text
                or "閼奉亜鐣炬稊?" in raw_name_text
            )
            if provider == "hunyuan":
                name = "Tencent Hunyuan"
            elif "api.openai.com" in base:
                name = "OpenAI (DALL-E)"
            elif "v-api.ai" in base:
                name = "V-API (Flux)"
            elif "siliconflow.cn" in base:
                name = "SiliconFlow (Image)"
            elif not base and ("custom-model" in models or is_custom_alias):
                name = "Custom"
            else:
                name = raw_name

            current = normalized.get(name)
            if current is None:
                normalized[name] = cfg
            else:
                if not current.get("key") and cfg.get("key"):
                    current["key"] = cfg["key"]
                merged_models = list(current.get("models", []) or [])
                for model in models:
                    if model not in merged_models:
                        merged_models.append(model)
                current["models"] = merged_models
        return normalized

    def _auto_load_story_api_selection(self):
        """自动加载故事 API 选择配置"""
        try:
            import os
            
            load_dotenv(override=True)
            
            # 加载故事创作功能API配置
            outline_api = os.getenv("STORY_OUTLINE_GEN_API", "DeepSeek")
            if hasattr(self, 'outline_gen_api'):
                self.outline_gen_api.set(outline_api)
                logger.info("loaded outline generation API: %s", outline_api)
            
            story_api = os.getenv("STORY_STORY_GEN_API", "DeepSeek")
            if hasattr(self, 'story_gen_api'):
                self.story_gen_api.set(story_api)
                logger.info("loaded story generation API: %s", story_api)
            
            # 更新故事创作功能API下拉框的选项
            if hasattr(self, 'api_presets') and hasattr(self, 'combo_outline_gen_api'):
                api_list = list(self.api_presets.keys())
                self.combo_outline_gen_api['values'] = api_list
                self.combo_story_gen_api['values'] = api_list
                logger.info("updated API option list: %s", api_list)
            
            # 同步到快速切换区域
            if hasattr(self, 'quick_story_api'):
                self.quick_story_api.set(story_api)
                logger.info("synced quick story API: %s", story_api)
                
        except Exception as e:
            logger.exception("load story API selection failed: %s", e)

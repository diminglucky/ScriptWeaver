"""Outline generation workflows."""

from tkinter import END, messagebox
import logging
import threading
from pathlib import Path

try:
    from dotenv import load_dotenv
except Exception:  # pragma: no cover - optional dependency
    def load_dotenv(*args, **kwargs):
        return False

from src.clients.deepseek_client import DeepSeekClient
from src.utils.text import sanitize as _sanitize

logger = logging.getLogger(__name__)


def print(*args, **kwargs):  # type: ignore[override]
    logger.info(" ".join(str(a) for a in args))


def _resolve_deepseek_client_cls():
    """Use aggregator module symbol so tests can monkey-patch one stable path."""
    try:
        from . import outline_generator as outline_generator_module  # local import avoids circular init timing issues

        patched = getattr(outline_generator_module, "DeepSeekClient", None)
        if patched is not None:
            return patched
    except Exception:
        pass
    return DeepSeekClient


class OutlineGenerateMixin:
    """Generate story outline via RAG or model-only paths."""
    def on_generate_outline(self) -> None:
        requirement = self._get_prompt_content()
        if not requirement:
            messagebox.showwarning("提示", "请先输入创作需求/主题")
            return

        self._refresh_story_creativity_nonce()
        api_config, selected_api, selected_model, api_key = self._resolve_outline_api_config()
        if not api_key:
            messagebox.showwarning("提示", f"API Key 为空，请在'基础 API 配置'中为 {selected_api} 填写后保存")
            return

        print(f"🤖 使用模型: {selected_model}")
        if self.model_only.get():
            self._generate_outline_model_only(requirement)
            return

        need_build = self._ensure_outline_index_ready()
        if need_build is None:
            return

        threading.Thread(
            target=lambda: self._run_outline_rag_generation_task(
                requirement=requirement,
                api_config=api_config,
                selected_api=selected_api,
                selected_model=selected_model,
                api_key=api_key,
                need_build=need_build,
            ),
            daemon=True,
        ).start()

    def _refresh_story_creativity_nonce(self) -> None:
        """为当前故事生成流程刷新创意签名。"""
        try:
            import time

            self._story_creativity_nonce = str(time.time_ns())
        except Exception:
            self._story_creativity_nonce = ""

    def _resolve_outline_api_config(self, use_ui_get: bool = False) -> tuple[dict, str, str, str]:
        """根据模型路由解析目录生成 API 配置。"""
        getter = self._ui_get if use_ui_get else (lambda fn: fn())

        fallback_provider = None
        if hasattr(self, "outline_gen_api"):
            fallback_provider = getter(self.outline_gen_api.get)
        if not fallback_provider and hasattr(self, "quick_story_api"):
            fallback_provider = getter(self.quick_story_api.get)
        if not fallback_provider and hasattr(self, "api_preset"):
            fallback_provider = getter(self.api_preset.get)

        fallback_model = None
        if hasattr(self, "story_model_var"):
            fallback_model = getter(self.story_model_var.get)
        elif hasattr(self, "model"):
            fallback_model = getter(self.model.get)

        api_config = getter(
            lambda: self._resolve_task_api(
                "story_outline",
                fallback_provider=fallback_provider,
                fallback_model=fallback_model,
            )
        )
        selected_api = api_config.get("provider", "")
        selected_model = api_config.get("model", "")
        api_key = _sanitize(api_config.get("key", ""))
        return api_config, selected_api, selected_model, api_key

    def _ensure_outline_index_ready(self) -> bool | None:
        """确保目录生成所需索引已就绪。返回 None 表示用户取消。"""
        index_path = Path(self.index_dir.get()) / "kb.index"
        if index_path.exists():
            return False
        if messagebox.askyesno("提示", "未找到索引，是否现在根据当前数据目录自动构建？"):
            return True
        return None

    def _collect_outline_rag_contexts(self, requirement: str, need_build: bool) -> tuple[list[str], list]:
        """构建索引（按需）并检索 RAG 上下文。"""
        from src.kb.ingest import IngestConfig, KnowledgeBaseIngestor
        from src.kb.search import KnowledgeBaseSearcher, SearchConfig

        load_dotenv()
        if need_build:
            if hasattr(self, "update_header_status"):
                self._ui(self.update_header_status, "正在构建索引...", "⏳")
            cfg = IngestConfig(
                data_root=Path(self._ui_get(self.data_dir.get)),
                index_dir=Path(self._ui_get(self.index_dir.get)),
            )
            KnowledgeBaseIngestor(cfg).build()

        if hasattr(self, "update_header_status"):
            self._ui(self.update_header_status, "检索资料中...", "🔍")
        top_k = self._ui_get(self.top_k.get)
        searcher = KnowledgeBaseSearcher(
            SearchConfig(
                index_dir=Path(self._ui_get(self.index_dir.get)),
                top_k=top_k,
            )
        )
        results = searcher.search(requirement, top_k)
        rag_rows = self._postprocess_rag_results(results) if hasattr(self, "_postprocess_rag_results") else results
        contexts = [c for c, _s, _m in rag_rows]
        return contexts, rag_rows

    def _emit_outline_generation_banner(self, requirement: str, rag_rows: list) -> None:
        """输出目录生成前的运行横幅。"""
        self._ui(self.output.delete, "1.0", END)
        if hasattr(self, "_build_story_run_banner"):
            banner = self._build_story_run_banner(requirement, self._ui_get(self.category.get), rag_rows)
            if banner:
                self._ui(self.output.insert, END, banner + "\n\n")
        self._ui(self.output.insert, END, "生成目录中...\n\n")

    def _finalize_outline_generation(self, outline_text: str, alignment_report) -> None:
        """写回目录结果并刷新章节选择与状态。"""
        self.current_outline = outline_text.strip()
        estimate = self._estimate_chars(self.current_outline)
        self.parsed_sections = self._parse_outline_sections(self.current_outline)
        self.story_memory_ledger = []
        self.chapter_quality_reports = []

        self._ui(self._update_section_selector)
        if hasattr(self, "_update_story_diagnostics_panel"):
            self._ui(self._update_story_diagnostics_panel)

        if alignment_report is not None:
            final_score = float(alignment_report.get("score", 0.0))
            final_reason = str(alignment_report.get("reason", "") or "")
            self._ui(self.status.set, f"目录已生成（对齐评分 {final_score:.2f}）")
            if final_reason and final_reason != "对齐通过":
                self._ui(self.output.insert, END, f"对齐检查提示：{final_reason}\n\n")
        else:
            self._ui(self.status.set, "目录已生成")

        self._ui(
            self.output.insert,
            END,
            f"目录（共{len(self.parsed_sections)}章，预估字数≈{estimate}字）\n\n{self.current_outline}\n\n",
        )
        if hasattr(self, "_auto_save_to_project"):
            self._ui(self._auto_save_to_project)
        if hasattr(self, "update_header_status"):
            self._ui(self.update_header_status, "目录生成完成", "✅")

    def _run_outline_rag_generation_task(
        self,
        *,
        requirement: str,
        api_config: dict,
        selected_api: str,
        selected_model: str,
        api_key: str,
        need_build: bool,
    ) -> None:
        """后台执行基于 RAG 的目录生成。"""
        try:
            self._ui(self.set_busy, True)
            self._ui(self.status.set, f"使用 {selected_api} 检索素材并生成目录中...")
            if hasattr(self, "update_header_status"):
                self._ui(self.update_header_status, "正在生成目录...", "📝")

            contexts, rag_rows = self._collect_outline_rag_contexts(requirement, need_build)
            if hasattr(self, "update_header_status"):
                self._ui(self.update_header_status, "AI生成目录中...", "📝")

            client = _resolve_deepseek_client_cls()(
                api_key=api_key,
                base_url=_sanitize(api_config.get("base_url", "")),
                model=selected_model,
            )
            outline_prompt = self._build_outline_prompt(requirement, contexts, self._ui_get(self.category.get))
            template = (
                self._get_story_template_profile(
                    requirement=requirement,
                    category=self._ui_get(self.category.get),
                )
                if hasattr(self, "_get_story_template_profile")
                else {}
            )
            outline_system_prompt = template.get(
                "outline_system_prompt",
                "你是资深中文创作者与编辑。请先产出结构化目录，不要写正文。",
            )
            self._emit_outline_generation_banner(requirement, rag_rows)

            outline_text = client.chat(
                [
                    {"role": "system", "content": outline_system_prompt},
                    {"role": "user", "content": outline_prompt},
                ],
                temperature=max(0.4, self._ui_get(self.temperature.get) - 0.2),
            )
            try:
                base_temp = float(self._ui_get(self.temperature.get))
            except Exception:
                base_temp = 0.7
            outline_text, alignment_report = self._refine_outline_with_alignment(
                client=client,
                requirement=requirement,
                contexts=contexts,
                category=self._ui_get(self.category.get),
                outline_text=outline_text,
                outline_system_prompt=outline_system_prompt,
                base_temperature=base_temp,
                stage_tag="rag",
            )
            self._finalize_outline_generation(outline_text, alignment_report)
        except Exception as exc:
            logger.exception("outline rag generation failed")
            brief = _sanitize(str(exc)) or exc.__class__.__name__
            self._ui(self.output.insert, END, f"❌ 生成目录失败：{brief}\n")
            self._ui(messagebox.showerror, "错误", brief)
            self._ui(self.status.set, "生成目录失败")
            if hasattr(self, "update_header_status"):
                self._ui(self.update_header_status, "生成目录失败", "❌")
        finally:
            self._ui(self.set_busy, False)

    def _generate_outline_model_only(self, requirement) -> None:
        threading.Thread(
            target=lambda: self._run_outline_model_only_task(requirement),
            daemon=True,
        ).start()

    def _run_outline_model_only_task(self, requirement: str) -> None:
        """后台执行仅模型目录生成。"""
        try:
            self._ui(self.set_busy, True)

            api_config, selected_api, selected_model, api_key = self._resolve_outline_api_config(use_ui_get=True)
            if not api_key:
                self._ui(
                    messagebox.showwarning,
                    "提示",
                    f"API Key 为空，请在'基础 API 配置'中为 {selected_api} 填写后保存",
                )
                return

            self._ui(self.status.set, f"使用 {selected_api} 生成目录中...")
            if hasattr(self, "update_header_status"):
                self._ui(self.update_header_status, "AI生成目录中...", "📝")

            print(f"🤖 使用模型: {selected_model}")
            client = _resolve_deepseek_client_cls()(
                api_key=api_key,
                base_url=_sanitize(api_config.get("base_url", "")),
                model=selected_model,
            )
            prompt = self._ui_get(lambda: self._build_outline_prompt(requirement, [], self.category.get()))
            template = (
                self._get_story_template_profile(
                    requirement=requirement,
                    category=self._ui_get(self.category.get),
                )
                if hasattr(self, "_get_story_template_profile")
                else {}
            )
            outline_system_prompt = template.get(
                "outline_system_prompt",
                "你是资深中文创作者与编辑。请先产出结构化目录，不要写正文。",
            )
            self._emit_outline_generation_banner(requirement, [])

            temperature_val = self._ui_get(self.temperature.get)
            outline_text = client.chat(
                [
                    {"role": "system", "content": outline_system_prompt},
                    {"role": "user", "content": prompt},
                ],
                temperature=max(0.4, temperature_val - 0.2),
            )
            try:
                base_temp = float(temperature_val)
            except Exception:
                base_temp = 0.7
            outline_text, alignment_report = self._refine_outline_with_alignment(
                client=client,
                requirement=requirement,
                contexts=[],
                category=self._ui_get(self.category.get),
                outline_text=outline_text,
                outline_system_prompt=outline_system_prompt,
                base_temperature=base_temp,
                stage_tag="model-only",
            )
            self._finalize_outline_generation(outline_text, alignment_report)
        except Exception as exc:
            self._ui(messagebox.showerror, "错误", str(exc))
            self._ui(self.status.set, "生成目录失败")
            if hasattr(self, "update_header_status"):
                self._ui(self.update_header_status, "生成目录失败", "❌")
        finally:
            self._ui(self.set_busy, False)

    

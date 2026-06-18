"""Outline generation workflows."""

from tkinter import END, messagebox
import logging
import threading
import time
from pathlib import Path
from typing import Optional

try:
    from dotenv import load_dotenv
except Exception:  # pragma: no cover - optional dependency
    def load_dotenv(*args, **kwargs):
        return False

from src.utils.text import sanitize as _sanitize
from src.gui.mixins.story_modules.story_infra import resolve_deepseek_client_cls as _resolve_deepseek_client_cls, log_print as print  # noqa: A001

logger = logging.getLogger(__name__)


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
        if use_ui_get:
            api_config = self._resolve_generation_api_config_safe("story_outline")
        else:
            api_config = self._resolve_generation_api_config("story_outline")
        selected_api = api_config.get("provider", "")
        selected_model = api_config.get("model", "")
        api_key = _sanitize(api_config.get("key", ""))
        return api_config, selected_api, selected_model, api_key

    def _get_story_generation_mode_key(self) -> str:
        mode = ""
        var = getattr(self, "story_generation_mode", None)
        if var is not None and hasattr(var, "get"):
            try:
                mode = str(var.get() or "").strip().lower()
            except Exception:
                mode = ""
        if not mode:
            mode = "balanced"
        return mode

    @staticmethod
    def _is_reasoning_outline_model(model_name: str) -> bool:
        model = str(model_name or "").strip().lower()
        if not model:
            return False
        markers = ("thinking", "reasoner", "r1", "o1", "o3", "deepseek-reasoner")
        return any(marker in model for marker in markers)

    def _compute_outline_max_tokens(self, model_name: str) -> int:
        mode = self._get_story_generation_mode_key()
        if mode == "fast":
            return 420
        if mode == "strict":
            return 900
        if self._is_reasoning_outline_model(model_name):
            return 560
        return 680

    def _should_prefer_low_latency_outline_alignment(self, model_name: str) -> bool:
        mode = self._get_story_generation_mode_key()
        if mode == "fast":
            return True
        return self._is_reasoning_outline_model(model_name)

    def _ensure_outline_index_ready(self) -> Optional[bool]:
        """确保目录生成所需索引已就绪。返回 None 表示用户取消。"""
        index_dir = Path(self.index_dir.get())
        has_index = (
            (index_dir / "v2" / "manifest.json").exists()
            or any(index_dir.glob("v2/**/chroma"))
        )
        if has_index:
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
                **self._rag_ingest_kwargs(),
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

    _OUTLINE_RETRY_MAX = 2
    _OUTLINE_RETRY_DELAYS = (0.5, 1.0)

    def _chat_with_connection_retry(
        self,
        client,
        messages: list[dict],
        *,
        temperature: float,
        max_tokens: Optional[int] = None,
        stage_label: str = "目录生成",
    ) -> str:
        """Wrap client.chat with automatic retry on transient connection errors."""
        _CONNECTION_MARKERS = (
            "connection error", "connection reset", "connection aborted",
            "network error", "timed out", "timeout", "temporarily unavailable",
            "remote protocol", "econnreset", "broken pipe",
        )
        last_exc: Optional[Exception] = None
        for attempt in range(self._OUTLINE_RETRY_MAX):
            try:
                return client.chat(
                    messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
            except Exception as exc:
                err_text = str(exc).lower()
                if not any(m in err_text for m in _CONNECTION_MARKERS):
                    raise
                last_exc = exc
                if attempt < self._OUTLINE_RETRY_MAX - 1:
                    delay = self._OUTLINE_RETRY_DELAYS[attempt]
                    try:
                        self._ui(
                            self.status.set,
                            f"{stage_label}网络波动，{delay:.0f}s 后自动重试（{attempt+1}/{self._OUTLINE_RETRY_MAX-1}）...",
                        )
                    except Exception:
                        pass
                    time.sleep(delay)
        raise last_exc  # type: ignore[misc]

    def _stream_outline_generation(
        self,
        client,
        messages: list[dict],
        *,
        temperature: float,
        max_tokens: int,
        stage_label: str = "目录生成",
    ) -> str:
        """流式生成目录，让用户实时看到文字出现。"""
        outline_text = ""
        _buf = ""
        _last_t = time.time()
        _FLUSH_INTERVAL = 0.08
        try:
            for delta in client.stream(
                messages,
                temperature=temperature,
                max_tokens=max_tokens,
            ):
                outline_text += delta
                _buf += delta
                now = time.time()
                if now - _last_t >= _FLUSH_INTERVAL or "\n" in delta:
                    self._ui(self.output.insert, END, _buf)
                    self._ui(self.output.see, END)
                    _buf = ""
                    _last_t = now
            if _buf:
                self._ui(self.output.insert, END, _buf)
                self._ui(self.output.see, END)
        except Exception as exc:
            err_text = str(exc).lower()
            _CONNECTION_MARKERS = (
                "connection error", "connection reset", "timed out",
                "timeout", "temporarily unavailable", "broken pipe",
            )
            if any(m in err_text for m in _CONNECTION_MARKERS) and not outline_text.strip():
                self._ui(self.status.set, f"{stage_label}网络波动，回退到阻塞调用...")
                return self._chat_with_connection_retry(
                    client, messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    stage_label=stage_label,
                )
            if outline_text.strip():
                return outline_text.strip()
            raise
        return outline_text.strip()

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
        if hasattr(self, "_invalidate_chapter_blueprints"):
            self._invalidate_chapter_blueprints()

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
            f"\n\n目录（共{len(self.parsed_sections)}章，预估字数≈{estimate}字）\n\n",
        )
        if hasattr(self, "_auto_save_to_project"):
            self._ui(self._auto_save_to_project)
        if hasattr(self, "update_header_status"):
            self._ui(self.update_header_status, "目录生成完成", "✅")

    def _offer_story_direction_preview(
        self,
        *,
        client,
        requirement: str,
        contexts: Optional[list] = None,
    ) -> None:
        """目录生成完成后自动触发全书总览预览，让用户在写正文前确认故事走向。"""
        if not hasattr(self, "_ensure_story_global_overview_before_generation"):
            return
        if not hasattr(self, "_is_story_global_overview_enabled"):
            return
        if not self._is_story_global_overview_enabled():
            return

        category = self._ui_get(self.category.get) if hasattr(self, "_ui_get") else self.category.get()
        outline_text = getattr(self, "current_outline", "") or ""

        if hasattr(self, "update_header_status"):
            self._ui(self.update_header_status, "正在生成故事走向预览...", "🧭")
        self._ui(self.status.set, "正在生成全书总览，供你确认故事走向...")

        action, overview_text = self._ensure_story_global_overview_before_generation(
            client=client,
            requirement=requirement,
            category=category,
            contexts=contexts or [],
            outline_text=outline_text,
            force_review=True,
        )
        if action == "accept" and overview_text:
            self._ui(self.output.insert, END, "\n🧭 已确认全书总览（后续故事生成将按此方向展开）\n\n")
            self._ui(self.status.set, "全书总览已确认，可开始生成正文")
            if hasattr(self, "update_header_status"):
                self._ui(self.update_header_status, "总览已确认，可生成正文", "✅")
        elif action == "discard":
            self._ui(self.output.insert, END, "\n↩️ 已跳过全书总览确认\n\n")
            self._ui(self.status.set, "已跳过全书总览，可直接生成正文")
            if hasattr(self, "update_header_status"):
                self._ui(self.update_header_status, "目录生成完成（总览已跳过）", "✅")

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
            outline_max_tokens = self._compute_outline_max_tokens(selected_model)
            prefer_low_latency_alignment = self._should_prefer_low_latency_outline_alignment(selected_model)
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

            outline_text = self._stream_outline_generation(
                client,
                [
                    {"role": "system", "content": outline_system_prompt},
                    {"role": "user", "content": outline_prompt},
                ],
                temperature=max(0.4, self._ui_get(self.temperature.get) - 0.2),
                max_tokens=outline_max_tokens,
                stage_label="RAG目录生成",
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
                prefer_low_latency=prefer_low_latency_alignment,
                retry_max_tokens=outline_max_tokens,
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
            outline_max_tokens = self._compute_outline_max_tokens(selected_model)
            prefer_low_latency_alignment = self._should_prefer_low_latency_outline_alignment(selected_model)
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
            outline_text = self._stream_outline_generation(
                client,
                [
                    {"role": "system", "content": outline_system_prompt},
                    {"role": "user", "content": prompt},
                ],
                temperature=max(0.4, temperature_val - 0.2),
                max_tokens=outline_max_tokens,
                stage_label="目录生成",
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
                prefer_low_latency=prefer_low_latency_alignment,
                retry_max_tokens=outline_max_tokens,
            )
            self._finalize_outline_generation(outline_text, alignment_report)
        except Exception as exc:
            self._ui(messagebox.showerror, "错误", str(exc))
            self._ui(self.status.set, "生成目录失败")
            if hasattr(self, "update_header_status"):
                self._ui(self.update_header_status, "生成目录失败", "❌")
        finally:
            self._ui(self.set_busy, False)

    

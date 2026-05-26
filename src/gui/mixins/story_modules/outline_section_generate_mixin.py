"""Section generation workflows based on parsed outlines."""

from tkinter import END, messagebox, scrolledtext
import hashlib
import logging
import os
import re
import threading
import time
from concurrent.futures import ThreadPoolExecutor, Future
import tkinter as tk
from pathlib import Path

try:
    from dotenv import load_dotenv
except Exception:  # pragma: no cover - optional dependency
    def load_dotenv(*args, **kwargs):
        return False

from src.utils.text import sanitize as _sanitize
from src.gui.helpers.story_quality import (
    extract_last_sentence,
    should_polish,
    strip_duplicate_lines,
)
from src.gui.mixins.story_modules.story_infra import resolve_deepseek_client_cls as _resolve_deepseek_client_cls, log_print as print  # noqa: A001

logger = logging.getLogger(__name__)

CHAPTER_SEPARATOR = "=" * 50
CHAPTER_HEADER_RE = re.compile(
    r"(?:\n|^)(?P<sep>={20,})\n【第\s*(?P<chapter>\d+)\s*/\s*(?P<total>\d+)\s*章：(?P<title>[^\n】]+)】\n\n",
    re.S,
)
COMPLETED_CHAPTER_BLOCK_RE = re.compile(
    r"(?P<block>\n?={20,}\n【第\s*(?P<chapter>\d+)\s*/\s*(?P<total>\d+)\s*章：(?P<title>[^\n】]+)】\n\n"
    r"(?P<body>.*?)\n\n={20,}\n✅ 第\s*(?P=chapter)\s*章完成！本章字数：(?P<chars>\d+)\s*字\n)",
    re.S,
)


class OutlineSectionGenerateMixin:
    """Generate sections and continue writing chapter-by-chapter."""

    # 流式输出缓冲配置（优化性能）
    STREAM_BUFFER_SIZE = 30      # 累积 30 个字符或
    STREAM_FLUSH_INTERVAL = 0.1  # 100ms 刷新一次

    def _run_modal_ui_call(self, func, *args, **kwargs):
        """Execute modal UI call with compatibility fallback for tests/stubs."""
        if hasattr(self, "_ui_modal"):
            return self._ui_modal(func, *args, **kwargs)
        if hasattr(self, "_ui"):
            return self._ui(func, *args, **kwargs)
        return func(*args, **kwargs)

    @staticmethod
    def _is_connection_like_error(error_text: str) -> bool:
        text = str(error_text or "").strip().lower()
        if not text:
            return False
        markers = (
            "connection error",
            "connection reset",
            "connection aborted",
            "network error",
            "timed out",
            "timeout",
            "temporarily unavailable",
            "remote protocol",
            "econnreset",
            "broken pipe",
            "bad gateway",
            "502",
            "503",
            "429",
            "rate limit",
            "service unavailable",
            "server error",
            "internal server error",
        )
        return any(mark in text for mark in markers)

    @staticmethod
    def _build_token_candidates(max_tokens: int, *, floor: int = 600) -> list[int]:
        upper = max(600, int(max_tokens))
        candidates = [upper, max(floor, int(upper * 0.7))]
        unique: list[int] = []
        for val in candidates:
            cur = max(floor, int(val))
            if cur not in unique:
                unique.append(cur)
        return unique

    def _chat_with_retry_and_token_fallback(
        self,
        *,
        client,
        prompt: str,
        temperature: float,
        max_tokens: int,
        stage_label: str,
    ) -> tuple[str, str]:
        """Call chat with retries and smaller token budgets for unstable gateways."""
        last_error = ""
        token_candidates = self._build_token_candidates(max_tokens)
        for idx, tokens in enumerate(token_candidates):
            try:
                text = client.chat(
                    [{"role": "user", "content": prompt}],
                    temperature=temperature,
                    max_tokens=tokens,
                ).strip()
                if text:
                    return text, ""
                last_error = "empty response"
            except Exception as exc:
                last_error = _sanitize(str(exc)) or exc.__class__.__name__
                if not self._is_connection_like_error(last_error):
                    raise
            if idx < len(token_candidates) - 1:
                try:
                    if hasattr(self, "status"):
                        self._ui(
                            self.status.set,
                            f"{stage_label}网络波动，自动重试中（{idx+1}/{len(token_candidates)-1}）...",
                        )
                except Exception:
                    pass
                time.sleep(min(1.2, 0.45 * (idx + 1)))
        return "", last_error

    def on_generate_section(self) -> None:
        """生成选中的章节"""
        if not self.parsed_sections:
            messagebox.showwarning("提示", "请先生成目录")
            return
        
        query = self._get_prompt_content()
        if not query:
            messagebox.showwarning("提示", "请先输入创作需求/主题")
            return
        try:
            import time
            self._story_creativity_nonce = str(time.time_ns())
        except Exception:
            self._story_creativity_nonce = ""
        
        # 章节生成前置检查：根据模型路由确认 API Key
        api_config = self._resolve_generation_api_config("story_generate")
        if not _sanitize(api_config.get("key", "")):
            messagebox.showwarning("提示", "API Key 为空，请在设置页配置")
            return
        
        # 获取选中的章节索引
        selected_index = self.section_selector.current()
        if selected_index < 0:
            messagebox.showwarning("提示", "请选择要生成的章节")
            return
        
        # 启动生成
        if self.model_only.get():
            self._generate_single_section(query, [], selected_index)
        else:
            # 带知识库检索
            need_build = False
            index_dir = Path(self.index_dir.get())
            has_index = (index_dir / "kb.index").exists() or (index_dir / "kb.faiss").exists()
            if not has_index:
                if messagebox.askyesno("提示", "未找到索引，是否现在构建？"):
                    need_build = True
                else:
                    return
            
            def task():
                try:
                    self._ui(self.set_busy, True)
                    from src.kb.ingest import IngestConfig, KnowledgeBaseIngestor
                    from src.kb.search import KnowledgeBaseSearcher, SearchConfig
                    load_dotenv()
                    if need_build:
                        cfg = IngestConfig(data_root=Path(self._ui_get(self.data_dir.get)), index_dir=Path(self._ui_get(self.index_dir.get)))
                        KnowledgeBaseIngestor(cfg).build()
                    searcher = KnowledgeBaseSearcher(SearchConfig(index_dir=Path(self._ui_get(self.index_dir.get)), top_k=self._ui_get(self.top_k.get)))
                    results = searcher.search(query, self._ui_get(self.top_k.get))
                    rag_rows = self._postprocess_rag_results(results) if hasattr(self, "_postprocess_rag_results") else results
                    contexts = [c for c, _s, _m in rag_rows]
                    self._generate_single_section_with_contexts(query, contexts, selected_index)
                except Exception as e:
                    self._report_section_generation_error(selected_index, e)
                finally:
                    self._ui(self.set_busy, False)
            threading.Thread(target=task, daemon=True).start()
    
    
    def on_continue_next_section(self) -> None:
        """继续生成下一章"""
        current_index = self.section_selector.current()
        if current_index < 0:
            messagebox.showwarning("提示", "请先选择当前章节")
            return
        
        next_index = current_index + 1
        if next_index >= len(self.parsed_sections):
            messagebox.showinfo("提示", "已经是最后一章了！")
            return
        
        # 自动选中下一章
        self.section_selector.current(next_index)
        
        # 直接生成
        self.on_generate_section()
    
    def _parallel_post_stream_repairs(
        self,
        *,
        client,
        section_content: str,
        section_title: str,
        section_index: int,
        previous_content: str,
        requirement: str,
        category: str,
        include_memory: bool = False,
    ) -> tuple[str, str, "dict | None", "dict | None"]:
        """并行执行末尾修复、衔接修复、质量评审、记忆提取，减少串行等待。

        Returns:
            (tail_patch, transition_result, review, memory_entry)
        """
        fast = hasattr(self, '_is_story_fast_mode') and self._is_story_fast_mode()
        quality_enabled = (not fast) and self._is_story_quality_review_enabled()

        # 末尾截断修复始终开启（不受快速模式/质量评审开关影响）
        need_tail = not self._is_section_tail_complete(section_content)
        need_transition = quality_enabled and section_index > 0
        include_memory = include_memory and quality_enabled

        tasks_needed = sum([need_tail, need_transition, quality_enabled, include_memory])
        if tasks_needed == 0:
            return "", section_content, None, None

        with ThreadPoolExecutor(max_workers=max(1, tasks_needed)) as pool:
            ft_tail = pool.submit(
                self._repair_section_tail_if_needed,
                client, section_title, section_content,
            ) if need_tail else None

            ft_transition = pool.submit(
                self._repair_section_transition_if_needed,
                client,
                section_index=section_index,
                section_title=section_title,
                previous_content=previous_content,
                section_content=section_content,
            ) if need_transition else None

            ft_review = pool.submit(
                self._review_section_quality,
                client, section_title, section_content,
                requirement, category,
            ) if quality_enabled else None

            # 优化③：记忆提取也并行执行
            ft_memory = pool.submit(
                self._extract_memory_entry,
                client,
                section_index=section_index,
                section_title=section_title,
                section_content=section_content,
            ) if include_memory else None

            _REPAIR_TIMEOUT = 45  # 单个后处理任务最多等 45 秒

            def _safe_result(ft, default, label: str = ""):
                if ft is None:
                    return default
                try:
                    return ft.result(timeout=_REPAIR_TIMEOUT)
                except Exception as exc:
                    logger.warning("post-stream %s timed out or failed: %s", label, str(exc)[:60])
                    return default

            tail_patch = _safe_result(ft_tail, "", "tail_repair")
            transition_result = _safe_result(ft_transition, section_content, "transition_repair")
            review = _safe_result(ft_review, None, "quality_review")
            memory_entry = _safe_result(ft_memory, None, "memory_extract")

        return tail_patch, transition_result, review, memory_entry

    @staticmethod
    def _merge_post_stream_repairs(
        section_content: str,
        tail_patch: str,
        transition_result: str,
    ) -> str:
        """合并并行修复的结果：先应用衔接修复（改开头），再追加末尾修复。"""
        merged = section_content
        if transition_result and transition_result != section_content:
            merged = transition_result
        if tail_patch:
            if not merged.endswith("\n"):
                merged += "\n"
            merged += tail_patch
        return merged

    def _generate_in_sections(self, client, requirement, contexts, sections, target_chars) -> bool:
        """分段生成长文本。返回 True=正常完成，False=中途取消。"""
        total_sections = len(sections)
        target_per_section = int(target_chars / total_sections)

        self._ui(self.output.insert, END, f"📖 开始分段生成（共{total_sections}段，目标总字数{target_chars}字）\n\n")
        self._ui(self.output.insert, END, "=" * 50 + "\n\n")
        
        accumulated_content = ""
        style_part = self.style.get().strip()
        category = self.category.get()
        stopped_by_preview = False

        fast = hasattr(self, '_is_story_fast_mode') and self._is_story_fast_mode()
        for idx, section in enumerate(sections):
            overview_action, section_overview_plan = self._prepare_section_overview_before_generation(
                client=client,
                section=section,
                section_index=idx,
                total_sections=total_sections,
                requirement=requirement,
                contexts=contexts,
                category=category,
                previous_content=accumulated_content,
                skip_dialog=True,
            )
            if overview_action == "discard":
                self._ui(self.output.insert, END, f"⏹️ 已取消第 {idx+1} 段生成（章节总览未采用）。\n")
                self._ui(self.output.see, END)
                self._ui(self.status.set, f"已停止（第 {idx+1} 段总览取消）")
                if hasattr(self, 'update_header_status'):
                    self._ui(self.update_header_status, "分段生成已停止", "⏹️")
                stopped_by_preview = True
                break

            # 更新状态
            self._ui(self.status.set, f"生成第 {idx+1}/{total_sections} 段: {section['title']}")
            self._ui(self.output.insert, END, f"【正在生成第 {idx+1}/{total_sections} 段】\n\n")
            self._ui(self.output.see, END)
            section_start_pos = self._ui_get(self.output.index, "end-1c") if hasattr(self, "_ui_get") else self.output.index("end-1c")
            # 更新顶部状态栏
            if hasattr(self, 'update_header_status'):
                self._ui(self.update_header_status, f"生成中 ({idx+1}/{total_sections})", "📝")
            
            # 构建本段提示词
            section_prompt = self._build_section_prompt(
                section=section,
                section_index=idx,
                total_sections=total_sections,
                previous_content=accumulated_content,
                requirement=requirement,
                contexts=contexts,
                category=category,
                style_part=style_part,
                target_chars_per_section=target_per_section,
                section_overview_plan=section_overview_plan,
            )
            template = (
                self._get_story_template_profile(requirement=requirement, category=category)
                if hasattr(self, "_get_story_template_profile")
                else {}
            )
            story_system_prompt = template.get(
                "story_system_prompt",
                "你是资深中文叙事作者，擅长结合资料写出有观点、有结构的中文故事。",
            )
            if hasattr(self, '_build_enhanced_system_prompt'):
                story_system_prompt = self._build_enhanced_system_prompt(story_system_prompt)
            
            # 流式生成本段（使用缓冲批量更新 UI + 连接中断自动重试）
            section_content = self._stream_section_content(
                client=client,
                story_system_prompt=story_system_prompt,
                section_prompt=section_prompt,
                target_per_section=target_per_section,
            )

            # 并行执行：末尾修复 + 衔接修复 + 质量评审 + 记忆提取
            original_content = section_content
            tail_patch, transition_result, review, memory_entry = self._parallel_post_stream_repairs(
                client=client,
                section_content=section_content,
                section_title=section.get("title", ""),
                section_index=idx,
                previous_content=accumulated_content,
                requirement=requirement,
                category=category,
                include_memory=not fast,
            )
            section_content = self._merge_post_stream_repairs(
                section_content, tail_patch, transition_result,
            )
            if section_content != original_content:
                self._ui(self.output.delete, section_start_pos, "end-1c")
                self._ui(self.output.insert, END, section_content)
                self._ui(self.output.see, END)

            # 质量评审结果 → 自动精修（优化④由环境变量控制）
            if review is not None:
                self._update_chapter_quality_report(idx, section.get("title", ""), review)
                if self._is_auto_polish_enabled():
                    min_avg, min_dim = self._get_story_quality_thresholds()
                    needs_polish = should_polish(review, min_avg_score=min_avg, min_dimension_score=min_dim)
                    if not needs_polish and self._needs_continuity_polish(review, idx):
                        needs_polish = True
                    if needs_polish:
                        polished = self._polish_section_text(
                            client,
                            section.get("title", ""),
                            section_content,
                            review,
                            target_per_section,
                            section_index=idx,
                            previous_content=accumulated_content,
                        )
                        if polished and polished != section_content:
                            self._ui(self.output.delete, section_start_pos, "end-1c")
                            self._ui(self.output.insert, END, polished)
                            self._ui(self.output.see, END)
                            section_content = polished

            preview_action = self._preview_generated_section_before_apply(
                client=client,
                section_index=idx,
                total_sections=total_sections,
                section_title=section.get("title", ""),
                section_content=section_content,
                requirement=requirement,
                category=category,
                previous_content=accumulated_content,
                skip_dialog=True,
            )
            if isinstance(preview_action, tuple):
                action_name, preview_text = preview_action
            else:
                action_name, preview_text = str(preview_action), section_content
            if preview_text and str(preview_text).strip():
                section_content = str(preview_text).strip()
                self._ui(self.output.delete, section_start_pos, "end-1c")
                self._ui(self.output.insert, END, section_content)
                self._ui(self.output.see, END)
            if action_name == "discard":
                self._ui(self.output.delete, section_start_pos, "end-1c")
                self._ui(self.output.insert, END, "⏹️ 已在预览阶段取消，本轮分段生成已停止。\n")
                self._ui(self.output.see, END)
                self._ui(self.status.set, f"已停止（第 {idx+1} 段预览取消）")
                if hasattr(self, 'update_header_status'):
                    self._ui(self.update_header_status, "分段生成已停止", "⏹️")
                stopped_by_preview = True
                break

            # 记忆账本已在并行池中提取完毕
            if memory_entry:
                self._update_story_memory_ledger(idx, section.get("title", ""), memory_entry)
            if hasattr(self, "_update_story_diagnostics_panel"):
                self._ui(self._update_story_diagnostics_panel)
            
            # 累积内容（用于下一段的上下文）
            accumulated_content += section_content
            
            # 段落分隔
            if idx < total_sections - 1:
                self._ui(self.output.insert, END, "\n\n")
                self._ui(self.output.see, END)
        
        # 完成提示
        if stopped_by_preview:
            return False
        final_length = len(accumulated_content)
        self._ui(self.output.insert, END, f"\n\n" + "=" * 50 + "\n")
        self._ui(self.output.insert, END, f"✅ 生成完成！总字数：{final_length} 字\n")
        self._ui(self.status.set, f"生成完成（{final_length} 字）")
        return True

    
    def _generate_single_section(self, query: str, contexts: list[str], section_index: int) -> None:
        """生成单个章节（无知识库）"""
        def task():
            try:
                self._ui(self.set_busy, True)
                
                api_config = self._resolve_generation_api_config_safe("story_generate")
                api_key = _sanitize(api_config.get("key", ""))
                if not api_key:
                    self._ui(messagebox.showwarning, "提示", f"API Key 为空，请在'基础 API 配置'中为 {api_config.get('provider', '')} 填写后保存")
                    return
                
                print(f"🤖 使用模型: {api_config.get('model', '')}")
                client = self._create_generation_client(api_config)
                self._do_generate_section(client, query, contexts, section_index)
            except Exception as e:
                self._report_section_generation_error(section_index, e)
            finally:
                self._ui(self.set_busy, False)
        threading.Thread(target=task, daemon=True).start()
    
    
    def _generate_single_section_with_contexts(self, query: str, contexts: list[str], section_index: int) -> None:
        """生成单个章节（带知识库）"""
        api_config = self._resolve_generation_api_config("story_generate")
        api_key = _sanitize(api_config.get("key", ""))
        if not api_key:
            self._ui(messagebox.showwarning, "提示", f"API Key 为空，请在'基础 API 配置'中为 {api_config.get('provider', '')} 填写后保存")
            return
        
        print(f"🤖 使用模型: {api_config.get('model', '')}")
        client = self._create_generation_client(api_config)
        self._do_generate_section(client, query, contexts, section_index)
    
    
    def _do_generate_section(
        self,
        client,
        query,
        contexts,
        section_index,
        existing_chapter_policy: str = "ask",
        skip_dialog: bool = False,
    ):
        """实际执行章节生成的核心逻辑。

        skip_dialog=True 时跳过所有阻塞弹窗（用于自动批量生成）。
        """
        section = self.parsed_sections[section_index]
        total_sections = len(self.parsed_sections)
        base_output_text = self._get_output_text_snapshot()

        try:
            overview_action, section_overview_plan = self._prepare_section_overview_before_generation(
                client=client,
                section=section,
                section_index=section_index,
                total_sections=total_sections,
                requirement=query,
                contexts=contexts,
                category=self.category.get(),
                previous_content=self.generated_content,
                skip_dialog=skip_dialog,
            )
            if overview_action == "discard":
                self._ui(self.status.set, f"已取消第 {section_index+1} 章生成（总览未采用）")
                if hasattr(self, "update_header_status"):
                    self._ui(self.update_header_status, f"第 {section_index+1} 章已取消", "↩️")
                return "preview_discard"

            target_per_section, section_prompt, story_system_prompt = self._prepare_section_generation_prompt(
                section=section,
                section_index=section_index,
                total_sections=total_sections,
                query=query,
                contexts=contexts,
                section_overview_plan=section_overview_plan,
            )
            section_start_pos = self._start_section_generation_ui(
                section_index=section_index,
                total_sections=total_sections,
                section_title=section["title"],
            )
            section_content = self._stream_section_content(
                client=client,
                story_system_prompt=story_system_prompt,
                section_prompt=section_prompt,
                target_per_section=target_per_section,
            )

            # 并行执行：末尾修复 + 衔接修复 + 质量评审 + 记忆提取
            fast = hasattr(self, '_is_story_fast_mode') and self._is_story_fast_mode()
            original_content = section_content
            tail_patch, transition_result, review, memory_entry = self._parallel_post_stream_repairs(
                client=client,
                section_content=section_content,
                section_title=section.get("title", ""),
                section_index=section_index,
                previous_content=self.generated_content,
                requirement=query,
                category=self.category.get(),
                include_memory=not fast,
            )
            section_content = self._merge_post_stream_repairs(
                section_content, tail_patch, transition_result,
            )
            if section_content != original_content:
                self._ui(self.output.delete, section_start_pos, "end-1c")
                self._ui(self.output.insert, END, section_content)
                self._ui(self.output.see, END)

            # 质量评审结果 → 自动精修（优化④由环境变量控制）
            if review is not None:
                if self._is_auto_polish_enabled():
                    min_avg, min_dim = self._get_story_quality_thresholds()
                    needs_polish = should_polish(review, min_avg_score=min_avg, min_dimension_score=min_dim)
                    if not needs_polish and self._needs_continuity_polish(review, section_index):
                        needs_polish = True
                    if needs_polish:
                        polished = self._polish_section_text(
                            client,
                            section.get("title", ""),
                            section_content,
                            review,
                            target_per_section,
                            section_index=section_index,
                            previous_content=self.generated_content,
                        )
                        if polished and polished != section_content:
                            self._ui(self.output.delete, section_start_pos, "end-1c")
                            self._ui(self.output.insert, END, polished)
                            self._ui(self.output.see, END)
                            section_content = polished

            preview_action = self._preview_generated_section_before_apply(
                client=client,
                section_index=section_index,
                total_sections=total_sections,
                section_title=section.get("title", ""),
                section_content=section_content,
                requirement=query,
                category=self.category.get(),
                previous_content=self.generated_content,
                skip_dialog=skip_dialog,
            )
            if isinstance(preview_action, tuple):
                action_name, preview_text = preview_action
            else:
                action_name, preview_text = str(preview_action), section_content

            if preview_text and str(preview_text).strip():
                section_content = str(preview_text).strip()

            if action_name == "discard":
                self._overwrite_output_text(base_output_text)
                self.generated_content = self._rebuild_generated_content_from_output(base_output_text)
                self._ui(self.status.set, f"已取消第 {section_index+1} 章入稿（预览后丢弃）")
                if hasattr(self, 'update_header_status'):
                    self._ui(self.update_header_status, f"第 {section_index+1} 章已丢弃", "↩️")
                return "preview_discard"

            action, final_output_text = self._apply_generated_section_output(
                base_output_text=base_output_text,
                section_index=section_index,
                total_sections=total_sections,
                section_title=section.get("title", ""),
                section_content=section_content,
                existing_chapter_policy=existing_chapter_policy,
            )
            self._overwrite_output_text(final_output_text)
            self.generated_content = self._rebuild_generated_content_from_output(final_output_text)

            if action in {"append", "replace"}:
                if review is not None:
                    self._update_chapter_quality_report(section_index, section.get("title", ""), review)
                # 记忆账本已在并行池中提取完毕
                if memory_entry:
                    self._update_story_memory_ledger(section_index, section.get("title", ""), memory_entry)
                if hasattr(self, "_update_story_diagnostics_panel"):
                    self._ui(self._update_story_diagnostics_panel)
                self._ui(self.status.set, f"第 {section_index+1} 章完成（{len(section_content)} 字）")
                if hasattr(self, 'update_header_status'):
                    self._ui(self.update_header_status, f"第 {section_index+1} 章完成", "✅")
                self._auto_save_to_project()
                return action

            if action == "keep_both":
                self._ui(self.status.set, f"第 {section_index+1} 章候选版本已生成（原章未替换）")
                if hasattr(self, 'update_header_status'):
                    self._ui(self.update_header_status, f"第 {section_index+1} 章候选已生成", "🧪")
                self._auto_save_to_project()
                return action

            self._ui(self.status.set, f"已保留第 {section_index+1} 章原版本（新版本已丢弃）")
            if hasattr(self, 'update_header_status'):
                self._ui(self.update_header_status, f"第 {section_index+1} 章保留原版本", "↩️")
            return action
        except Exception:
            self._overwrite_output_text(base_output_text)
            raise

    def _prepare_section_generation_prompt(
        self,
        *,
        section,
        section_index: int,
        total_sections: int,
        query: str,
        contexts: list[str],
        section_overview_plan: str = "",
    ) -> tuple[int, str, str]:
        """准备章节生成提示词与系统提示。"""
        target_chars = self.target_chars.get()
        target_per_section = int(target_chars / total_sections)
        self._ensure_generated_content_initialized(query, contexts)

        section_prompt = self._build_section_prompt(
            section=section,
            section_index=section_index,
            total_sections=total_sections,
            previous_content=self.generated_content,
            requirement=query,
            contexts=contexts,
            category=self.category.get(),
            style_part=self.style.get().strip(),
            target_chars_per_section=target_per_section,
            section_overview_plan=section_overview_plan,
        )
        template = (
            self._get_story_template_profile(requirement=query, category=self.category.get())
            if hasattr(self, "_get_story_template_profile")
            else {}
        )
        story_system_prompt = template.get(
            "story_system_prompt",
            "你是资深中文叙事作者，擅长结合资料写出有观点、有结构的中文故事。",
        )
        if hasattr(self, '_build_enhanced_system_prompt'):
            story_system_prompt = self._build_enhanced_system_prompt(story_system_prompt)
        return target_per_section, section_prompt, story_system_prompt

    def _ensure_generated_content_initialized(self, query: str, contexts: list[str]) -> None:
        """从当前输出里恢复已生成正文，必要时补运行横幅。"""
        current_output = self._get_output_text_snapshot()
        rebuilt = self._rebuild_generated_content_from_output(current_output)
        if rebuilt:
            self.generated_content = rebuilt
        elif "目录" in current_output and "\n\n" in current_output:
            parts = current_output.split("\n\n", 2)
            if len(parts) >= 3:
                self.generated_content = parts[2]
            elif len(parts) == 2:
                self.generated_content = current_output.split(self.current_outline)[-1].strip()
        else:
            self.generated_content = ""

        if not self.generated_content and hasattr(self, "_build_story_run_banner"):
            banner = self._build_story_run_banner(query, self.category.get(), contexts)
            if banner:
                self._ui(self.output.insert, END, banner + "\n\n")

    def _get_output_text_snapshot(self) -> str:
        """安全读取输出区全文。"""
        try:
            return str(self._ui_get(self.output.get, "1.0", END) or "")
        except Exception as exc:
            logger.debug("read output text failed: %s", exc)
            return ""

    def _overwrite_output_text(self, text: str) -> None:
        """用指定文本覆盖输出区，清理半截候选/报错堆栈。"""
        self._ui(self.output.delete, "1.0", END)
        if text:
            self._ui(self.output.insert, "1.0", text)
        self._ui(self.output.see, END)

    def _iter_completed_chapter_blocks(self, text: str) -> list[dict[str, object]]:
        """提取已完成章节块（仅匹配 ✅ 完成标记）。"""
        blocks: list[dict[str, object]] = []
        for match in COMPLETED_CHAPTER_BLOCK_RE.finditer(text or ""):
            blocks.append(
                {
                    "chapter": int(match.group("chapter")),
                    "total": int(match.group("total")),
                    "title": str(match.group("title")).strip(),
                    "start": match.start("block"),
                    "end": match.end("block"),
                    "body": str(match.group("body")).rstrip(),
                    "block": match.group("block"),
                }
            )
        return blocks

    def _iter_chapter_spans(self, text: str) -> list[dict[str, object]]:
        """提取所有章节块范围（含已完成/候选/失败残块）。"""
        raw_text = text or ""
        headers = list(CHAPTER_HEADER_RE.finditer(raw_text))
        spans: list[dict[str, object]] = []
        for idx, header in enumerate(headers):
            start = header.start()
            end = headers[idx + 1].start() if idx + 1 < len(headers) else len(raw_text)
            chapter_no = int(header.group("chapter"))
            block_text = raw_text[start:end]
            spans.append(
                {
                    "chapter": chapter_no,
                    "total": int(header.group("total")),
                    "title": str(header.group("title")).strip(),
                    "start": start,
                    "end": end,
                    "block": block_text,
                    "completed": bool(re.search(rf"✅\s*第\s*{chapter_no}\s*章完成", block_text)),
                    "candidate": bool(re.search(rf"🧪\s*第\s*{chapter_no}\s*章候选版本", block_text)),
                }
            )
        return spans

    def _build_chapter_block_text(
        self,
        *,
        section_index: int,
        total_sections: int,
        section_title: str,
        section_content: str,
        candidate: bool = False,
    ) -> str:
        """组装章节文本块。"""
        chapter_no = section_index + 1
        clean_content = (section_content or "").rstrip()
        footer = (
            f"🧪 第 {chapter_no} 章候选版本（本章字数：{len(clean_content)} 字，原章未替换）\n"
            if candidate
            else f"✅ 第 {chapter_no} 章完成！本章字数：{len(clean_content)} 字\n"
        )
        return (
            f"\n{CHAPTER_SEPARATOR}\n"
            f"【第 {chapter_no}/{total_sections} 章：{section_title}】\n\n"
            f"{clean_content}\n\n"
            f"{CHAPTER_SEPARATOR}\n"
            f"{footer}"
        )

    def _resolve_regeneration_policy(self, section_index: int, section_title: str) -> str:
        """询问用户如何处理重生成结果。"""
        choice = self._run_modal_ui_call(
            messagebox.askyesnocancel,
            "章节重生成",
            (
                f"检测到第 {section_index+1} 章《{section_title}》已存在。\n\n"
                "是：用新版本替换原章节（原位置覆盖）\n"
                "否：保留原章节，并在原位置后追加候选版本\n"
                "取消：保留原章节，丢弃这次新版本"
            ),
        )
        if choice is True:
            return "replace"
        if choice is False:
            return "keep_both"
        return "discard"

    def _apply_generated_section_output(
        self,
        *,
        base_output_text: str,
        section_index: int,
        total_sections: int,
        section_title: str,
        section_content: str,
        existing_chapter_policy: str = "ask",
    ) -> tuple[str, str]:
        """合并本次章节到最终输出，支持原位替换/候选保留/丢弃。"""
        chapter_no = section_index + 1
        official_block = self._build_chapter_block_text(
            section_index=section_index,
            total_sections=total_sections,
            section_title=section_title,
            section_content=section_content,
            candidate=False,
        )
        chapter_spans = self._iter_chapter_spans(base_output_text)
        chapter_blocks = [b for b in chapter_spans if int(b["chapter"]) == chapter_no]

        if not chapter_blocks:
            return "append", f"{base_output_text.rstrip()}{official_block}\n"

        policy = (existing_chapter_policy or "ask").strip().lower()
        if policy not in {"replace", "keep_both", "discard"}:
            policy = self._resolve_regeneration_policy(section_index, section_title)

        if policy == "discard":
            return "discard", base_output_text

        if policy == "keep_both":
            candidate_block = self._build_chapter_block_text(
                section_index=section_index,
                total_sections=total_sections,
                section_title=section_title,
                section_content=section_content,
                candidate=True,
            )
            insert_at = int(chapter_blocks[-1]["end"])
            merged = f"{base_output_text[:insert_at]}{candidate_block}{base_output_text[insert_at:]}"
            return "keep_both", merged

        first_start = int(chapter_blocks[0]["start"])
        slices: list[str] = []
        cursor = 0
        for block in chapter_blocks:
            start = int(block["start"])
            end = int(block["end"])
            slices.append(base_output_text[cursor:start])
            cursor = end
        slices.append(base_output_text[cursor:])
        base_without_chapter = "".join(slices)
        merged = f"{base_without_chapter[:first_start]}{official_block}{base_without_chapter[first_start:]}"
        return "replace", merged

    def _rebuild_generated_content_from_output(self, text: str) -> str:
        """从输出中回推章节正文，按章节号拼接（同章取最新完成版）。"""
        blocks = self._iter_completed_chapter_blocks(text)
        if not blocks:
            return ""

        latest_by_chapter: dict[int, str] = {}
        for block in blocks:
            latest_by_chapter[int(block["chapter"])] = str(block["body"])

        return "\n\n".join(
            (latest_by_chapter.get(chapter_no, "").strip())
            for chapter_no in sorted(latest_by_chapter.keys())
            if latest_by_chapter.get(chapter_no, "").strip()
        )

    def _report_section_generation_error(
        self,
        section_index: int,
        error: Exception,
        *,
        prefix: str = "生成出错",
    ) -> None:
        """统一错误提示：不把 traceback 写入正文区。"""
        chapter_no = max(1, int(section_index) + 1)
        brief = _sanitize(str(error)) or error.__class__.__name__
        self._ui(self.output.insert, END, f"\n❌ {prefix}（第 {chapter_no} 章）：{brief}\n")
        self._ui(self.status.set, f"第 {chapter_no} 章生成失败")
        if hasattr(self, "update_header_status"):
            self._ui(self.update_header_status, f"第 {chapter_no} 章生成失败", "❌")
        self._ui(messagebox.showerror, "错误", brief)

    def _start_section_generation_ui(self, *, section_index: int, total_sections: int, section_title: str):
        """刷新章节生成开始时的状态与输出头部。"""
        self._ui(self.status.set, f"生成第 {section_index+1}/{total_sections} 章: {section_title}")
        if hasattr(self, "update_header_status"):
            self._ui(self.update_header_status, f"生成章节 ({section_index+1}/{total_sections})", "📝")
        self._ui(self.output.insert, END, f"\n{'='*50}\n")
        self._ui(self.output.insert, END, f"【第 {section_index+1}/{total_sections} 章：{section_title}】\n\n")
        self._ui(self.output.see, END)
        if hasattr(self, "_ui_get"):
            return self._ui_get(self.output.index, "end-1c")
        return self.output.index("end-1c")

    _STREAM_RETRY_MAX = 2
    _STREAM_RETRY_DELAY = 1.5

    def _stream_section_content(
        self,
        *,
        client,
        story_system_prompt: str,
        section_prompt: str,
        target_per_section: int,
    ) -> str:
        """流式生成单章正文（使用缓冲批量更新 UI，提升 5-10 倍性能）。

        包含连接中断自动重试：如果流式传输中途断开，自动重试最多 _STREAM_RETRY_MAX 次。
        """
        max_tokens = max(1200, min(8192, int(target_per_section * 3.2)))
        messages = [
            {"role": "system", "content": story_system_prompt},
            {"role": "user", "content": section_prompt},
        ]
        last_exc: Exception | None = None

        for attempt in range(self._STREAM_RETRY_MAX):
            section_content = ""
            buffer_text = ""
            last_flush = time.time()

            def flush_buffer(force: bool = False) -> None:
                nonlocal buffer_text, last_flush
                now = time.time()
                elapsed = now - last_flush
                should_flush = (
                    force
                    or len(buffer_text) >= self.STREAM_BUFFER_SIZE
                    or elapsed >= self.STREAM_FLUSH_INTERVAL
                )
                if should_flush and buffer_text:
                    text_to_insert = buffer_text
                    buffer_text = ""
                    last_flush = now
                    def _update():
                        self.output.insert(END, text_to_insert)
                        self.output.see(END)
                    self._ui(_update)

            try:
                for delta in client.stream(
                    messages,
                    temperature=self.temperature.get(),
                    max_tokens=max_tokens,
                ):
                    section_content += delta
                    buffer_text += delta
                    flush_buffer(force=False)

                flush_buffer(force=True)
                return section_content
            except Exception as exc:
                last_exc = exc
                err_text = str(exc).lower()
                _RETRY_MARKERS = (
                    "incomplete chunked read", "chunked", "peer closed",
                    "connection reset", "connection error", "connection aborted",
                    "timed out", "timeout", "broken pipe", "econnreset",
                    "temporarily unavailable", "remote protocol",
                )
                if not any(m in err_text for m in _RETRY_MARKERS):
                    raise

                # 连接中断：如果已拿到足够内容（>=60%目标），直接使用
                if section_content and len(section_content) >= target_per_section * 0.6:
                    logger.warning("stream interrupted at %d chars (>60%% target), using partial content",
                                   len(section_content))
                    flush_buffer(force=True)
                    return section_content

                if attempt < self._STREAM_RETRY_MAX - 1:
                    retry_msg = f"流式传输中断，{self._STREAM_RETRY_DELAY}s 后自动重试（{attempt+1}/{self._STREAM_RETRY_MAX-1}）..."
                    logger.warning("stream interrupted: %s, retrying...", str(exc)[:80])
                    try:
                        self._ui(self.status.set, retry_msg)
                    except Exception:
                        pass
                    time.sleep(self._STREAM_RETRY_DELAY)
                    # 清除之前的半截内容
                    if section_content:
                        try:
                            self._ui(self.output.delete, "end-%dc" % (len(section_content) + 1), "end-1c")
                        except Exception:
                            pass

        raise last_exc  # type: ignore[misc]
    
    
    def _auto_generate_all_sections(self, query, contexts, start_index=0):
        """自动生成所有章节（无知识库）"""
        def task():
            try:
                self._ui(self.set_busy, True)
                
                api_config = self._resolve_generation_api_config_safe("story_generate")
                api_key = _sanitize(api_config.get("key", ""))
                if not api_key:
                    self._ui(messagebox.showwarning, "提示", f"API Key 为空，请在'基础 API 配置'中为 {api_config.get('provider', '')} 填写后保存")
                    return
                
                print(f"🤖 使用模型: {api_config.get('model', '')}")
                client = self._create_generation_client(api_config)
                
                total_sections = len(self.parsed_sections)
                current_idx = start_index

                _PER_CHAPTER_RETRY_MAX = 2
                _PER_CHAPTER_RETRY_DELAY = 2.0

                for idx in range(start_index, total_sections):
                    current_idx = idx
                    self._ui(self.section_selector.current, idx)
                    
                    # 单章重试机制：连接中断时自动重试，不中断整条流水线
                    chapter_ok = False
                    for ch_attempt in range(_PER_CHAPTER_RETRY_MAX):
                        try:
                            result = self._do_generate_section(
                                client, query, contexts, idx,
                                existing_chapter_policy="replace",
                                skip_dialog=True,
                            )
                            if result == "preview_discard":
                                self._ui(self.output.insert, END, "\n⏹️ 已在预览阶段取消，自动生成已停止。\n")
                                self._ui(self.output.see, END)
                                self._ui(self.status.set, "自动生成已停止（预览取消）")
                                if hasattr(self, 'update_header_status'):
                                    self._ui(self.update_header_status, "自动生成已停止", "⏹️")
                                return
                            chapter_ok = True
                            break
                        except Exception as ch_exc:
                            err_lower = str(ch_exc).lower()
                            _CONN_MARKERS = (
                                "incomplete chunked", "chunked", "peer closed",
                                "connection reset", "connection error", "timed out",
                                "timeout", "broken pipe", "econnreset",
                            )
                            is_conn_err = any(m in err_lower for m in _CONN_MARKERS)
                            if not is_conn_err or ch_attempt >= _PER_CHAPTER_RETRY_MAX - 1:
                                raise
                            logger.warning("chapter %d failed (attempt %d): %s, retrying...",
                                           idx + 1, ch_attempt + 1, str(ch_exc)[:80])
                            self._ui(self.output.insert, END,
                                     f"\n⚠️ 第 {idx+1} 章生成中断，{_PER_CHAPTER_RETRY_DELAY}s 后自动重试...\n\n")
                            self._ui(self.output.see, END)
                            self._ui(self.status.set,
                                     f"第 {idx+1} 章连接中断，自动重试中（{ch_attempt+1}/{_PER_CHAPTER_RETRY_MAX-1}）...")
                            time.sleep(_PER_CHAPTER_RETRY_DELAY)

                    if not chapter_ok:
                        continue

                    if idx < total_sections - 1:
                        self._ui(self.output.insert, END, f"\n\n⏳ 准备生成下一章...\n\n")
                        self._ui(self.output.see, END)
                
                # 全部完成
                total_chars = len(self.generated_content)
                self._ui(self.output.insert, END, f"\n\n{'='*50}\n")
                self._ui(self.output.insert, END, f"🎉 全部章节生成完成！共 {total_sections} 章，总字数：{total_chars} 字\n")
                self._ui(self.output.see, END)
                self._ui(self.status.set, f"全部完成（{total_chars} 字）")
                if hasattr(self, 'update_header_status'):
                    self._ui(self.update_header_status, "全部章节完成", "✅")
                self._auto_save_to_project()
                # 弹窗放在 try 外，超时不影响结果
                try:
                    self._ui(messagebox.showinfo, "完成", f"所有章节已生成完成！\n\n共 {total_sections} 章，总字数：{total_chars} 字")
                except Exception:
                    pass
            except Exception as e:
                self._report_section_generation_error(current_idx, e, prefix="自动生成出错")
                # 更新顶部状态栏
                if hasattr(self, 'update_header_status'):
                    self._ui(self.update_header_status, "自动生成失败", "❌")
            finally:
                self._ui(self.set_busy, False)
        threading.Thread(target=task, daemon=True).start()
    
    

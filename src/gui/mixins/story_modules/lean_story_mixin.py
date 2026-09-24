"""Lean two-call chapter generation pipeline."""

from __future__ import annotations

import json
import logging
import re
import threading
from tkinter import END, messagebox
from typing import Any

from src.utils.text import sanitize as _sanitize

logger = logging.getLogger(__name__)


class LeanStoryMixin:
    """Generate chapters directly, then update a compact story state."""

    CHAPTER_SEPARATOR = "=" * 50
    CHAPTER_HEADER_RE = re.compile(
        r"(?:\n|^)(?P<sep>={20,})\n"
        r"【第\s*(?P<chapter>\d+)\s*/\s*(?P<total>\d+)\s*章："
        r"(?P<title>[^\n】]+)】\n\n",
        re.S,
    )
    COMPLETED_CHAPTER_BLOCK_RE = re.compile(
        r"(?P<block>\n?={20,}\n"
        r"【第\s*(?P<chapter>\d+)\s*/\s*(?P<total>\d+)\s*章："
        r"(?P<title>[^\n】]+)】\n\n"
        r"(?P<body>.*?)\n\n={20,}\n"
        r"✅ 第\s*(?P=chapter)\s*章完成！本章字数："
        r"(?P<chars>\d+)\s*字\n)",
        re.S,
    )

    def _try_begin_auto_generation(self) -> bool:
        lock = getattr(self, "_auto_generation_lock", None)
        if lock is None:
            lock = threading.Lock()
            self._auto_generation_lock = lock
        with lock:
            if getattr(self, "_auto_generation_active", False):
                return False
            self._auto_generation_active = True
            return True

    def _end_auto_generation(self) -> None:
        lock = getattr(self, "_auto_generation_lock", None)
        if lock is None:
            self._auto_generation_active = False
            return
        with lock:
            self._auto_generation_active = False

    def _auto_generate_all_sections(
        self,
        query,
        contexts,
        start_index=0,
        context_provider=None,
        _generation_claimed=False,
    ):
        """Run the lean chapter loop in a background thread."""
        if not _generation_claimed and not self._try_begin_auto_generation():
            self._ui(self.status.set, "自动生成已在进行中")
            return False

        def task():
            try:
                self._ui(self.set_busy, True)
                self._generate_all_chapters_lean(
                    query=query,
                    start_index=start_index,
                    total_sections=len(self.parsed_sections),
                )
            except Exception as exc:
                self._report_section_generation_error(
                    start_index,
                    exc,
                    prefix="自动生成出错",
                )
            finally:
                self._end_auto_generation()
                self._ui(self.set_busy, False)

        threading.Thread(target=task, daemon=True).start()
        return True

    def _generate_all_chapters_lean(
        self,
        *,
        query: str,
        start_index: int,
        total_sections: int,
    ) -> None:
        api_config = self._resolve_generation_api_config_safe("story_generate")
        if not _sanitize(api_config.get("key", "")):
            provider = api_config.get("provider", "")
            raise RuntimeError(f"API Key 为空：{provider}")

        client = self._create_generation_client(api_config)
        state = self._get_lean_story_state()
        self.generated_content = self._rebuild_generated_content_from_output(
            self._get_output_text_snapshot()
        )

        for index in range(start_index, total_sections):
            section = self.parsed_sections[index]
            title = str(section.get("title", "") or f"第{index + 1}章")
            target_chars = self._lean_target_chars(total_sections)
            self._ui(self.section_selector.current, index)
            self._ui(
                self.status.set,
                f"精简生成第 {index + 1}/{total_sections} 章：{title}",
            )
            if hasattr(self, "update_header_status"):
                self._ui(
                    self.update_header_status,
                    f"生成章节 ({index + 1}/{total_sections})",
                    "📝",
                )

            prompt = self._build_lean_chapter_prompt(
                query=query,
                section=section,
                section_index=index,
                total_sections=total_sections,
                target_chars=target_chars,
                state=state,
            )
            chapter_text = self._call_lean_text(
                client,
                prompt,
                max_tokens=max(1200, int(target_chars * 2.2)),
                temperature=0.72,
            )
            if not chapter_text.strip():
                raise RuntimeError(f"第 {index + 1} 章返回为空")

            base_output = self._get_output_text_snapshot()
            action, final_output = self._apply_generated_section_output(
                base_output_text=base_output,
                section_index=index,
                total_sections=total_sections,
                section_title=title,
                section_content=chapter_text,
                existing_chapter_policy="replace",
            )
            if action in {"append", "replace"}:
                self._overwrite_output_text(final_output)
                self.generated_content = self._rebuild_generated_content_from_output(
                    final_output
                )
                state = self._update_lean_story_state(
                    client=client,
                    chapter_index=index,
                    chapter_title=title,
                    chapter_text=chapter_text,
                    state=state,
                )
                self.lean_story_state = state
                self._auto_save_to_project()
                self._ui(self.status.set, f"第 {index + 1} 章完成")
            else:
                self._ui(self.status.set, f"第 {index + 1} 章未入稿")

        total_chars = len(self.generated_content)
        self._ui(self.status.set, f"全部完成（{total_chars} 字）")
        if hasattr(self, "update_header_status"):
            self._ui(self.update_header_status, "全部章节完成", "✅")

    def _get_lean_story_state(self) -> dict[str, Any]:
        state = getattr(self, "lean_story_state", None)
        if isinstance(state, dict):
            return state
        return {
            "summary": "",
            "facts": [],
            "open_hooks": [],
            "characters": [],
            "last_tail": "",
        }

    def _lean_target_chars(self, total_sections: int) -> int:
        try:
            target = int(self.target_chars.get())
        except Exception:
            target = 1800
        return max(500, int(target / max(1, total_sections)))

    def _build_lean_chapter_prompt(
        self,
        *,
        query: str,
        section: dict,
        section_index: int,
        total_sections: int,
        target_chars: int,
        state: dict[str, Any],
    ) -> str:
        title = str(section.get("title", "") or f"第{section_index + 1}章")
        last_tail = str(state.get("last_tail", "") or "").strip()
        if not last_tail and self.generated_content:
            last_tail = self.generated_content[-1200:]
        state_for_prompt = {
            "summary": str(state.get("summary", "") or ""),
            "facts": list(state.get("facts", []) or [])[-12:],
            "open_hooks": list(state.get("open_hooks", []) or [])[-8:],
            "characters": list(state.get("characters", []) or [])[-12:],
        }
        position = (
            "开篇章，需要快速建立人物、冲突和悬念"
            if section_index == 0
            else (
                "结局章，需要收束主要冲突和伏笔"
                if section_index == total_sections - 1
                else f"第 {section_index + 1}/{total_sections} 章"
            )
        )
        return (
            "你是中文小说作者。只写本章正文，不要标题、目录、解释或 Markdown。\n\n"
            f"创作需求：{query}\n"
            f"本章定位：{position}\n"
            f"章节标题：{title}\n"
            f"目标字数：{target_chars} 字左右\n\n"
            "【当前故事状态】\n"
            f"{json.dumps(state_for_prompt, ensure_ascii=False, indent=2)}\n\n"
            "【上一章结尾】\n"
            f"{last_tail or '无，本章建立开场。'}\n\n"
            "写作要求：\n"
            "1. 第一段直接进入场景或冲突，不解释背景。\n"
            "2. 必须与上一章结尾自然衔接，不重复已经发生的事件。\n"
            "3. 本章包含一个明确目标、一个阻力、一次选择及可见后果。\n"
            "4. 结尾留下一个具体的新问题或未完成动作。\n"
            "5. 人物称谓、关系、已发生事实必须与故事状态一致。\n"
            "6. 用自然叙事完成，不要使用“首先/其次/最后”等模板腔。\n"
        )

    def _call_lean_text(
        self,
        client,
        prompt: str,
        *,
        max_tokens: int,
        temperature: float,
    ) -> str:
        messages = [
            {
                "role": "system",
                "content": "你是中文小说作者。直接输出章节正文。",
            },
            {"role": "user", "content": prompt},
        ]
        return str(
            client.chat(
                messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            or ""
        ).strip()

    def _update_lean_story_state(
        self,
        *,
        client,
        chapter_index: int,
        chapter_title: str,
        chapter_text: str,
        state: dict[str, Any],
    ) -> dict[str, Any]:
        prompt = (
            "你是小说连续性编辑。只输出 JSON，不要 Markdown。\n"
            "根据刚完成的章节更新故事状态。JSON 格式：\n"
            "{\n"
            '  "summary": "全书当前故事摘要，120字以内",\n'
            '  "facts": ["已经发生且后续不能改写的事实"],\n'
            '  "open_hooks": ["尚未解决的问题或威胁"],\n'
            '  "characters": ["人物名：当前状态、关系或目标"],\n'
            '  "last_tail": "本章最后两段的原文摘录"\n'
            "}\n\n"
            f"章节：第{chapter_index + 1}章 {chapter_title}\n"
            "既有状态：\n"
            f"{json.dumps(state, ensure_ascii=False)}\n\n"
            "本章正文：\n"
            f"{chapter_text}\n"
        )
        raw = self._call_lean_text(
            client,
            prompt,
            max_tokens=700,
            temperature=0.1,
        )
        parsed = self._parse_lean_state(raw)
        if parsed is None:
            logger.warning("lean state update returned invalid JSON; using fallback")
            parsed = {
                "summary": str(state.get("summary", "") or ""),
                "facts": list(state.get("facts", []) or []),
                "open_hooks": list(state.get("open_hooks", []) or []),
                "characters": list(state.get("characters", []) or []),
            }
        parsed["last_tail"] = chapter_text[-1200:].strip()
        parsed["facts"] = [str(item).strip() for item in parsed.get("facts", []) if str(item).strip()][-20:]
        parsed["open_hooks"] = [
            str(item).strip()
            for item in parsed.get("open_hooks", [])
            if str(item).strip()
        ][-12:]
        parsed["characters"] = [
            str(item).strip()
            for item in parsed.get("characters", [])
            if str(item).strip()
        ][-20:]
        return parsed

    @staticmethod
    def _parse_lean_state(raw: str) -> dict[str, Any] | None:
        text = str(raw or "").strip()
        if text.startswith("```"):
            text = re.sub(r"^```(?:json)?\s*", "", text)
            text = re.sub(r"\s*```$", "", text)
        try:
            parsed = json.loads(text)
        except (TypeError, ValueError):
            match = re.search(r"\{[\s\S]*\}", text)
            if not match:
                return None
            try:
                parsed = json.loads(match.group())
            except (TypeError, ValueError):
                return None
        return parsed if isinstance(parsed, dict) else None

    def _get_output_text_snapshot(self) -> str:
        try:
            return str(self._ui_get(self.output.get, "1.0", END) or "")
        except Exception:
            return ""

    def _overwrite_output_text(self, text: str) -> None:
        self._ui(self.output.delete, "1.0", END)
        if text:
            self._ui(self.output.insert, "1.0", text)
        self._ui(self.output.see, END)

    def _iter_completed_chapter_blocks(self, text: str) -> list[dict[str, object]]:
        blocks: list[dict[str, object]] = []
        for match in self.COMPLETED_CHAPTER_BLOCK_RE.finditer(text or ""):
            blocks.append({
                "chapter": int(match.group("chapter")),
                "total": int(match.group("total")),
                "title": str(match.group("title")).strip(),
                "start": match.start("block"),
                "end": match.end("block"),
                "body": str(match.group("body")).rstrip(),
                "block": match.group("block"),
            })
        return blocks

    def _iter_chapter_spans(self, text: str) -> list[dict[str, object]]:
        raw_text = text or ""
        headers = list(self.CHAPTER_HEADER_RE.finditer(raw_text))
        spans: list[dict[str, object]] = []
        for index, header in enumerate(headers):
            start = header.start()
            end = (
                headers[index + 1].start()
                if index + 1 < len(headers)
                else len(raw_text)
            )
            chapter_no = int(header.group("chapter"))
            block_text = raw_text[start:end]
            spans.append({
                "chapter": chapter_no,
                "total": int(header.group("total")),
                "title": str(header.group("title")).strip(),
                "start": start,
                "end": end,
                "block": block_text,
                "completed": bool(
                    re.search(
                        rf"✅\s*第\s*{chapter_no}\s*章完成",
                        block_text,
                    )
                ),
                "candidate": False,
            })
        return spans

    def _build_chapter_block_text(
        self,
        *,
        section_index: int,
        total_sections: int,
        section_title: str,
        section_content: str,
    ) -> str:
        chapter_no = section_index + 1
        clean_content = (section_content or "").rstrip()
        return (
            f"\n{self.CHAPTER_SEPARATOR}\n"
            f"【第 {chapter_no}/{total_sections} 章：{section_title}】\n\n"
            f"{clean_content}\n\n"
            f"{self.CHAPTER_SEPARATOR}\n"
            f"✅ 第 {chapter_no} 章完成！本章字数：{len(clean_content)} 字\n"
        )

    def _apply_generated_section_output(
        self,
        *,
        base_output_text: str,
        section_index: int,
        total_sections: int,
        section_title: str,
        section_content: str,
        existing_chapter_policy: str = "replace",
    ) -> tuple[str, str]:
        chapter_no = section_index + 1
        official_block = self._build_chapter_block_text(
            section_index=section_index,
            total_sections=total_sections,
            section_title=section_title,
            section_content=section_content,
        )
        chapter_blocks = [
            block
            for block in self._iter_chapter_spans(base_output_text)
            if int(block["chapter"]) == chapter_no
        ]
        if not chapter_blocks:
            return "append", f"{base_output_text.rstrip()}{official_block}\n"
        if existing_chapter_policy == "discard":
            return "discard", base_output_text

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
        merged = (
            f"{base_without_chapter[:first_start]}"
            f"{official_block}"
            f"{base_without_chapter[first_start:]}"
        )
        return "replace", merged

    def _rebuild_generated_content_from_output(self, text: str) -> str:
        blocks = self._iter_completed_chapter_blocks(text)
        if not blocks:
            return ""
        latest_by_chapter: dict[int, str] = {}
        for block in blocks:
            latest_by_chapter[int(block["chapter"])] = str(block["body"])
        return "\n\n".join(
            latest_by_chapter[chapter_no].strip()
            for chapter_no in sorted(latest_by_chapter)
            if latest_by_chapter[chapter_no].strip()
        )

    def _report_section_generation_error(
        self,
        section_index: int,
        error: Exception,
        *,
        prefix: str = "生成出错",
    ) -> None:
        chapter_no = max(1, int(section_index) + 1)
        brief = _sanitize(str(error)) or error.__class__.__name__
        self._ui(
            self.output.insert,
            END,
            f"\n❌ {prefix}（第 {chapter_no} 章）：{brief}\n",
        )
        self._ui(self.status.set, f"第 {chapter_no} 章生成失败")
        self._ui(messagebox.showerror, "错误", brief)

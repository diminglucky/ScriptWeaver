"""Parsed-outline utility helpers for story UI."""

from __future__ import annotations

import re
from tkinter import DISABLED, NORMAL

from src.gui.helpers.story_writing_guardrails import normalize_chapter_title


class OutlineSectionUtilsMixin:
    """Utilities for section selector and outline parsing."""

    def _ensure_simple_story_plan(self, requirement: str) -> bool:
        """Create an internal lean chapter plan without an outline API call."""
        if self.parsed_sections:
            return True

        try:
            target_chars = int(self.target_chars.get())
        except Exception:
            target_chars = 1800
        target_chars = max(500, min(30000, target_chars))
        chapter_count = max(1, min(12, round(target_chars / 1800)))
        if chapter_count == 1:
            stages = ["完整故事"]
        else:
            stages = []
            for index in range(chapter_count):
                progress = index / max(1, chapter_count - 1)
                if index == 0:
                    stages.append("异常开场")
                elif index == chapter_count - 1:
                    stages.append("代价与收束")
                elif progress < 0.35:
                    stages.append("冲突升级")
                elif progress < 0.7:
                    stages.append("反转与失控")
                else:
                    stages.append("最坏处境")

        sections: list[dict[str, str]] = []
        for index, stage in enumerate(stages):
            chapter_no = index + 1
            event_promise = (
                "本章必须发生一次改变后续选择空间的不可逆事件，"
                "并留下下一章必须处理的直接后果。"
            )
            sections.append({
                "title": f"第{chapter_no}章 {stage}",
                "items": [
                    f"围绕创作需求推进：{str(requirement or '').strip()[:120]}",
                    "延续上一章实际结尾，不重复已经发生的事件。",
                    "本章至少完成一次目标、阻力、行动、结果和新问题闭环。",
                ],
                "event_promise": event_promise,
            })

        self.parsed_sections = sections
        self.current_outline = "\n".join(
            f"{index + 1}. {section['title']} | {section['event_promise']}"
            for index, section in enumerate(sections)
        )
        self.chapter_blueprints = []
        self._chapter_blueprints_outline_sig = ""
        self._update_section_selector()
        return bool(self.parsed_sections)

    def _update_section_selector(self) -> None:
        """更新章节选择器"""
        if not self.parsed_sections:
            self.section_selector['values'] = ["请先生成目录"]
            self.btn_generate_section.config(state=DISABLED)
            self.btn_continue_next.config(state=DISABLED)
            return
        
        # 构建章节选项列表
        section_options = []
        for idx, section in enumerate(self.parsed_sections):
            title = section['title']
            section_options.append(f"{idx+1}. {title}")
        
        self.section_selector['values'] = section_options
        self.section_selector.current(0)  # 默认选中第一章
        self.btn_generate_section.config(state=NORMAL)
        self.btn_continue_next.config(state=NORMAL)
        
        # 重置生成内容
        self.generated_content = ""
        
        self.status.set(f"已解析 {len(self.parsed_sections)} 个章节，可开始逐章生成")
        if hasattr(self, "_update_story_diagnostics_panel"):
            try:
                self._update_story_diagnostics_panel()
            except Exception:
                pass
    
    
    def _parse_outline_sections(self, outline: str) -> list[dict[str, str]]:
        """解析目录，提取章节信息"""
        if not outline:
            return []

        sections: list[dict[str, str]] = []
        lines = outline.strip().splitlines()
        current_section = None
        current_items: list[str] = []

        for line in lines:
            stripped = line.strip()
            if not stripped:
                continue

            # 检测是否为章节标题（数字编号、中文编号、或 -, *, •）
            is_main_section = False
            if re.match(r'^\d+[.、]', stripped) or re.match(r'^[一二三四五六七八九十]+[.、]', stripped):
                is_main_section = True
            elif stripped[:1] in ("-", "•", "*") and not stripped[1:2].isdigit():
                # 一级标题
                is_main_section = True

            if is_main_section:
                # 保存上一个章节
                if current_section:
                    sections.append({
                        "title": current_section,
                        "items": current_items.copy()
                    })
                # 去掉编号前缀，避免重复显示
                title = stripped
                title = re.sub(r'^\d+[.、]\s*', '', title)
                title = re.sub(r'^[一二三四五六七八九十]+[.、]\s*', '', title)
                title = re.sub(r'^[-•*]\s*', '', title)
                # Keep the compact title for the selector, but preserve a
                # pipe-delimited chapter brief as prompt material.
                title_parts = re.split(r'\s*[|｜]\s*', title, maxsplit=1)
                current_section = normalize_chapter_title(title_parts[0].strip())
                current_items = [title_parts[1].strip()] if len(title_parts) > 1 and title_parts[1].strip() else []
            else:
                # 子项
                if current_section:
                    current_items.append(stripped)

        # 添加最后一个章节
        if current_section:
            sections.append({
                "title": current_section,
                "items": current_items
            })

        return sections


    

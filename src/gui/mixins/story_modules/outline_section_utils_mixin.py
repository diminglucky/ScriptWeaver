"""Parsed-outline utility helpers for story UI."""

from __future__ import annotations

import re
from tkinter import DISABLED, NORMAL

from src.gui.helpers.story_writing_guardrails import normalize_chapter_title


class OutlineSectionUtilsMixin:
    """Utilities for section selector and outline parsing."""
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
                current_section = normalize_chapter_title(title.strip())
                current_items = []
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


    

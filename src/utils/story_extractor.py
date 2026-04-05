"""
Story content extractor helpers.
"""

from __future__ import annotations

import re
from typing import Optional


class StoryExtractor:
    """Extract pure story body from mixed runtime output logs."""

    _CANDIDATE_CHAPTER_BLOCK = re.compile(
        r"\n?={20,}\n【第\s*\d+\s*/\s*\d+\s*章：[^\n】]+】\n\n.*?\n\n={20,}\n🧪\s*第\s*\d+\s*章候选版本[^\n]*\n?",
        re.S,
    )
    _RAG_SCORE_LINE = re.compile(
        r"^\s*\d+[\.、]\s*.+[（(]\s*score\s*=\s*\d+(?:\.\d+)?\s*[）)]\s*$",
        re.IGNORECASE,
    )
    _EMAIL_PATTERN = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")

    @staticmethod
    def _strip_non_publish_blocks(text: str) -> str:
        cleaned = StoryExtractor._CANDIDATE_CHAPTER_BLOCK.sub("\n", text or "")
        return cleaned

    @staticmethod
    def _is_traceback_stack_line(raw_line: str, stripped: str) -> bool:
        if not stripped:
            return True
        if raw_line.startswith((" ", "\t")):
            return True
        if stripped.startswith(("File \"", "^")):
            return True
        if re.match(r"^[A-Za-z_][A-Za-z0-9_]*(Error|Exception)\s*:", stripped):
            return True
        if stripped.startswith(("During handling of the above exception", "The above exception")):
            return True
        return False

    @staticmethod
    def _is_runtime_marker_line(stripped: str) -> bool:
        if not stripped:
            return False

        fixed_prefixes = (
            "🎭 本次模版：",
            "🔎 RAG检索：",
            "🧠 创新引擎",
            "📊 RAG检索：",
            "🧭 题材纠偏：",
            "对齐检查提示：",
            "❌ 生成出错",
            "❌ 自动生成出错",
            "❌ 生成故事失败",
            "❌ 生成目录失败",
            "❌ 自动生成失败",
        )
        if stripped.startswith(fixed_prefixes):
            return True

        if StoryExtractor._RAG_SCORE_LINE.match(stripped):
            return True

        patterns = (
            r"^使用\s+.+(检索素材并生成目录中|生成目录中|生成正文中|准备生成).*$",
            r"^目录生成中[\.。…]*$",
            r"^故事生成中[\.。…]*$",
            r"^正在构建索引[\.。…]*$",
            r"^正在生成第\s*\d+/\d+\s*段.*$",
            r"^正在生成第\s*\d+/\d+\s*章.*$",
            r"^No text-like files found under .+$",
            r"^未找到索引.*$",
            r"^目录对齐不足.*$",
            r"^[🎭🔎📊🧭📝⏳✅❌]+\s*.*(策略|命中|score=|阈值).*$",
            r"^🧪\s*第\s*\d+\s*章候选版本.*$",
            r"^❌\s*(生成|自动生成).*(出错|失败).*$",
        )
        for pattern in patterns:
            if re.match(pattern, stripped, re.IGNORECASE):
                return True
        return False

    @staticmethod
    def extract_pure_story(full_text: str) -> str:
        """
        Remove outline/runtime logs and keep body content only.
        """
        if not full_text or not full_text.strip():
            return ""

        full_text = StoryExtractor._strip_non_publish_blocks(full_text)
        lines = full_text.split("\n")
        story_lines: list[str] = []
        skip_toc = False
        in_story = False
        skipping_traceback = False

        for line in lines:
            stripped = line.strip()

            if stripped.startswith("Traceback (most recent call last):"):
                skipping_traceback = True
                continue
            if skipping_traceback:
                if StoryExtractor._is_traceback_stack_line(line, stripped):
                    continue
                skipping_traceback = False

            if not stripped:
                if in_story:
                    story_lines.append(line)
                continue

            if StoryExtractor._is_runtime_marker_line(stripped):
                continue

            if re.match(r"^目录[：:]*\s*$", stripped, re.IGNORECASE):
                skip_toc = True
                continue

            if skip_toc:
                if re.match(r"^\d+[\.、]\s*.{1,40}$", stripped):
                    continue
                if re.match(r"^第[一二三四五六七八九十百千\d]+[章节篇]\s*.{1,40}$", stripped):
                    continue
                if re.match(r"^[（\(].*共.*[章节篇].*字.*[）\)]$", stripped):
                    continue
                if re.match(r"^[=\-_]{3,}$", stripped):
                    skip_toc = False
                    continue
                if len(stripped) > 50 and not re.match(r"^\d+[\.、]", stripped):
                    skip_toc = False
                    in_story = True

            if re.match(r"^【第\s*\d+/\d+\s*章.*】$", stripped):
                continue

            if re.match(r"^生成.*中[\.。…]*$", stripped):
                continue
            if re.match(r"^[📄📝✍️⏳]*\s*准备.*[\.。…]*$", stripped):
                continue
            if re.match(r"^[✓✔☑️✅]*\s*第\s*\d+\s*章完成[！!]\s*本章字数[：:]\s*\d+\s*字", stripped):
                continue
            if re.match(r"^🧪\s*第\s*\d+\s*章候选版本", stripped):
                continue
            if re.match(r"^[🎉]*\s*全部章节生成完成[！!]\s*共\s*\d+\s*章.*总字数[：:]\s*\d+\s*字", stripped):
                continue

            if not in_story:
                if re.match(r"^目录\s*[（\(].*共.*[章节篇].*字.*[）\)]", stripped):
                    continue
                if re.match(r"^\d+[\.、]\s*.{1,30}$", stripped):
                    continue
                if re.match(r"^第[一二三四五六七八九十百千\d]+[章节篇][\s：:]*.*$", stripped) and len(stripped) < 35:
                    continue
            if re.match(r"^[=\-_]{3,}$", stripped):
                continue
            if re.match(r"^[*#\-=_\s]+$", stripped):
                continue

            in_story = True
            story_lines.append(line)

        result = "\n".join(story_lines).strip()
        result = re.sub(r"\n{3,}", "\n\n", result)
        return result

    @staticmethod
    def sanitize_for_publish(text: str) -> str:
        """Final pass before publishing: remove runtime noise and invalid control chars."""
        pure = StoryExtractor.extract_pure_story(text)
        if not pure:
            return ""

        cleaned_lines: list[str] = []
        for line in pure.split("\n"):
            stripped = line.strip()
            if StoryExtractor._is_runtime_marker_line(stripped):
                continue
            # keep tabs/newlines, drop other control chars that may break editor input
            safe_line = "".join(ch for ch in line if ch in ("\t",) or ord(ch) >= 32)
            safe_line = safe_line.replace("\u200b", "").replace("\ufeff", "")
            cleaned_lines.append(safe_line.rstrip())

        cleaned = "\n".join(cleaned_lines).strip()
        cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
        return cleaned

    @staticmethod
    def sanitize_for_zhihu_publish(text: str) -> str:
        """
        Zhihu-specific sanitize pass.
        Neutralize mention-style `@` to avoid editor mention popups while keeping emails.
        """
        cleaned = StoryExtractor.sanitize_for_publish(text)
        if not cleaned:
            return ""

        protected_emails: list[str] = []

        def _protect_email(match: re.Match[str]) -> str:
            protected_emails.append(match.group(0))
            return f"__EMAIL_TOKEN_{len(protected_emails) - 1}__"

        text_with_tokens = StoryExtractor._EMAIL_PATTERN.sub(_protect_email, cleaned)
        text_with_tokens = text_with_tokens.replace("@", "＠")

        for idx, email in enumerate(protected_emails):
            text_with_tokens = text_with_tokens.replace(f"__EMAIL_TOKEN_{idx}__", email)

        return text_with_tokens

    @staticmethod
    def extract_title_from_story(full_text: str) -> Optional[str]:
        if not full_text or not full_text.strip():
            return None

        lines = full_text.split("\n")
        for line in lines[:10]:
            stripped = line.strip()
            if not stripped or stripped in ["目录", "目录：", "目录:"]:
                continue
            if re.match(r"^\d+[\.、]", stripped):
                continue
            if re.match(r"^【第\s*\d+/\d+\s*章.*】$", stripped):
                continue
            if re.match(r"^第[一二三四五六七八九十百千\d]+[章节篇]", stripped):
                continue
            if re.match(r"^[=\-_]{3,}$", stripped):
                continue
            if 5 < len(stripped) < 50 and not stripped.endswith("。"):
                return stripped
        return None

    @staticmethod
    def get_story_preview(full_text: str, max_length: int = 200) -> str:
        pure_story = StoryExtractor.extract_pure_story(full_text)
        if not pure_story:
            return ""
        if len(pure_story) <= max_length:
            return pure_story

        preview = pure_story[:max_length]
        last_period = preview.rfind("。")
        if last_period > int(max_length * 0.5):
            preview = preview[: last_period + 1]
        else:
            preview += "..."
        return preview

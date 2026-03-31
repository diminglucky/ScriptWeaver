"""
Story content extractor helpers.
"""

from __future__ import annotations

import re
from typing import Optional


class StoryExtractor:
    """Extract pure story body from mixed runtime output logs."""

    @staticmethod
    def extract_pure_story(full_text: str) -> str:
        """
        Remove outline/runtime logs and keep body content only.
        """
        if not full_text or not full_text.strip():
            return ""

        lines = full_text.split("\n")
        story_lines: list[str] = []
        skip_toc = False
        in_story = False

        for line in lines:
            stripped = line.strip()

            if not stripped:
                if in_story:
                    story_lines.append(line)
                continue

            if stripped.startswith("🎭 本次模版："):
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
            if re.match(r"^[🎉]*\s*全部章节生成完成[！!]\s*共\s*\d+\s*章.*总字数[：:]\s*\d+\s*字", stripped):
                continue

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


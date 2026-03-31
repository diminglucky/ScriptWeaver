import re
import unittest

from src.gui.mixins.project_mixin import ProjectMixin


class _Selector:
    def __init__(self):
        self._index = 0

    def current(self, index=None):
        if index is None:
            return self._index
        self._index = int(index)
        return self._index


class _Var:
    def __init__(self, value=0):
        self._value = value

    def get(self):
        return self._value

    def set(self, value):
        self._value = value


class _DummyRestore(ProjectMixin):
    def __init__(self):
        self.current_outline = None
        self.parsed_sections = []
        self.generated_content = ""
        self.section_selector = _Selector()
        self.current_section_index = _Var(0)
        self.selector_update_count = 0

    def _update_section_selector(self):
        self.selector_update_count += 1

    def _parse_outline_sections(self, outline: str):
        sections = []
        for line in outline.splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            title = re.sub(r"^\d+[.、]\s*", "", stripped)
            title = re.sub(r"^[一二三四五六七八九十百千]+[.、]\s*", "", title)
            title = re.sub(r"^[-•*]\s*", "", title)
            title = title.strip()
            if title:
                sections.append({"title": title, "items": []})
        return sections


class ProjectMixinRestoreTests(unittest.TestCase):
    def test_restore_prefers_saved_outline_and_section_index(self):
        obj = _DummyRestore()
        story = (
            "目录（共2章，预估字数≈800字）\n\n"
            "1. 旧标题A\n2. 旧标题B\n\n"
            "==================================================\n"
            "【第 1/2 章：旧标题A】\n\n正文"
        )
        meta = {
            "outline": "1. 新标题A\n2. 新标题B",
            "parsed_sections": [
                {"title": "新标题A", "items": []},
                {"title": "新标题B", "items": ["要点"]},
            ],
            "section_index": 1,
        }

        obj._restore_story_structure_from_project(story, meta)

        self.assertEqual(obj.current_outline, "1. 新标题A\n2. 新标题B")
        self.assertEqual(len(obj.parsed_sections), 2)
        self.assertEqual(obj.parsed_sections[1]["title"], "新标题B")
        self.assertEqual(obj.section_selector.current(), 1)
        self.assertEqual(obj.current_section_index.get(), 1)
        self.assertTrue(obj.generated_content.startswith("【第 1/2 章：旧标题A】"))
        self.assertEqual(obj.selector_update_count, 1)

    def test_restore_falls_back_to_story_text_and_detects_last_chapter(self):
        obj = _DummyRestore()
        story = (
            "🎭 本次模版：知乎现实故事（策略：固定模版）\n\n"
            "生成目录中...\n\n"
            "目录（共3章，预估字数≈1200字）\n\n"
            "1. 开场冲突\n"
            "2. 危机升级\n"
            "3. 最终反转\n\n"
            "==================================================\n"
            "【第 1/3 章：开场冲突】\n\n第一章内容\n\n"
            "==================================================\n"
            "【第 2/3 章：危机升级】\n\n第二章内容"
        )

        obj._restore_story_structure_from_project(story, {})

        self.assertEqual(
            obj.current_outline,
            "1. 开场冲突\n2. 危机升级\n3. 最终反转",
        )
        self.assertEqual([x["title"] for x in obj.parsed_sections], ["开场冲突", "危机升级", "最终反转"])
        self.assertEqual(obj.section_selector.current(), 1)
        self.assertEqual(obj.current_section_index.get(), 1)
        self.assertTrue(obj.generated_content.startswith("【第 1/3 章：开场冲突】"))
        self.assertEqual(obj.selector_update_count, 1)


if __name__ == "__main__":
    unittest.main()

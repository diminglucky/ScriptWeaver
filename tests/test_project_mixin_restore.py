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


class _Text:
    def __init__(self, value=""):
        self.value = value

    def delete(self, start, end):
        self.value = ""


class _DummyRestore(ProjectMixin):
    def __init__(self):
        self.current_outline = None
        self.parsed_sections = []
        self.generated_content = ""
        self.story_memory_ledger = []
        self.chapter_quality_reports = []
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


class _DummyReset(ProjectMixin):
    def __init__(self):
        self.output = _Text("old story")
        self.prompt_text = _Text("old prompt")
        self.category = _Var("悬疑")
        self.style = _Var("情感起伏")
        self.current_outline = "1. old"
        self.parsed_sections = [{"title": "old", "items": []}]
        self.generated_content = "old generated"
        self.story_global_overview_text = "old overview"
        self.story_global_overview_signature = "old sig"
        self.story_memory_ledger = [{"summary": "old"}]
        self.chapter_quality_reports = [{"avg_score": 8}]
        self.chapter_blueprints = [{"blueprint": "old"}]
        self._chapter_blueprints_outline_sig = "old outline sig"
        self.section_selector = _Selector()
        self.current_section_index = _Var(3)
        self.story_quality_summary_var = _Var("质量评审：旧")
        self.story_memory_summary_var = _Var("记忆账本：旧")
        self.selector_update_count = 0
        self.invalidated_blueprints = False

    def _update_section_selector(self):
        self.selector_update_count += 1

    def _invalidate_chapter_blueprints(self):
        self.invalidated_blueprints = True
        self.chapter_blueprints = []
        self._chapter_blueprints_outline_sig = ""


class _ProjectManagerStartupStub:
    def __init__(self, last_project=None, projects=None):
        self._last_project = last_project
        self._projects = projects or []

    def get_last_project(self):
        return self._last_project

    def list_projects(self):
        return list(self._projects)


class _DummyStartup(ProjectMixin):
    def __init__(self, project_manager, load_result=True):
        self.project_manager = project_manager
        self.status = _Var("")
        self.current_project = None
        self.loaded_paths = []
        self.loaded_kwargs = []
        self.load_result = load_result

    def _load_project_by_path(self, project_path, **kwargs):
        self.loaded_paths.append(str(project_path))
        self.loaded_kwargs.append(dict(kwargs))
        self.current_project = type("Project", (), {"metadata": {"name": "自动恢复项目"}})()
        return self.load_result


class ProjectMixinRestoreTests(unittest.TestCase):
    def test_reset_story_workspace_clears_project_scoped_state(self):
        obj = _DummyReset()

        obj._reset_story_workspace_for_project()

        self.assertEqual(obj.output.value, "")
        self.assertEqual(obj.prompt_text.value, "")
        self.assertEqual(obj.category.get(), "")
        self.assertEqual(obj.style.get(), "")
        self.assertIsNone(obj.current_outline)
        self.assertEqual(obj.parsed_sections, [])
        self.assertEqual(obj.generated_content, "")
        self.assertEqual(obj.story_global_overview_text, "")
        self.assertEqual(obj.story_global_overview_signature, "")
        self.assertEqual(obj.story_memory_ledger, [])
        self.assertEqual(obj.chapter_quality_reports, [])
        self.assertTrue(obj.invalidated_blueprints)
        self.assertEqual(obj.chapter_blueprints, [])
        self.assertEqual(obj._chapter_blueprints_outline_sig, "")
        self.assertEqual(obj.current_section_index.get(), 0)
        self.assertEqual(obj.story_quality_summary_var.get(), "质量评审：未开始")
        self.assertEqual(obj.story_memory_summary_var.get(), "记忆账本：暂无章节记忆")
        self.assertEqual(obj.selector_update_count, 1)

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
            "story_global_overview": "【一句话主线】新人与旧案交织，真相在毕业前揭开。",
            "story_global_overview_signature": "sig123",
            "parsed_sections": [
                {"title": "新标题A", "items": []},
                {"title": "新标题B", "items": ["要点"]},
            ],
            "story_memory_ledger": [
                {
                    "chapter_index": 0,
                    "chapter_title": "新标题A",
                    "summary": "第一章摘要",
                    "plot_points": ["事件A"],
                    "relation_changes": ["关系变化A"],
                    "unresolved_hooks": ["伏笔A"],
                    "state_shift": "情绪转折A",
                    "character_states": ["主角：怀疑同桌/知道匿名信存在/手受伤/不能报警"],
                    "timeline_events": ["晚自习后在走廊收到匿名信"],
                    "open_threads": ["匿名信来源未确认"],
                }
            ],
            "chapter_quality_reports": [
                {
                    "chapter_index": 0,
                    "chapter_title": "新标题A",
                    "avg_score": 7.6,
                    "scores": {"realism": 7.5},
                    "issues": ["细节不足"],
                    "key_fix": "补细节",
                }
            ],
            "section_index": 1,
        }

        obj._restore_story_structure_from_project(story, meta)

        self.assertEqual(obj.current_outline, "1. 新标题A\n2. 新标题B")
        self.assertEqual(obj.story_global_overview_text, "【一句话主线】新人与旧案交织，真相在毕业前揭开。")
        self.assertEqual(obj.story_global_overview_signature, "sig123")
        self.assertEqual(len(obj.parsed_sections), 2)
        self.assertEqual(obj.parsed_sections[1]["title"], "新标题B")
        self.assertEqual(obj.section_selector.current(), 1)
        self.assertEqual(obj.current_section_index.get(), 1)
        self.assertTrue(obj.generated_content.startswith("【第 1/2 章：旧标题A】"))
        self.assertEqual(len(obj.story_memory_ledger), 1)
        self.assertEqual(obj.story_memory_ledger[0]["summary"], "第一章摘要")
        self.assertEqual(obj.story_memory_ledger[0]["character_states"][0], "主角：怀疑同桌/知道匿名信存在/手受伤/不能报警")
        self.assertEqual(obj.story_memory_ledger[0]["timeline_events"][0], "晚自习后在走廊收到匿名信")
        self.assertEqual(obj.story_memory_ledger[0]["open_threads"][0], "匿名信来源未确认")
        self.assertEqual(len(obj.chapter_quality_reports), 1)
        self.assertEqual(obj.chapter_quality_reports[0]["key_fix"], "补细节")
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

    def test_auto_restore_prefers_last_project_marker(self):
        manager = _ProjectManagerStartupStub(
            last_project="/tmp/marker_project",
            projects=[{"path": "/tmp/latest_project"}],
        )
        obj = _DummyStartup(manager)

        obj._auto_restore_last_project_on_startup()

        self.assertEqual(obj.loaded_paths, ["/tmp/marker_project"])
        self.assertEqual(
            obj.loaded_kwargs,
            [
                {
                    "show_popup": False,
                    "switch_to_story": False,
                    "remember_last": False,
                    "select_in_tree": True,
                }
            ],
        )
        self.assertEqual(obj.status.get(), "已自动恢复项目: 自动恢复项目")

    def test_auto_restore_falls_back_to_latest_project(self):
        manager = _ProjectManagerStartupStub(
            last_project=None,
            projects=[
                {"path": "/tmp/latest_project"},
                {"path": "/tmp/older_project"},
            ],
        )
        obj = _DummyStartup(manager)

        obj._auto_restore_last_project_on_startup()

        self.assertEqual(obj.loaded_paths, ["/tmp/latest_project"])
        self.assertEqual(obj.status.get(), "已自动恢复项目: 自动恢复项目")

    def test_auto_restore_skips_when_no_project_available(self):
        manager = _ProjectManagerStartupStub(last_project=None, projects=[])
        obj = _DummyStartup(manager)

        obj._auto_restore_last_project_on_startup()

        self.assertEqual(obj.loaded_paths, [])
        self.assertEqual(obj.status.get(), "")


if __name__ == "__main__":
    unittest.main()

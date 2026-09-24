from __future__ import annotations

from src.gui.helpers.story_output import build_story_from_chapters, clean_story_text
from src.gui.mixins.project_mixin import ProjectMixin


class _Output:
    def __init__(self, text: str):
        self.text = text

    def get(self, *_args):
        return self.text


class _SaveHarness(ProjectMixin):
    def __init__(self, output: str, generated: str):
        self.output = _Output(output)
        self.generated_content = generated


def test_clean_story_text_removes_runtime_noise_and_wrappers():
    raw = (
        "🎭 本次模版：知乎现实故事\n\n"
        "我会先调整结构，下面是正文：\n"
        "```text\n"
        "# 第一章\n"
        "她在凌晨收到一条不该存在的短信。\n"
        "\n"
        "✅ 生成完成！总字数：20 字\n"
        "```\n"
    )

    assert clean_story_text(raw) == "她在凌晨收到一条不该存在的短信。"


def test_build_story_from_chapters_keeps_latest_publishable_chapter_shape():
    result = build_story_from_chapters(
        [
            {"chapter": 1, "title": "门后的回声", "body": "第一段。\n\n⏳ 准备生成下一章"},
            {"chapter": 2, "title": "不在场的人", "body": "第二段。"},
        ]
    )

    assert "⏳" not in result
    assert result.startswith("【第 1 章：门后的回声】")
    assert "【第 2 章：不在场的人】" in result


def test_save_prefers_canonical_snapshot_for_section_scaffold():
    result = _SaveHarness(
        "🎭 本次模版：悬疑\n目录（共2章）\n==================================================\n日志",
        "第一章正文\n\n第二章正文",
    )._story_text_for_save()

    assert result == "第一章正文\n\n第二章正文"

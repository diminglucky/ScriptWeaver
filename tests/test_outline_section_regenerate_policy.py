from __future__ import annotations

from unittest.mock import patch

from src.gui.mixins.story_modules.outline_section_generate_mixin import OutlineSectionGenerateMixin


class _Var:
    def __init__(self, value):
        self._value = value

    def get(self):
        return self._value

    def set(self, value):
        self._value = value


class _Output:
    def __init__(self):
        self.text = ""

    def insert(self, *_args):
        self.text += str(_args[-1]) if _args else ""

    def delete(self, *_args):
        self.text = ""

    def get(self, *_args):
        return self.text

    def see(self, *_args):
        return None


class _DummyApp(OutlineSectionGenerateMixin):
    def __init__(self):
        self.output = _Output()
        self.status = _Var("")
        self.category = _Var("校园")
        self.style = _Var("")
        self.generated_content = ""
        self.parsed_sections = [
            {"title": "第一章"},
            {"title": "第二章"},
            {"title": "第三章"},
        ]

    def _ui(self, fn, *args, **kwargs):
        return fn(*args, **kwargs)

    def _ui_get(self, fn, *args, **kwargs):
        return fn(*args, **kwargs)


def _build_base_output(app: _DummyApp) -> str:
    intro = "目录（共3章）\n\n1. 第一章\n2. 第二章\n3. 第三章\n"
    ch1 = app._build_chapter_block_text(
        section_index=0,
        total_sections=3,
        section_title="第一章",
        section_content="第一章旧内容",
    )
    ch2 = app._build_chapter_block_text(
        section_index=1,
        total_sections=3,
        section_title="第二章",
        section_content="第二章旧内容",
    )
    ch3 = app._build_chapter_block_text(
        section_index=2,
        total_sections=3,
        section_title="第三章",
        section_content="第三章旧内容",
    )
    return f"{intro}{ch1}{ch2}{ch3}\n"


def test_regenerate_replace_keeps_original_position():
    app = _DummyApp()
    base = _build_base_output(app)

    action, merged = app._apply_generated_section_output(
        base_output_text=base,
        section_index=1,
        total_sections=3,
        section_title="第二章",
        section_content="第二章新内容",
        existing_chapter_policy="replace",
    )

    assert action == "replace"
    assert "第二章旧内容" not in merged
    assert "第二章新内容" in merged
    assert merged.count("✅ 第 2 章完成！") == 1
    assert merged.index("第一章旧内容") < merged.index("第二章新内容") < merged.index("第三章旧内容")


def test_regenerate_keep_both_inserts_candidate_near_original():
    app = _DummyApp()
    base = _build_base_output(app)

    action, merged = app._apply_generated_section_output(
        base_output_text=base,
        section_index=1,
        total_sections=3,
        section_title="第二章",
        section_content="第二章候选内容",
        existing_chapter_policy="keep_both",
    )

    assert action == "keep_both"
    assert "第二章旧内容" in merged
    assert "第二章候选内容" in merged
    assert "🧪 第 2 章候选版本" in merged
    assert merged.count("✅ 第 2 章完成！") == 1
    assert merged.index("第二章旧内容") < merged.index("第二章候选内容") < merged.index("第三章旧内容")


def test_regenerate_discard_keeps_original():
    app = _DummyApp()
    base = _build_base_output(app)

    action, merged = app._apply_generated_section_output(
        base_output_text=base,
        section_index=1,
        total_sections=3,
        section_title="第二章",
        section_content="第二章新内容",
        existing_chapter_policy="discard",
    )

    assert action == "discard"
    assert merged == base


def test_rebuild_generated_content_prefers_latest_completed_chapter():
    app = _DummyApp()
    base = _build_base_output(app)
    duplicate_latest = app._build_chapter_block_text(
        section_index=1,
        total_sections=3,
        section_title="第二章",
        section_content="第二章最新版本",
    )
    merged = f"{base}{duplicate_latest}\n"

    rebuilt = app._rebuild_generated_content_from_output(merged)

    assert "第二章最新版本" in rebuilt
    assert "第二章旧内容" not in rebuilt
    assert rebuilt.index("第一章旧内容") < rebuilt.index("第二章最新版本") < rebuilt.index("第三章旧内容")


def test_regenerate_replace_cleans_failed_stale_block():
    app = _DummyApp()
    ch1 = app._build_chapter_block_text(
        section_index=0,
        total_sections=3,
        section_title="第一章",
        section_content="第一章旧内容",
    )
    stale_ch2 = (
        "\n==================================================\n"
        "【第 2/3 章：第二章】\n\n"
        "生成出错:\nTraceback (most recent call last): ...\n"
    )
    ch3 = app._build_chapter_block_text(
        section_index=2,
        total_sections=3,
        section_title="第三章",
        section_content="第三章旧内容",
    )
    base = f"目录（共3章）\n{ch1}{stale_ch2}{ch3}\n"

    action, merged = app._apply_generated_section_output(
        base_output_text=base,
        section_index=1,
        total_sections=3,
        section_title="第二章",
        section_content="第二章新内容",
        existing_chapter_policy="replace",
    )

    assert action == "replace"
    assert "Traceback (most recent call last)" not in merged
    assert "第二章新内容" in merged
    assert merged.index("第一章旧内容") < merged.index("第二章新内容") < merged.index("第三章旧内容")


def test_report_error_does_not_dump_traceback_to_output():
    app = _DummyApp()

    with patch("tkinter.messagebox.showerror", lambda *args, **kwargs: None):
        app._report_section_generation_error(1, RuntimeError("network timeout"))

    assert "Traceback" not in app.output.text
    assert "❌ 生成出错（第 2 章）" in app.output.text
    assert "network timeout" in app.output.text

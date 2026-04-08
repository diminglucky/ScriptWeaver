from __future__ import annotations

from unittest.mock import patch

from src.gui.mixins.story_modules.outline_section_generate_mixin import OutlineSectionGenerateMixin
from src.gui.mixins.story_modules.outline_overview_mixin import OutlineOverviewMixin
from src.gui.mixins.story_modules.outline_preview_mixin import OutlinePreviewMixin
from src.gui.mixins.story_modules.story_infra import StoryInfraMixin


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

    def index(self, *_args):
        return "1.0"

    def see(self, *_args):
        return None


class _PreviewClient:
    def __init__(self, reply: str):
        self.reply = reply
        self.last_messages = []

    def chat(self, messages, temperature=0.0, max_tokens=0):
        _ = (temperature, max_tokens)
        self.last_messages = messages
        return self.reply


class _DummyApp(StoryInfraMixin, OutlineSectionGenerateMixin):
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


class _PreviewDummy(StoryInfraMixin, OutlinePreviewMixin, OutlineSectionGenerateMixin):
    def __init__(self):
        self.temperature = _Var(0.7)

    def _build_section_transition_context(self, section_index: int, previous_content: str) -> str:
        _ = (section_index, previous_content)
        return "- 上章收束后主角处于防御姿态。"

    def _build_story_memory_context(self, section_index: int, max_items: int = 3) -> str:
        _ = (section_index, max_items)
        return "- 第2章《走廊风声》摘要：他确认周明在隐瞒关键证据。"


class _GeneratePreviewDummy(StoryInfraMixin, OutlineOverviewMixin, OutlinePreviewMixin, OutlineSectionGenerateMixin):
    def __init__(self):
        self.output = _Output()
        self.status = _Var("")
        self.category = _Var("校园")
        self.style = _Var("")
        self.target_chars = _Var(2000)
        self.generated_content = "上章结尾。"
        self.parsed_sections = [{"title": "第一章"}]
        self.story_preview_before_apply = _Var(True)
        self.apply_payload = None
        self.prepare_prompt_kwargs = None

    def _ui(self, fn, *args, **kwargs):
        return fn(*args, **kwargs)

    def _ui_get(self, fn, *args, **kwargs):
        return fn(*args, **kwargs)

    def _get_output_text_snapshot(self):
        return "BASE"

    def _prepare_section_generation_prompt(self, **kwargs):
        self.prepare_prompt_kwargs = kwargs
        return 800, "section-prompt", "system-prompt"

    def _start_section_generation_ui(self, **_kwargs):
        return "1.0"

    def _stream_section_content(self, **_kwargs):
        return "原始章节正文"

    def _repair_section_tail_if_needed(self, *_args, **_kwargs):
        return ""

    def _repair_section_transition_if_needed(self, *_args, **_kwargs):
        return ""

    def _is_section_tail_complete(self, text: str) -> bool:
        tail = (text or "").strip()
        if not tail:
            return False
        import re
        # Check if text ends with Chinese punctuation
        if re.search(r"[。！？!?…；;]\s*$", tail):
            return True
        return False

    def _is_story_quality_review_enabled(self):
        return False

    def _preview_generated_section_before_apply(self, **_kwargs):
        return "accept", "用户确认后的预览正文"

    def _apply_generated_section_output(self, **kwargs):
        self.apply_payload = kwargs
        return "append", "FINAL"

    def _overwrite_output_text(self, text: str):
        self.output.text = text

    def _rebuild_generated_content_from_output(self, text: str):
        return "rebuilt:" + str(text)

    def _extract_memory_entry(self, *_args, **_kwargs):
        return {"summary": "ok", "plot_points": [], "relation_changes": [], "unresolved_hooks": [], "state_shift": ""}

    def _update_story_memory_ledger(self, *_args, **_kwargs):
        return None

    def _auto_save_to_project(self):
        return None


class _SegmentClient:
    def stream(self, *_args, **_kwargs):
        yield "分段正文"


class _SegmentOverviewDummy(StoryInfraMixin, OutlineSectionGenerateMixin):
    def __init__(self):
        self.output = _Output()
        self.status = _Var("")
        self.category = _Var("校园")
        self.style = _Var("")
        self.temperature = _Var(0.7)
        self.section_prompt_calls: list[dict] = []

    def _ui(self, fn, *args, **kwargs):
        return fn(*args, **kwargs)

    def _ui_get(self, fn, *args, **kwargs):
        return fn(*args, **kwargs)

    def _ensure_story_global_overview_before_generation(self, **_kwargs):
        return "accept", "全书总览"

    def _prepare_section_overview_before_generation(self, **kwargs):
        section_index = int(kwargs.get("section_index", 0))
        return "accept", f"第{section_index + 1}段总览"

    def _build_section_prompt(self, **kwargs):
        self.section_prompt_calls.append(kwargs)
        return "SECTION_PROMPT"

    def _repair_section_tail_if_needed(self, *_args, **_kwargs):
        return ""

    def _is_section_tail_complete(self, text: str) -> bool:
        tail = (text or "").strip()
        if not tail:
            return False
        import re
        if re.search(r"[。！？!?…；;]\s*$", tail):
            return True
        return False

    def _repair_section_transition_if_needed(self, *_args, **_kwargs):
        return ""

    def _is_story_quality_review_enabled(self):
        return False

    def _preview_generated_section_before_apply(self, **kwargs):
        return "accept", kwargs.get("section_content", "")

    def _extract_memory_entry(self, *_args, **_kwargs):
        return {"summary": "ok", "plot_points": [], "relation_changes": [], "unresolved_hooks": [], "state_shift": ""}

    def _update_story_memory_ledger(self, *_args, **_kwargs):
        return None


class _GlobalOverviewDummy(StoryInfraMixin, OutlineOverviewMixin, OutlineSectionGenerateMixin):
    def __init__(self):
        self.story_global_overview_enabled = _Var(True)
        self.story_global_overview_text = "旧总览"
        self.story_global_overview_signature = "oldsig"
        self.temperature = _Var(0.7)
        self.status = _Var("")
        self.dialog_called = 0
        self.dialog_result = ("accept", "新总览")

    def _ui(self, fn, *args, **kwargs):
        return fn(*args, **kwargs)

    def _show_story_global_overview_dialog(self, **_kwargs):
        self.dialog_called += 1
        return self.dialog_result


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


def test_regenerate_preview_uses_feedback_and_continuity_context():
    app = _PreviewDummy()
    client = _PreviewClient(
        "他把湿掉的校服袖口慢慢卷起，先看了眼走廊监控，再压低声音开口。"
        "门后的人没立即回应，空气里只有电扇老旧的嗡鸣。"
        "他没有退，手指敲了两下门框，像在提醒对方也在提醒自己。"
        "这一次，他决定把话说清楚。"
    )
    rewritten = app._regenerate_section_preview_with_feedback(
        client=client,
        section_index=2,
        section_title="宿舍夜话与匿名信",
        current_content="他站在门口，没有进去。",
        feedback="情绪更克制，增加走廊和动作细节，不要直接喊口号。",
        requirement="写一个校园悬疑故事",
        category="校园",
        previous_content="他把纸条塞进袖口，转身走向宿舍楼。",
    )

    prompt = client.last_messages[0]["content"]
    assert rewritten.startswith("他把湿掉的校服袖口慢慢卷起")
    assert "用户修改意见" in prompt
    assert "上章收束句" in prompt
    assert "记忆账本" in prompt


def test_regenerate_preview_without_feedback_still_generates_new_variant():
    app = _PreviewDummy()
    client = _PreviewClient(
        "他在门口停了两秒，先抬眼看了眼走廊灯，再把呼吸压稳。"
        "门后传来翻页声，他没有立刻敲门，只把掌心的冷汗擦在衣摆上。"
        "这一次，他打算换个方式开口。"
    )
    rewritten = app._regenerate_section_preview_with_feedback(
        client=client,
        section_index=2,
        section_title="宿舍夜话与匿名信",
        current_content="他站在门口，没有进去。",
        feedback="",
        requirement="写一个校园悬疑故事",
        category="校园",
        previous_content="他把纸条塞进袖口，转身走向宿舍楼。",
    )

    prompt = client.last_messages[0]["content"]
    assert rewritten.startswith("他在门口停了两秒")
    assert "未填写意见" in prompt


def test_do_generate_section_uses_accepted_preview_content():
    app = _GeneratePreviewDummy()
    result = app._do_generate_section(
        client=None,
        query="测试需求",
        contexts=[],
        section_index=0,
        existing_chapter_policy="replace",
    )

    assert result == "append"
    assert app.apply_payload is not None
    assert app.apply_payload["section_content"] == "用户确认后的预览正文"


def test_do_generate_section_passes_accepted_overview_plan_into_prompt():
    app = _GeneratePreviewDummy()
    app._prepare_section_overview_before_generation = lambda **_kwargs: ("accept", "总览A：先冲突后缓和")

    result = app._do_generate_section(
        client=None,
        query="测试需求",
        contexts=[],
        section_index=0,
        existing_chapter_policy="replace",
    )

    assert result == "append"
    assert app.prepare_prompt_kwargs is not None
    assert app.prepare_prompt_kwargs["section_overview_plan"] == "总览A：先冲突后缓和"


def test_generate_in_sections_uses_section_overview_plan():
    app = _SegmentOverviewDummy()
    client = _SegmentClient()
    ok = app._generate_in_sections(
        client=client,
        requirement="测试需求",
        contexts=[],
        sections=[{"title": "第一段", "items": []}],
        target_chars=1200,
    )

    assert ok is True
    assert len(app.section_prompt_calls) == 1
    assert app.section_prompt_calls[0]["section_overview_plan"] == "第1段总览"


def test_global_overview_signature_mismatch_triggers_review():
    app = _GlobalOverviewDummy()
    expected_sig = app._build_story_global_overview_signature(
        requirement="新需求",
        category="校园",
        outline_text="1. 新目录",
    )

    action, overview = app._ensure_story_global_overview_before_generation(
        client=_PreviewClient("unused"),
        requirement="新需求",
        category="校园",
        contexts=[],
        outline_text="1. 新目录",
        force_review=False,
    )

    assert action == "accept"
    assert overview == "新总览"
    assert app.dialog_called == 1
    assert app.story_global_overview_signature == expected_sig


def test_global_overview_signature_match_skips_review():
    app = _GlobalOverviewDummy()
    app.story_global_overview_text = "稳定总览"
    app.story_global_overview_signature = app._build_story_global_overview_signature(
        requirement="稳定需求",
        category="校园",
        outline_text="1. 稳定目录",
    )

    action, overview = app._ensure_story_global_overview_before_generation(
        client=_PreviewClient("unused"),
        requirement="稳定需求",
        category="校园",
        contexts=[],
        outline_text="1. 稳定目录",
        force_review=False,
    )

    assert action == "accept"
    assert overview == "稳定总览"
    assert app.dialog_called == 0

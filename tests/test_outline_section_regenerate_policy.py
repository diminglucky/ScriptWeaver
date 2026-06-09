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


class _BlueprintClient:
    def __init__(self):
        self.last_messages = []

    def stream(self, messages, **_kwargs):
        self.last_messages = messages
        yield (
            "=== 第1章 ===\n"
            "【承接点】从雨夜电话开篇。\n"
            "【本章目标】主角必须确认匿名信来源。\n"
            "【场景链】\n"
            "场景1：目标/查看信封；阻力/监控缺失；行动/询问门卫；结果/得到错误时间；新问题/谁改了记录。\n"
            "场景2：目标/核对记录；阻力/同学隐瞒；行动/当面对质；结果/关系破裂；新问题/匿名信是否来自熟人。\n"
            "场景3：目标/逼近真相；阻力/新证据被拿走；行动/追到楼梯口；结果/看见熟悉背影；新问题/为什么是他。\n"
            "【反转或失败】主角发现自己一直查错了方向。\n"
            "【不可逆代价】他失去同学信任。\n"
            "【人物状态变化】从被动困惑变成主动怀疑。\n"
            "【新钩子】熟悉背影为什么提前知道匿名信。\n"
            "【伏笔线索】埋伏笔→第2章回收。\n"
            "【连续性禁区】不得跳过雨夜电话后的即时行动。\n"
        )


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
        self.memory_contents: list[str] = []
        self.memory_updates: list[tuple[int, str, dict]] = []

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

    def _extract_memory_entry(self, *_args, **kwargs):
        self.memory_contents.append(str(kwargs.get("section_content", "")))
        return {"summary": "ok", "plot_points": [], "relation_changes": [], "unresolved_hooks": [], "state_shift": ""}

    def _update_story_memory_ledger(self, section_index, section_title, entry):
        self.memory_updates.append((section_index, section_title, entry))
        return None

    def _auto_save_to_project(self):
        return None


class _QualityFallbackDummy(_GeneratePreviewDummy):
    def __init__(self):
        super().__init__()
        self.story_preview_before_apply = _Var(False)
        self.rewrite_calls = 0
        self.polish_calls = 0

    def _is_story_quality_review_enabled(self):
        return True

    def _is_auto_polish_enabled(self):
        return True

    def _get_story_quality_min_avg(self):
        return 8.0

    def _get_story_quality_min_dim(self):
        return 7.5

    def _get_story_quality_thresholds(self):
        return 8.0, 7.5

    def _review_section_quality(self, *_args, **_kwargs):
        return {
            "scores": {
                "realism": 6.0,
                "emotion": 6.0,
                "continuity": 6.0,
                "escalation": 6.0,
                "hook_density": 6.0,
            },
            "issues": ["冲突弱，缺少不可逆代价"],
            "key_fix": "补足冲突与代价",
        }

    def _needs_continuity_polish(self, *_args, **_kwargs):
        return False

    def _needs_structural_rewrite(self, *_args, **_kwargs):
        return True

    def _rewrite_section_structure(self, *_args, **_kwargs):
        self.rewrite_calls += 1
        return "原始章节正文"

    def _polish_section_text(self, *_args, **_kwargs):
        self.polish_calls += 1
        return "普通润色后的章节正文。"

    def _preview_generated_section_before_apply(self, **kwargs):
        return "accept", kwargs.get("section_content", "")

    def _update_chapter_quality_report(self, *_args, **_kwargs):
        return None


class _FinalMemoryDummy(_QualityFallbackDummy):
    def _preview_generated_section_before_apply(self, **_kwargs):
        return "accept", "用户最终改稿正文。"


class _ParallelReviewDummy(StoryInfraMixin, OutlineSectionGenerateMixin):
    def __init__(self):
        self.review_args = None
        self.memory_args = None

    def _is_story_fast_mode(self):
        return False

    def _is_story_quality_review_enabled(self):
        return True

    def _is_section_tail_complete(self, _text: str) -> bool:
        return True

    def _review_section_quality(self, *args):
        self.review_args = args
        return {"scores": {"continuity": 8.0}, "avg_score": 8.0, "issues": [], "key_fix": ""}

    def _extract_memory_entry(self, *args, **kwargs):
        self.memory_args = (args, kwargs)
        return {"summary": "ok"}


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
        self.memory_contents: list[str] = []

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

    def _extract_memory_entry(self, *_args, **kwargs):
        self.memory_contents.append(str(kwargs.get("section_content", "")))
        return {"summary": "ok", "plot_points": [], "relation_changes": [], "unresolved_hooks": [], "state_shift": ""}

    def _update_story_memory_ledger(self, *_args, **_kwargs):
        return None


class _SegmentFinalMemoryDummy(_SegmentOverviewDummy):
    def _preview_generated_section_before_apply(self, **_kwargs):
        return "accept", "分段最终预览正文。"


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


class _OverviewOnlyDummy(StoryInfraMixin, OutlineOverviewMixin):
    def __init__(self):
        self.temperature = _Var(0.7)
        self.style = _Var("克制悬疑")
        self.output = _Output()
        self.last_retry_prompt = ""

    def _ui(self, fn, *args, **kwargs):
        return fn(*args, **kwargs)

    def _ui_get(self, fn, *args, **kwargs):
        return fn(*args, **kwargs)

    def _build_story_state_contract(self, section_index: int, previous_content: str = "") -> str:
        _ = (section_index, previous_content)
        return "【事实锁定】\n- 匿名信已经出现，不能重新当作首次发现。\n【未回收钩子队列】\n- 送信人身份未明。"

    def _chat_with_retry_and_token_fallback(self, **kwargs):
        self.last_retry_prompt = str(kwargs.get("prompt", ""))
        return "【承接点】从匿名信余波继续。\n【本章目标】确认送信人。\n【场景链】\n场景1：目标/查信；阻力/记录缺失；行动/询问门卫；结果/得到线索；新问题/谁改了时间。", ""


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


def test_do_generate_section_falls_back_to_polish_when_structure_rewrite_noops():
    app = _QualityFallbackDummy()

    result = app._do_generate_section(
        client=None,
        query="测试需求",
        contexts=[],
        section_index=0,
        existing_chapter_policy="replace",
    )

    assert result == "append"
    assert app.rewrite_calls == 1
    assert app.polish_calls == 1
    assert app.apply_payload is not None
    assert app.apply_payload["section_content"] == "普通润色后的章节正文。"


def test_post_stream_quality_review_receives_repaired_text_and_section_overview_plan():
    app = _ParallelReviewDummy()

    review = app._post_stream_quality_review(
        client=None,
        section_content="修复后的完整章节正文。",
        section_title="匿名信",
        section_index=0,
        previous_content="",
        requirement="写一个校园悬疑故事",
        category="校园",
        section_overview_plan="【本章目标】确认送信人。\n【场景链】场景1：目标/查信；阻力/记录缺失；行动/询问门卫；结果/获得线索；新问题/谁改了时间。",
    )

    assert review is not None
    assert app.review_args is not None
    assert app.review_args[2] == "修复后的完整章节正文。"
    assert app.review_args[-1].startswith("【本章目标】确认送信人")


def test_do_generate_section_extracts_memory_from_final_accepted_text():
    app = _FinalMemoryDummy()

    result = app._do_generate_section(
        client=None,
        query="测试需求",
        contexts=[],
        section_index=0,
        existing_chapter_policy="replace",
    )

    assert result == "append"
    assert app.apply_payload is not None
    assert app.apply_payload["section_content"] == "用户最终改稿正文。"
    assert app.memory_contents == ["用户最终改稿正文。"]
    assert len(app.memory_updates) == 1


def test_final_memory_extraction_still_runs_when_quality_review_disabled():
    app = _GeneratePreviewDummy()

    memory_entry = app._extract_final_memory_entry(
        client=None,
        section_index=0,
        section_title="第一章",
        section_content="最终入稿正文。",
        include_memory=True,
    )

    assert memory_entry is not None
    assert app.memory_contents == ["最终入稿正文。"]


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


def test_generate_in_sections_extracts_memory_from_final_preview_text():
    app = _SegmentFinalMemoryDummy()
    client = _SegmentClient()
    ok = app._generate_in_sections(
        client=client,
        requirement="测试需求",
        contexts=[],
        sections=[{"title": "第一段", "items": []}],
        target_chars=1200,
    )

    assert ok is True
    assert app.memory_contents == ["分段最终预览正文。"]


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


def test_local_section_overview_fallback_returns_scene_execution_card():
    app = _OverviewOnlyDummy()

    card = app._build_local_section_overview_fallback(
        section_title="匿名信",
        requirement="写一个校园悬疑故事",
        category="校园",
        previous_content="他把纸条塞进袖口，转身走向宿舍楼。",
        section_points=["询问门卫", "对质同学", "发现监控被删"],
    )

    assert "【承接点】" in card
    assert "【本章目标】" in card
    assert "【场景链】" in card
    assert "目标/" in card
    assert "阻力/" in card
    assert "行动/" in card
    assert "结果/" in card
    assert "新问题/" in card
    assert "【不可逆代价】" in card
    assert "【连续性禁区】" in card


def test_generate_all_chapter_blueprints_requests_scene_execution_cards():
    app = _OverviewOnlyDummy()
    client = _BlueprintClient()

    blueprints = app.generate_all_chapter_blueprints(
        client=client,
        requirement="写一个校园悬疑故事",
        category="校园",
        outline_text="1. 匿名信",
        sections=[{"title": "匿名信"}],
    )

    prompt = client.last_messages[1]["content"]
    assert len(blueprints) == 1
    assert blueprints[0]["blueprint"].startswith("【承接点】")
    assert "场景执行卡" in prompt
    assert "【场景链】" in prompt
    assert "目标/阻力/行动/结果/新问题" in prompt
    assert "连续性禁区" in prompt
    assert "静态说明" not in prompt


def test_section_overview_draft_includes_story_state_contract():
    app = _OverviewOnlyDummy()

    draft = app._generate_section_overview_draft(
        client=None,
        section={"title": "追查匿名信", "items": ["询问门卫"], "event_promise": "确认送信人线索"},
        section_index=1,
        total_sections=3,
        requirement="写一个校园悬疑故事",
        contexts=[],
        category="校园",
        previous_content="他把匿名信压进书页，听见楼道里有人停步。",
    )

    assert draft.startswith("【承接点】")
    assert "故事状态合同" in app.last_retry_prompt
    assert "匿名信已经出现" in app.last_retry_prompt
    assert "送信人身份未明" in app.last_retry_prompt
    assert "【连续性禁区】必须引用故事状态合同" in app.last_retry_prompt


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

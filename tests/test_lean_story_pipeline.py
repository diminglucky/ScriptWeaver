from __future__ import annotations

from unittest.mock import patch

from src.gui.mixins.story_modules.lean_story_mixin import LeanStoryMixin


class _Var:
    def __init__(self, value=None):
        self.value = value

    def get(self):
        return self.value

    def set(self, value):
        self.value = value


class _ImmediateThread:
    def __init__(self, target=None, daemon=None):
        self.target = target

    def start(self):
        if self.target:
            self.target()


class _FakeClient:
    def __init__(self, response: str):
        self.response = response
        self.calls = []

    def chat(self, messages, **kwargs):
        self.calls.append((messages, kwargs))
        return self.response


class _LeanApp(LeanStoryMixin):
    def __init__(self):
        self.target_chars = _Var(1800)
        self.generated_content = "上一章最后一段。"


def test_lean_prompt_contains_state_and_no_planning_artifacts():
    app = _LeanApp()
    prompt = app._build_lean_chapter_prompt(
        query="写一个悬疑故事",
        section={"title": "第1章 异常开场"},
        section_index=0,
        total_sections=1,
        target_chars=1800,
        state={
            "summary": "主角收到警告",
            "facts": ["警告来自陌生号码"],
            "open_hooks": ["谁发送了警告"],
            "characters": ["林夏：保持警觉"],
            "last_tail": "",
        },
    )

    assert "当前故事状态" in prompt
    assert "警告来自陌生号码" in prompt
    assert "章节蓝图" not in prompt
    assert "全书总览" not in prompt


def test_lean_state_update_uses_one_model_call_and_falls_back_tail():
    app = _LeanApp()
    client = _FakeClient(
        '{"summary":"局势升级","facts":["钥匙丢失"],'
        '"open_hooks":["谁拿走钥匙"],"characters":["林夏：被怀疑"]}'
    )

    state = app._update_lean_story_state(
        client=client,
        chapter_index=0,
        chapter_title="第1章",
        chapter_text="第一章正文。钥匙不见了。",
        state={"summary": "", "facts": [], "open_hooks": [], "characters": []},
    )

    assert len(client.calls) == 1
    assert state["summary"] == "局势升级"
    assert state["facts"] == ["钥匙丢失"]
    assert state["last_tail"] == "第一章正文。钥匙不见了。"


class _LeanLoopApp(LeanStoryMixin):
    def __init__(self):
        self.parsed_sections = [{"title": "第1章"}]
        self.calls = []
        self.busy_states = []
        self.status = _Var("")

    def _is_story_lean_mode(self):
        return True

    def _generate_all_chapters_lean(self, **kwargs):
        self.calls.append(kwargs)

    def _ui(self, func, *args, **kwargs):
        return func(*args, **kwargs)

    def set_busy(self, busy):
        self.busy_states.append(busy)


def test_auto_loop_routes_lean_mode_to_two_call_pipeline():
    app = _LeanLoopApp()

    with patch(
        "src.gui.mixins.story_modules.lean_story_mixin.threading.Thread",
        _ImmediateThread,
    ):
        started = app._auto_generate_all_sections("需求", [], start_index=0)

    assert started is True
    assert app.calls == [
        {"query": "需求", "start_index": 0, "total_sections": 1}
    ]
    assert app.busy_states == [True, False]

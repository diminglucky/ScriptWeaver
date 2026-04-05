from __future__ import annotations

from src.gui.mixins.story_modules.outline_quality_mixin import OutlineQualityMixin


class _Var:
    def __init__(self, value):
        self._value = value

    def get(self):
        return self._value


class _FakeClient:
    def __init__(self, reply: str):
        self.reply = reply
        self.last_messages = None

    def chat(self, _messages, temperature=0.0, max_tokens=0):  # pragma: no cover - simple stub
        _ = (temperature, max_tokens)
        self.last_messages = _messages
        return self.reply


class _Dummy(OutlineQualityMixin):
    def __init__(self):
        self.temperature = _Var(0.7)

    def _build_section_transition_context(self, section_index: int, previous_content: str) -> str:
        _ = (section_index, previous_content)
        return "- 上章情绪：压抑后强行镇定。"

    def _build_story_memory_context(self, section_index: int, max_items: int = 3) -> str:
        _ = (section_index, max_items)
        return "- 第1章《旧账》摘要：主角拿到证据但未公开。"


def test_transition_repair_rewrites_redundant_opening():
    obj = _Dummy()
    client = _FakeClient("他踩着未散的水汽停下，先看清了走廊尽头的人影，再开口。")
    previous = "他推开门，冷风一下子扑到脸上。"
    section = "他推开门，冷风一下子扑到脸上。\n\n周明抬起头，手里的课本差点掉地。"

    repaired = obj._repair_section_transition_if_needed(
        client,
        section_index=1,
        section_title="学生宿舍里的秘密交易",
        previous_content=previous,
        section_content=section,
    )

    assert repaired != section
    assert repaired.startswith("他踩着未散的水汽停下")
    assert "周明抬起头" in repaired


def test_transition_repair_skips_first_section():
    obj = _Dummy()
    client = _FakeClient("新的开头")
    section = "开篇第一段。\n\n后续正文。"

    repaired = obj._repair_section_transition_if_needed(
        client,
        section_index=0,
        section_title="开篇",
        previous_content="",
        section_content=section,
    )

    assert repaired == section


def test_continuity_low_score_triggers_polish_gate():
    obj = _Dummy()

    assert obj._needs_continuity_polish({"scores": {"continuity": 7.2}}, section_index=1)
    assert not obj._needs_continuity_polish({"scores": {"continuity": 8.1}}, section_index=1)
    assert not obj._needs_continuity_polish({"scores": {"continuity": 6.0}}, section_index=0)


def test_polish_prompt_includes_continuity_context_for_middle_section():
    obj = _Dummy()
    client = _FakeClient(
        "他贴着墙根慢慢走，鞋底在地面蹭出轻响。"
        "走廊尽头的灯忽明忽暗，他把呼吸压得更低，"
        "在门把上停了两秒才推门，生怕惊动门后的人。"
        "门内传来翻书声，他侧耳听了三拍才迈进去，"
        "肩胛绷得发硬，连抬眼都带着迟疑。"
        "他没先开口，只把湿冷的手掌藏进衣兜，"
        "让对方先说第一句。"
    )
    review = {"scores": {"continuity": 6.9}, "issues": ["衔接生硬"], "key_fix": "修复跨章衔接"}

    polished = obj._polish_section_text(
        client,
        section_title="学生宿舍里的秘密交易",
        section_content="他站在走廊尽头，手心发冷。",
        review=review,
        target_chars_per_section=900,
        section_index=1,
        previous_content="他推开门，冷风一下子扑到脸上。",
    )

    prompt = (client.last_messages or [{}])[0].get("content", "")
    assert polished.startswith("他贴着墙根慢慢走")
    assert "连贯性资料" in prompt
    assert "上章收束句" in prompt
    assert "记忆账本" in prompt

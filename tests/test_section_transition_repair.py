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

    def _build_story_state_contract(self, section_index: int, previous_content: str = "") -> str:
        _ = (section_index, previous_content)
        return "【事实锁定】\n- 主角已经拿到证据但尚未公开。\n【未回收钩子队列】\n- 内鬼身份未明。"


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


def test_low_hook_or_escalation_triggers_structural_rewrite_gate():
    obj = _Dummy()

    assert obj._needs_structural_rewrite(
        {"scores": {"escalation": 6.8, "hook_density": 8.0}, "issues": []},
        section_index=0,
    )
    assert obj._needs_structural_rewrite(
        {"scores": {"escalation": 8.0, "hook_density": 6.9}, "issues": []},
        section_index=0,
    )
    assert obj._needs_structural_rewrite(
        {"scores": {"escalation": 8.0, "hook_density": 8.0}, "issues": ["本章过于平淡"]},
        section_index=0,
    )
    assert not obj._needs_structural_rewrite(
        {"scores": {"escalation": 8.0, "hook_density": 8.0, "continuity": 8.2}, "issues": []},
        section_index=1,
    )


def test_quality_review_prompt_includes_scene_card_contract():
    obj = _Dummy()
    client = _FakeClient(
        '{"scores":{"realism":8,"detail":8,"coherence":6.5,"continuity":8,'
        '"escalation":6.5,"hook_density":6.5,"naturalness":8},'
        '"strengths":["有现场感"],"issues":["未兑现执行卡里的不可逆代价"],"key_fix":"补足执行卡兑现"}'
    )

    review = obj._review_section_quality(
        client,
        section_title="会议室里的调包",
        section_content="他想了很久，决定先等等。",
        requirement="写一个职场逆袭故事",
        category="职场",
        section_index=1,
        previous_content="他推开门，冷风一下子扑到脸上。",
        section_overview_plan="【本章目标】当众证明证据被调包。\n【不可逆代价】主角失去唯一筹码。\n【新钩子】内鬼身份暴露一角。",
    )

    prompt = (client.last_messages or [{}])[0].get("content", "")
    assert review["key_fix"] == "补足执行卡兑现"
    assert "故事状态合同" in prompt
    assert "本章场景执行卡" in prompt
    assert "当众证明证据被调包" in prompt
    assert "未兑现" not in prompt
    assert "escalation/hook_density/coherence 必须低于7" in prompt


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


def test_structural_rewrite_prompt_includes_contract_and_continuity_context():
    obj = _Dummy()
    client = _FakeClient(
        "他没有再解释，直接把那份调包后的证据摊在桌上。"
        "对方脸色一变，会议室里所有人的目光同时压过来，"
        "他这才意识到自己已经没有退路。"
        "他必须在三分钟内证明原件曾经存在，否则连最后一个愿意帮他的人也会被拖下水。"
        "他把手机反扣在桌面，听见录音软件还在后台跳秒，"
        "于是故意提高声音问对方为什么提前知道文件袋编号。"
        "那人下意识看向门口，门缝里正站着本不该出现的财务主管。"
        "所有人都顺着他的视线望过去，会议室短暂安静下来，"
        "而主角终于明白，调包不是为了毁掉证据，是为了逼他把真正的内鬼带到明面上。"
    )
    review = {
        "scores": {"escalation": 6.8, "hook_density": 6.5, "continuity": 7.0},
        "issues": ["冲突弱，缺少不可逆代价"],
        "key_fix": "补足证据调包后的代价",
    }

    rewritten = obj._rewrite_section_structure(
        client,
        section_title="会议室里的调包",
        section_content="他想了很久，觉得事情有些不对。",
        review=review,
        target_chars_per_section=900,
        section_index=1,
        previous_content="他推开门，冷风一下子扑到脸上。",
        section_overview_plan="【核心事件】他当众提交证据，却发现证据被调包。",
        event_promise="证据被调包，主角失去唯一筹码",
    )

    prompt = (client.last_messages or [{}])[0].get("content", "")
    assert rewritten.startswith("他没有再解释")
    assert "剧情重构版" in prompt
    assert "本章剧情任务书" in prompt
    assert "证据被调包" in prompt
    assert "上章收束句" in prompt
    assert "记忆账本" in prompt
    assert "故事状态合同" in prompt
    assert "内鬼身份未明" in prompt

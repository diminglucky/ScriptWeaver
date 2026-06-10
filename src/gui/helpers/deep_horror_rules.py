"""Deep psychological horror rules for story prompts."""

from __future__ import annotations


DEEP_HORROR_KEYWORDS = (
    "惊悚",
    "恐怖",
    "悬疑",
    "诡异",
    "灵异",
    "怪谈",
    "心理",
    "噩梦",
)


def should_apply_deep_horror_rules(*values: str) -> bool:
    """Return whether the prompt should receive deep-horror constraints."""
    text = " ".join(str(value or "") for value in values)
    return any(keyword in text for keyword in DEEP_HORROR_KEYWORDS)


def build_deep_horror_rules(
    *,
    stage: str = "story",
    requirement: str = "",
    category: str = "",
    style_hint: str = "",
    template_label: str = "",
    template_key: str = "",
) -> str:
    """Return rules that favor soul-level dread over stale horror props."""
    if not should_apply_deep_horror_rules(
        requirement,
        category,
        style_hint,
        template_label,
        template_key,
    ):
        return ""

    scope = "整篇故事" if stage == "story" else "本章" if stage == "section" else "目录"
    return (
        f"- {scope}的恐惧来源必须是“熟悉生活突然不对劲”：亲人说出不该知道的话、房间细节被悄悄改动、记忆与证据互相否定、身份关系开始松动、日常规则被轻轻破坏。\n"
        "- 惊悚感要来自灵魂深处的不安：主角越解释越不确定，越求证越发现自己也可能是问题的一部分；读者怕的不是怪物出现，而是“我信赖的世界不再可信”。\n"
        "- 禁止把恐怖主要建立在手术刀、审讯室、废弃医院、解剖台、血浆、尸块、白大褂、地下室囚禁、连环杀手独白等廉价道具或常见场景上，除非用户需求明确要求。\n"
        "- 每个惊悚节点都要有一个具体但反常的日常细节：同一句话第二次出现时多了一个字、合照里站位变了、家人避开某个称呼、门锁没有坏却总是从里面反锁、手机记录证明主角去过自己没去过的地方。\n"
        "- 不要用大段解释“这里很恐怖”；要让异常先小到可以被忽略，再逐步变成无法否认，最后逼迫人物重新怀疑自己的记忆、身份、关系或道德立场。\n"
        "- 反转不能只是“凶手另有其人”；更好的反转是：主角依赖的证据本身有问题、保护他的人在改写他的认知、他一直逃避的真相来自自己、或者最安全的关系才是恐惧源头。\n"
        "- 结尾要留下后劲：真相即使被解释，也必须改变主角对某个亲密关系、日常空间或自身记忆的信任，让读者读完后想到自己的生活细节也会发凉。"
    )

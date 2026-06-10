"""Story category signal helpers.

This module keeps category inference out of the prompt mixins so the
classification logic can evolve without bloating the alignment code.
"""

from __future__ import annotations

from collections.abc import Iterable


_STORY_CATEGORY_CANONICAL_ALIASES = {
    "惊悚": "心理惊悚",
    "恐怖": "心理惊悚",
}


_STORY_CATEGORY_SIGNAL_GROUPS: dict[str, tuple[tuple[str, int], ...]] = {
    "校园": (
        ("校园", 6),
        ("学生", 4),
        ("班级", 4),
        ("宿舍", 4),
        ("宿舍楼", 5),
        ("老师", 3),
        ("班主任", 5),
        ("考试", 3),
        ("成绩单", 4),
        ("晚自习", 5),
        ("校服", 4),
        ("校门", 4),
        ("校门口", 5),
        ("社团", 3),
        ("班群", 3),
        ("广播站", 4),
    ),
    "职场": (
        ("职场", 6),
        ("公司", 5),
        ("同事", 5),
        ("上司", 5),
        ("老板", 5),
        ("办公室", 5),
        ("工位", 4),
        ("项目", 4),
        ("KPI", 5),
        ("绩效", 5),
        ("裁员", 5),
        ("调岗", 4),
        ("晋升", 4),
        ("加班", 2),
        ("报销", 3),
        ("周报", 3),
        ("会议纪要", 4),
        ("合同", 2),
        ("邮件", 2),
        ("群消息", 2),
        ("打卡", 3),
        ("开会", 2),
    ),
    "悬疑": (
        ("悬疑", 6),
        ("命案", 5),
        ("线索", 4),
        ("侦探", 4),
        ("凶手", 4),
        ("疑点", 4),
        ("真相", 4),
        ("反转", 4),
        ("证据", 4),
        ("档案", 3),
        ("匿名", 3),
        ("调查", 4),
        ("失踪", 4),
        ("录音", 3),
        ("监控", 3),
        ("旧照片", 3),
        ("遗嘱", 3),
    ),
    "心理惊悚": (
        ("心理惊悚", 6),
        ("惊悚", 5),
        ("恐怖", 5),
        ("灵异", 4),
        ("怪谈", 4),
        ("梦魇", 4),
        ("诡异", 4),
        ("门锁", 3),
        ("反锁", 3),
        ("陌生短信", 5),
        ("未知来电", 5),
        ("来电显示未知", 5),
        ("群聊", 3),
        ("监控", 4),
        ("旧照片", 4),
        ("错位记忆", 5),
        ("记忆缺口", 5),
        ("记忆错位", 5),
        ("失忆", 4),
        ("夜班", 2),
        ("楼道", 2),
        ("电梯", 2),
        ("钥匙", 2),
        ("指纹锁", 4),
        ("镜子", 3),
        ("收件箱", 3),
        ("语音", 2),
        ("不该知道", 4),
        ("少了我", 5),
        ("合租", 2),
        ("房租", 2),
        ("加班", 1),
        ("合同", 1),
        ("旧账", 3),
        ("便签", 2),
        ("门缝", 3),
        ("走廊", 2),
    ),
    "科幻": (
        ("科幻", 6),
        ("未来", 4),
        ("AI", 5),
        ("人工智能", 5),
        ("机器人", 4),
        ("太空", 4),
        ("时空", 4),
        ("实验室", 4),
        ("算法", 3),
        ("芯片", 3),
        ("虚拟", 3),
        ("记忆上传", 5),
    ),
    "爱情": (
        ("爱情", 6),
        ("恋爱", 4),
        ("告白", 4),
        ("前任", 4),
        ("暗恋", 4),
        ("分手", 4),
        ("心动", 3),
        ("复合", 4),
        ("失约", 3),
    ),
    "成长": (
        ("成长", 6),
        ("蜕变", 4),
        ("自我", 3),
        ("逆袭", 4),
        ("成熟", 4),
        ("和解", 3),
        ("选择", 2),
        ("告别", 2),
    ),
    "亲情": (
        ("亲情", 6),
        ("父亲", 5),
        ("母亲", 5),
        ("家人", 4),
        ("兄妹", 4),
        ("家庭", 4),
        ("孩子", 3),
        ("陪伴", 2),
    ),
    "社会观察": (
        ("社会", 5),
        ("现实", 4),
        ("阶层", 4),
        ("制度", 4),
        ("舆论", 4),
        ("公共", 3),
        ("规则", 3),
        ("偏见", 3),
    ),
    "历史": (
        ("历史", 6),
        ("朝代", 4),
        ("古代", 4),
        ("王朝", 4),
        ("战国", 4),
        ("明朝", 4),
        ("清朝", 4),
        ("遗址", 3),
    ),
    "奇幻": (
        ("奇幻", 6),
        ("魔法", 4),
        ("精灵", 4),
        ("异界", 4),
        ("龙", 3),
        ("神话", 4),
        ("咒语", 4),
        ("仪式", 3),
    ),
}


def normalize_story_category_label(category: str) -> str:
    """Return the canonical label used by the signal maps."""
    text = str(category or "").strip()
    if not text:
        return ""
    return _STORY_CATEGORY_CANONICAL_ALIASES.get(text, text)


def get_story_category_signals(category: str) -> tuple[str, ...]:
    """Return signal phrases for a category."""
    canonical = normalize_story_category_label(category)
    return tuple(signal for signal, _weight in _STORY_CATEGORY_SIGNAL_GROUPS.get(canonical, ()))


def _iter_category_signals(category: str) -> Iterable[tuple[str, int]]:
    canonical = normalize_story_category_label(category)
    return _STORY_CATEGORY_SIGNAL_GROUPS.get(canonical, ())


def score_story_category(text: str, category: str) -> int:
    """Score how strongly *text* matches *category* signals."""
    haystack = str(text or "").strip()
    if not haystack:
        return 0
    score = 0
    for signal, weight in _iter_category_signals(category):
        if signal and signal in haystack:
            score += max(1, int(weight))
    return score


def infer_story_category(text: str) -> tuple[str, int]:
    """Infer the most likely category from free-form requirement text."""
    haystack = str(text or "").strip()
    if not haystack:
        return "", 0

    best_category = ""
    best_score = 0
    for category in _STORY_CATEGORY_SIGNAL_GROUPS:
        score = score_story_category(haystack, category)
        if score > best_score:
            best_score = score
            best_category = category
    if best_score <= 0:
        return "", 0
    return best_category, best_score


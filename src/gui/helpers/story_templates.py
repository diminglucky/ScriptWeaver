"""Story prompt templates for multi-genre generation."""

from __future__ import annotations

from copy import deepcopy
import hashlib


DEFAULT_STORY_TEMPLATE_KEY = "zhihu_realistic"
DEFAULT_STORY_TEMPLATE_STRATEGY = "fixed"

_SUSPENSE_SIGNALS = (
    "悬疑", "惊悚", "灵异", "鬼故事", "推理", "诡异", "闹鬼", "失踪",
    "死亡通知", "凶案", "命案", "密室", "监控异常", "身份错位", "恐怖故事",
)


STORY_TEMPLATE_STRATEGIES: dict[str, dict[str, str]] = {
    "fixed": {
        "label": "固定模版",
        "description": "始终使用当前选中的模版，风格最稳定。",
    },
    "rotate": {
        "label": "轮换模版",
        "description": "每轮创作按顺序轮换到相邻模版，提升题材覆盖。",
    },
    "shuffle": {
        "label": "随机模版",
        "description": "每轮根据主题随机选择模版，差异最大。",
    },
}


STORY_TEMPLATES: dict[str, dict] = {
    "zhihu_realistic": {
        "label": "知乎现实故事",
        "description": "现实感、情绪张力、观点回扣，适合知乎回答体叙事。",
        "outline_focus": "围绕现实处境和价值冲突设计章节推进。",
        "outline_rules": [
            "冲突要贴近日常，避免玄幻化设定。",
            "每章标题要能看出关系变化或认知转折。",
            "章节顺序体现因果，不要只堆事件。",
        ],
        "story_focus": "语言自然、细节真实、情绪渐进，结尾有可传播观点。",
        "story_rules": [
            "前150字抛出矛盾或异常信息。",
            "每3-5段推动一次关键变化。",
            "结尾回扣开头并给出态度或反思。",
        ],
        "section_rules": [
            "本节至少出现一次关系变化或立场变化。",
            "本节结尾留下下一节问题钩子。",
        ],
        "outline_system_prompt": "你是擅长现实题材的中文编辑，请输出结构化目录，不要正文。",
        "story_system_prompt": "你是资深现实题材中文作者，重视细节、逻辑与情绪递进，避免空话。",
    },
    "urban_power": {
        "label": "都市逆袭爽文",
        "description": "快节奏、压迫开局、连续反转、爽点兑现。",
        "outline_focus": "设计主角从低位到高位的阶段性逆袭路径。",
        "outline_rules": [
            "前半段持续制造压制与阻碍，后半段逐层反击。",
            "每章都要有明确目标和结果，不要无效过渡。",
            "关键章节安排打脸或地位反转。",
        ],
        "story_focus": "节奏偏快，冲突密集，人物决策果断，爽点清晰可感。",
        "story_rules": [
            "开场100字给出主角困境和不公平处境。",
            "中段至少两次反转，且代价真实。",
            "结尾给出阶段胜利并抛出更大目标。",
        ],
        "section_rules": [
            "本节必须出现可感知的收益或损失。",
            "对抗场景要写清动作、话术与后果。",
            "进入高潮前主角必须至少遭遇一次实质失败：证据失效、盟友背刺、计划被截胡或被迫牺牲一个重要筹码，禁止一路顺风。",
        ],
        "outline_system_prompt": "你是擅长都市逆袭爽文的策划编辑，请先产出章节目录。",
        "story_system_prompt": "你是擅长都市爽文的中文作者，节奏紧凑、冲突清晰、反转有力，避免拖沓。",
    },
    "suspense_thriller": {
        "label": "悬疑惊悚",
        "description": "心理侵入、日常异化、认知不可靠，制造来自灵魂深处的不安。",
        "outline_focus": "围绕熟悉生活被悄悄改写来推进真相，保证每个异常都有心理代价和后续回收。",
        "outline_rules": [
            "至少设置1条外在线索和1条心理暗线：外线追查事实，暗线动摇主角对记忆、身份或亲密关系的信任。",
            "关键线索要来自日常细节的轻微错位，不要依赖手术刀、审讯室、废弃医院、血腥道具等套路化恐怖符号。",
            "高潮章节必须揭示核心异常为什么一直贴近主角生活，并让主角付出认知、关系或身份层面的代价。",
        ],
        "story_focus": "控制信息释放节奏，用熟悉事物异化、记忆不可靠和关系侵蚀制造后背发凉的恐惧。",
        "story_rules": [
            "开篇即出现一个小到可以被忽略、但越想越不对劲的日常异常。",
            "中段加入误导信息，但误导必须改变主角对某个亲密关系或自身记忆的判断。",
            "结尾解释关键因果，不留硬性逻辑漏洞，同时保留对日常生活的余悸。",
            "每个关键场景都必须让主角做出选择并承担后果；异常不能只负责吓人，必须改变人物关系或行动路线。",
            "全篇同时推进一条可验证的外在线索和一条心理暗线；每章最多保留一个主钩子和一个次钩子，避免连续堆叠灵异道具。",
            "核心谜底必须在结尾前明确，开放结尾只保留余味，不得用故弄玄虚替代因果解释。",
            "涉及监控、手机、报警、医疗或法律程序时，先保证现实细节自洽，再使用超自然效果。",
        ],
        "section_rules": [
            "本节新增至少一条有效线索或一条日常错位疑点，并让人物因此怀疑自己的判断。",
            "对话中包含潜台词，不直接把谜底说透；恐惧优先来自关系、记忆和证据互相冲突。",
            "禁止用手术刀、审讯室、血浆、白大褂、地下室囚禁等道具替代真正的心理压迫，除非用户明确要求。",
            "本节只能有一个主钩子和一个次钩子；每个钩子都要在后续给出回收路径，不能靠新增谜语拖延。",
            "本节结尾前必须完成一次不可逆选择或关系变化，并明确它给下一节带来的具体代价。",
        ],
        "outline_system_prompt": "你是擅长心理惊悚和日常异化的中文编辑，请生成可执行的章节目录。",
        "story_system_prompt": "你是心理惊悚小说作者，擅长用熟悉生活的轻微错位制造深层恐惧，避免廉价血腥、道具恐怖和逻辑断裂。",
    },
    "xianxia_fantasy": {
        "label": "仙侠玄幻",
        "description": "世界观成长线、修炼体系、机缘冲突并进。",
        "outline_focus": "体现修炼进阶、势力博弈与道心变化。",
        "outline_rules": [
            "章节安排体现境界推进与资源争夺。",
            "关键战斗前要有动机铺垫与代价设定。",
            "角色成长不仅是战力提升，也有认知变化。",
        ],
        "story_focus": "兼顾奇观描写与规则自洽，避免纯数值堆砌。",
        "story_rules": [
            "开篇明确世界规则或修炼门槛。",
            "中段体现机缘与危机并存。",
            "结尾收束本阶段因果并延伸更大天道格局。",
        ],
        "section_rules": [
            "本节至少出现一个体系要素（功法/法器/阵法/势力规矩）。",
            "战斗场景写清策略，不只写强弱碾压。",
        ],
        "outline_system_prompt": "你是仙侠玄幻编辑，请生成层次分明的章节目录，不写正文。",
        "story_system_prompt": "你是仙侠玄幻作者，注重世界规则、势力关系与成长逻辑。",
    },
    "scifi_hard": {
        "label": "硬科幻",
        "description": "科技设定驱动剧情，理性推演与人性冲突并重。",
        "outline_focus": "以核心科学假设驱动情节升级与伦理抉择。",
        "outline_rules": [
            "核心设定必须可解释，不可随意超展开。",
            "每章推进“技术问题-决策-后果”链条。",
            "高潮章节体现技术风险与人性选择冲突。",
        ],
        "story_focus": "保持理性表达与紧张叙事平衡，避免科技术语堆砌。",
        "story_rules": [
            "开篇提出技术异常或系统危机。",
            "中段写出方案博弈与失败代价。",
            "结尾给出可验证的解决路径或开放式科学问题。",
        ],
        "section_rules": [
            "本节包含一个可执行决策及其副作用。",
            "技术描述服务剧情，不可脱离人物行动。",
        ],
        "outline_system_prompt": "你是硬科幻策划编辑，请输出逻辑严谨的章节目录。",
        "story_system_prompt": "你是硬科幻作者，擅长技术推演与伦理冲突，避免玄学化叙事。",
    },
    "light_comedy": {
        "label": "轻喜剧",
        "description": "轻快节奏、人物反差、笑点与温情并行。",
        "outline_focus": "通过人物关系错位和目标冲突制造喜剧情境。",
        "outline_rules": [
            "每章设置一个核心笑点场景。",
            "笑点来自人物性格与情境，不靠低俗梗。",
            "结局保持温暖收束，避免突兀沉重。",
        ],
        "story_focus": "对话驱动，节奏明快，笑中带情感回落。",
        "story_rules": [
            "开篇快速建立人物反差。",
            "中段升级误会或错位冲突。",
            "结尾完成情绪回收，给读者轻松满足感。",
        ],
        "section_rules": [
            "本节至少一处有效笑点和一处情感推进。",
            "台词口语化，避免解释性独白过多。",
        ],
        "outline_system_prompt": "你是轻喜剧编剧编辑，请先输出章节目录，不写正文。",
        "story_system_prompt": "你是轻喜剧作者，擅长人物反差和节奏笑点，保持轻松但不低幼。",
    },
}


def get_story_template(template_key: str | None) -> dict:
    key = str(template_key or "").strip()
    if key in STORY_TEMPLATES:
        profile = deepcopy(STORY_TEMPLATES[key])
        profile["key"] = key
        return profile
    profile = deepcopy(STORY_TEMPLATES[DEFAULT_STORY_TEMPLATE_KEY])
    profile["key"] = DEFAULT_STORY_TEMPLATE_KEY
    return profile


def list_story_templates() -> list[dict]:
    items: list[dict] = []
    for key, value in STORY_TEMPLATES.items():
        row = {
            "key": key,
            "label": value.get("label", key),
            "description": value.get("description", ""),
        }
        items.append(row)
    return items


def normalize_story_template_strategy(raw: str | None) -> str:
    key = str(raw or "").strip().lower()
    if key in STORY_TEMPLATE_STRATEGIES:
        return key
    return DEFAULT_STORY_TEMPLATE_STRATEGY


def list_story_template_strategies() -> list[dict]:
    rows: list[dict] = []
    for key, value in STORY_TEMPLATE_STRATEGIES.items():
        rows.append(
            {
                "key": key,
                "label": value.get("label", key),
                "description": value.get("description", ""),
            }
        )
    return rows


def _pick_index(size: int, seed: str) -> int:
    if size <= 0:
        return 0
    digest = hashlib.sha256(seed.encode("utf-8")).digest()
    return int.from_bytes(digest[:4], "big") % size


def resolve_story_template(
    template_key: str | None,
    strategy: str | None = None,
    *,
    nonce: str = "",
    requirement: str = "",
    category: str = "",
) -> dict:
    strategy_key = normalize_story_template_strategy(strategy)
    base_profile = get_story_template(template_key)
    base_key = str(base_profile.get("key", DEFAULT_STORY_TEMPLATE_KEY)).strip() or DEFAULT_STORY_TEMPLATE_KEY

    # The default Zhihu-realistic profile is intentionally adaptive: a user can
    # leave the default selected and still get suspense-specific constraints
    # when the request clearly asks for mystery/horror. Explicitly selected
    # templates remain untouched.
    if base_key == DEFAULT_STORY_TEMPLATE_KEY:
        signal_text = f"{requirement or ''} {category or ''}"
        if any(signal in signal_text for signal in _SUSPENSE_SIGNALS):
            base_key = "suspense_thriller"

    all_keys = list(STORY_TEMPLATES.keys())
    if not all_keys:
        return base_profile

    if base_key not in all_keys:
        base_key = DEFAULT_STORY_TEMPLATE_KEY if DEFAULT_STORY_TEMPLATE_KEY in all_keys else all_keys[0]

    if strategy_key == "fixed" or len(all_keys) <= 1:
        profile = get_story_template(base_key)
        profile["base_key"] = base_key
        profile["resolved_key"] = base_key
        profile["strategy"] = strategy_key
        return profile

    seed = f"{nonce}|{requirement}|{category}|{base_key}|{strategy_key}"
    if strategy_key == "rotate":
        base_idx = all_keys.index(base_key)
        offset = _pick_index(len(all_keys), seed + "|offset")
        resolved_key = all_keys[(base_idx + offset) % len(all_keys)]
    else:
        resolved_key = all_keys[_pick_index(len(all_keys), seed + "|shuffle")]
        if resolved_key == base_key and len(all_keys) > 1:
            resolved_key = all_keys[(all_keys.index(resolved_key) + 1) % len(all_keys)]

    profile = get_story_template(resolved_key)
    profile["base_key"] = base_key
    profile["resolved_key"] = resolved_key
    profile["strategy"] = strategy_key
    return profile

"""Config-driven profile for story review/polish/memory/emotion prompts."""

from __future__ import annotations

from copy import deepcopy
import json
import os
from pathlib import Path
from typing import Any


DEFAULT_STORY_PIPELINE_PROFILE: dict[str, Any] = {
    "emotion_arc": {
        "story_lines": [
            "主角情绪至少经历三段变化（压抑/犹豫→爆发/决断→余震/代价），每段要有事件触发；",
            "情绪强度必须随剧情压力递增，不允许中段回到平稳叙述；每次短暂缓和都必须立刻引出更大危机；",
            "至少出现三次情绪高点：第一次被迫反击，第二次发现反击失败或真相更坏，第三次在最坏处境中做不可逆选择；",
            "关键情绪通过动作、停顿、对话细节体现，不直接喊口号；",
            "高潮必须体现选择成本，且成本必须改变人物关系、身份处境或后续选择空间；",
            "结尾保留情绪余波而非说教总结，余波中必须带有代价感或未完全消散的威胁。",
        ],
        "section_lines": [
            "本节要明确情绪起点与终点，至少发生一次可感知的情绪位移；",
            "本节情绪终点必须比起点更紧、更痛或更决绝，禁止以彻底安心、释然、圆满作为章节落点；",
            "本节至少一次情绪高点必须由具体事件触发，而不是由内心独白硬拔高；",
            "用微动作和场景细节承载情绪变化，避免直接解释“他很痛苦/她很感动”；",
            "章节结尾留一个情绪钩子，驱动下一章；该钩子必须让主角下一章无法按原计划行动。",
        ],
    },
    "quality_review": {
        "dimensions": [
            {"key": "realism", "label": "真实感"},
            {"key": "detail", "label": "细节密度"},
            {"key": "coherence", "label": "逻辑连贯"},
            {"key": "continuity", "label": "跨章衔接"},
            {"key": "escalation", "label": "高潮升级"},
            {"key": "hook_density", "label": "钩子密度"},
            {"key": "naturalness", "label": "语言自然度"},
        ],
        "json_schema": (
            "{\"scores\":{\"realism\":0,\"detail\":0,\"coherence\":0,\"continuity\":0,\"escalation\":0,\"hook_density\":0,\"naturalness\":0},"
            "\"strengths\":[\"\"],\"issues\":[\"\"],\"key_fix\":\"\"}"
        ),
        "rules": [
            "若章节没有明确危机升级、不可逆事件或新钩子，escalation/hook_density 必须低于7；",
            "若开头前两句话或前两段没有异常信息、危险信号、关系爆雷、具体悬念或即时压力，hook_density 必须低于6.5；",
            "若章节只是在解释、铺垫、回忆或平稳过渡，必须指出为核心问题；",
            "若存在前后事实、人物动机、钩子回收冲突，continuity/coherence 必须低于7；",
            "issues 至少给1条且可执行；",
            "key_fix 20字以内；",
            "禁止输出 JSON 以外内容。",
        ],
    },
    "polish": {
        "fallback_fix": "高潮密度不足或逻辑衔接弱",
        "rules": [
            "保留原剧情顺序与关键事件，不新增大剧情；",
            "优先修复：{fix_goal}；",
            "检查并修复跨章衔接：本章开头应承接上章尾句后的动作/情绪，避免重复叙述；",
            "若提供“连贯性资料”，优先修复与历史设定冲突的称谓/地点/关系，不得自相矛盾；",
            "增强危机升级：把平稳过渡改成具体阻力、失败后果、关系破裂、秘密揭露或不可逆选择；",
            "补足钩子接力：回收上一章至少一个未解问题，并在结尾制造更强的新问题；",
            "若开头平淡，必须重写前两句话或前两段：直接切入异常、危险、关系爆雷、证据出现或不可逆后果，禁止天气/背景/履历开场；",
            "若原文缺少高潮，请在不改主线事实的前提下把关键场景改为“目标受阻→反击失败/成功有代价→新威胁出现”；",
            "不得为了刺激而制造逻辑跳跃；新增反转必须能从前文细节、人物动机或已知规则推导出来；",
            "增加可感知细节（动作/环境/心理），减少空泛评价句；",
            "语言自然克制，禁止模板腔（如：首先/其次/最后/总的来说）；",
            "字数控制在 {target_low}-{target_high} 字附近（当前约{current_chars}字）；",
            "只输出最终章节正文，不要解释。",
        ],
    },
    "plot_contract": {
        "rules": [
            "把本章当成一个可拍摄的剧情任务，而不是散文段落；",
            "本章必须围绕一个清晰目标推进：人物想得到/阻止/证明/隐瞒什么；",
            "至少安排3个连续场景，每个场景都必须产生新信息、新阻力或新代价；",
            "场景之间必须是因果推进：上一场的结果直接造成下一场的困难；",
            "每章必须先处理上一章留下的一个具体钩子，再抛出更高风险的新钩子；",
            "不可逆事件必须落到事实变化：证据损毁、关系破裂、身份暴露、选择空间缩小或代价兑现；",
            "禁止用解释、回忆、情绪反复和背景介绍填充字数；若需要交代信息，必须通过行动/对话/冲突透露；",
            "结尾不能恢复平静，必须留下一个会改变下一章行动方案的压力。",
        ],
    },
    "structure_rewrite": {
        "fallback_fix": "本章缺少强事件、因果推进或章末钩子",
        "rules": [
            "这是结构性重写，不是普通润色；允许重排场景、压缩解释段、强化冲突和改写开头/结尾；",
            "必须保留：人物姓名、已发生事实、核心设定、上章衔接点和本章不可逆事件承诺；",
            "必须补足：明确目标、具体阻力、至少一次反转或失败、可见代价、章末新钩子；",
            "把空泛心理、总结性说明、重复解释改成动作、对话、证据、选择和后果；",
            "每3-5段必须出现一次剧情推进，不允许连续两段只解释或抒情；",
            "若原文没有完成本章剧情任务，必须改写到完成，而不是只把句子写漂亮；",
            "开头必须紧接上章尾句后的动作/情绪；结尾必须制造下一章必须处理的新压力；",
            "字数控制在 {target_low}-{target_high} 字附近（当前约{current_chars}字）；",
            "只输出重写后的章节正文，不要解释。",
        ],
    },
    "transition": {
        "section_lines": [
            "中间章节开头必须承接上一章末尾动作或情绪，不得复制上一章原句；",
            "首段最多1句背景回顾，核心篇幅用于推进新事件；",
            "本章必须处理上一章留下的未解钩子，不能假装上一章危机不存在；",
            "新危机必须由上一章事件自然引出，禁止空降新设定、新人物或无因反转；",
            "章节压力必须接力升级：上一章造成的后果必须在本章变成更具体、更难解决的问题；",
            "人物立场、关系变化、已揭示事实必须与记忆账本一致，禁止反向改设定。",
        ],
    },
    "memory_ledger": {
        "json_schema": (
            "{\"summary\":\"\",\"plot_points\":[\"\"],\"relation_changes\":[\"\"],"
            "\"unresolved_hooks\":[\"\"],\"state_shift\":\"\","
            "\"character_states\":[\"\"],\"timeline_events\":[\"\"],\"open_threads\":[\"\"]}"
        ),
        "rules": [
            "summary 40-120字；",
            "plot_points 最多4条，聚焦事实事件；",
            "relation_changes 最多3条，写清人物关系变化；",
            "unresolved_hooks 最多3条，写未回收问题；",
            "unresolved_hooks 必须记录会影响下一章行动的具体威胁/谜团，不能写泛泛的情绪悬念；",
            "plot_points 必须包含本章不可逆事件或关键代价，若没有则写明“本章缺少不可逆事件”；",
            "state_shift 30字以内；",
            "character_states 最多5条，格式为“人物：当前立场/知道的信息/身体或情绪状态/行动限制”；",
            "timeline_events 最多5条，按发生顺序记录本章关键时间点、地点变化或因果后果；",
            "open_threads 最多5条，记录仍会影响后文的任务、承诺、威胁、证据、倒计时或待回收伏笔；",
            "禁止输出 JSON 以外内容。",
        ],
    },
}


_STORY_PIPELINE_PROFILE_CACHE: dict[str, Any] | None = None
_STORY_PIPELINE_PROFILE_CACHE_KEY: tuple[str, float] | None = None


def _resolve_profile_file() -> Path:
    raw = (os.getenv("STORY_PIPELINE_PROFILE_FILE", "") or "").strip()
    if raw:
        return Path(raw).expanduser()
    return Path.cwd() / "config" / "story_pipeline_profile.json"


def _normalize_text_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    out: list[str] = []
    for item in value:
        text = str(item or "").strip()
        if text:
            out.append(text)
    return out


def _normalize_dimensions(value: Any) -> list[dict[str, str]]:
    if not isinstance(value, list):
        return []
    rows: list[dict[str, str]] = []
    for item in value:
        if isinstance(item, dict):
            key = str(item.get("key", "") or "").strip()
            label = str(item.get("label", "") or "").strip()
            if key and label:
                rows.append({"key": key, "label": label})
        elif isinstance(item, (list, tuple)) and len(item) >= 2:
            key = str(item[0] or "").strip()
            label = str(item[1] or "").strip()
            if key and label:
                rows.append({"key": key, "label": label})
    return rows


def _ensure_quality_dimensions(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    """Ensure core quality dimensions are always present, even with custom profile overrides."""
    merged: list[dict[str, str]] = []
    seen: set[str] = set()
    for row in rows:
        key = str(row.get("key", "") or "").strip()
        label = str(row.get("label", "") or "").strip()
        if not key or not label or key in seen:
            continue
        merged.append({"key": key, "label": label})
        seen.add(key)

    default_dims = _normalize_dimensions(DEFAULT_STORY_PIPELINE_PROFILE["quality_review"]["dimensions"])
    for row in default_dims:
        key = row["key"]
        if key in seen:
            continue
        merged.append({"key": key, "label": row["label"]})
        seen.add(key)
    return merged


def _ensure_memory_ledger_defaults(cfg: dict[str, Any]) -> None:
    """Keep custom memory profiles compatible with newer continuity fields."""
    memory_cfg = cfg.get("memory_ledger", {})
    if not isinstance(memory_cfg, dict):
        return
    schema = str(memory_cfg.get("json_schema", "") or "").strip()
    required_keys = ("character_states", "timeline_events", "open_threads")
    if any(key not in schema for key in required_keys):
        memory_cfg["json_schema"] = str(DEFAULT_STORY_PIPELINE_PROFILE["memory_ledger"]["json_schema"])

    existing_rules = _normalize_text_list(memory_cfg.get("rules"))
    default_rules = _normalize_text_list(DEFAULT_STORY_PIPELINE_PROFILE["memory_ledger"]["rules"])
    for default_rule in default_rules:
        head = default_rule.split(" ", 1)[0]
        if default_rule in existing_rules:
            continue
        if head and any(str(rule).startswith(head) for rule in existing_rules):
            continue
        existing_rules.append(default_rule)
    memory_cfg["rules"] = existing_rules


def _merge_section_list(cfg: dict[str, Any], payload: dict[str, Any], section: str, key: str) -> None:
    section_payload = payload.get(section, {})
    if not isinstance(section_payload, dict):
        return
    lines = _normalize_text_list(section_payload.get(key))
    if lines:
        cfg[section][key] = lines


def _load_profile() -> dict[str, Any]:
    cfg = deepcopy(DEFAULT_STORY_PIPELINE_PROFILE)
    path = _resolve_profile_file()
    if not path.exists():
        return cfg
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return cfg
    if not isinstance(payload, dict):
        return cfg

    _merge_section_list(cfg, payload, "emotion_arc", "story_lines")
    _merge_section_list(cfg, payload, "emotion_arc", "section_lines")
    _merge_section_list(cfg, payload, "transition", "section_lines")
    _merge_section_list(cfg, payload, "quality_review", "rules")
    _merge_section_list(cfg, payload, "polish", "rules")
    _merge_section_list(cfg, payload, "plot_contract", "rules")
    _merge_section_list(cfg, payload, "structure_rewrite", "rules")
    _merge_section_list(cfg, payload, "memory_ledger", "rules")

    quality_raw = payload.get("quality_review", {})
    if isinstance(quality_raw, dict):
        dims = _normalize_dimensions(quality_raw.get("dimensions"))
        if dims:
            cfg["quality_review"]["dimensions"] = dims
        schema = str(quality_raw.get("json_schema", "") or "").strip()
        if schema:
            cfg["quality_review"]["json_schema"] = schema

    polish_raw = payload.get("polish", {})
    if isinstance(polish_raw, dict):
        fallback_fix = str(polish_raw.get("fallback_fix", "") or "").strip()
        if fallback_fix:
            cfg["polish"]["fallback_fix"] = fallback_fix

    rewrite_raw = payload.get("structure_rewrite", {})
    if isinstance(rewrite_raw, dict):
        fallback_fix = str(rewrite_raw.get("fallback_fix", "") or "").strip()
        if fallback_fix:
            cfg["structure_rewrite"]["fallback_fix"] = fallback_fix

    memory_raw = payload.get("memory_ledger", {})
    if isinstance(memory_raw, dict):
        schema = str(memory_raw.get("json_schema", "") or "").strip()
        if schema:
            cfg["memory_ledger"]["json_schema"] = schema
    _ensure_memory_ledger_defaults(cfg)

    return cfg


def reload_story_pipeline_profile() -> None:
    """Clear cache so next call reloads profile from disk."""
    global _STORY_PIPELINE_PROFILE_CACHE, _STORY_PIPELINE_PROFILE_CACHE_KEY
    _STORY_PIPELINE_PROFILE_CACHE = None
    _STORY_PIPELINE_PROFILE_CACHE_KEY = None


def get_story_pipeline_profile() -> dict[str, Any]:
    """Return merged profile from defaults + optional JSON override."""
    global _STORY_PIPELINE_PROFILE_CACHE, _STORY_PIPELINE_PROFILE_CACHE_KEY
    path = _resolve_profile_file()
    path_key = str(path.resolve())
    mtime = -1.0
    if path.exists():
        try:
            mtime = float(path.stat().st_mtime)
        except Exception:
            mtime = -1.0
    key = (path_key, mtime)
    if _STORY_PIPELINE_PROFILE_CACHE is not None and _STORY_PIPELINE_PROFILE_CACHE_KEY == key:
        return _STORY_PIPELINE_PROFILE_CACHE
    _STORY_PIPELINE_PROFILE_CACHE = _load_profile()
    _STORY_PIPELINE_PROFILE_CACHE_KEY = key
    return _STORY_PIPELINE_PROFILE_CACHE


def _format_lines(lines: list[str], *, numbered: bool = False) -> str:
    out: list[str] = []
    for idx, line in enumerate(lines, start=1):
        text = str(line or "").strip()
        if not text:
            continue
        if numbered:
            out.append(f"{idx}) {text}")
        else:
            if not text.startswith("- "):
                text = "- " + text
            out.append(text)
    return "\n".join(out).strip()


def build_emotion_arc_guidelines(stage: str = "story") -> str:
    cfg = get_story_pipeline_profile()
    emotion_cfg = cfg.get("emotion_arc", {})
    if not isinstance(emotion_cfg, dict):
        emotion_cfg = {}
    key = "section_lines" if stage == "section" else "story_lines"
    lines = _normalize_text_list(emotion_cfg.get(key))
    if not lines:
        lines = _normalize_text_list(DEFAULT_STORY_PIPELINE_PROFILE["emotion_arc"][key])
    return _format_lines(lines, numbered=False)


def build_section_transition_guidelines() -> str:
    cfg = get_story_pipeline_profile()
    transition_cfg = cfg.get("transition", {})
    if not isinstance(transition_cfg, dict):
        transition_cfg = {}
    lines = _normalize_text_list(transition_cfg.get("section_lines"))
    if not lines:
        lines = _normalize_text_list(DEFAULT_STORY_PIPELINE_PROFILE["transition"]["section_lines"])
    return _format_lines(lines, numbered=False)


def build_plot_contract_guidelines() -> str:
    """Return hard scene/causality rules for chapter drafting."""
    cfg = get_story_pipeline_profile()
    contract_cfg = cfg.get("plot_contract", {})
    if not isinstance(contract_cfg, dict):
        contract_cfg = {}
    lines = _normalize_text_list(contract_cfg.get("rules"))
    if not lines:
        lines = _normalize_text_list(DEFAULT_STORY_PIPELINE_PROFILE["plot_contract"]["rules"])
    return _format_lines(lines, numbered=True)


def build_quality_review_prompt(
    *,
    requirement: str,
    category: str,
    section_title: str,
    preview: str,
    continuity_contract: str = "",
    scene_card_contract: str = "",
) -> str:
    cfg = get_story_pipeline_profile()
    quality_cfg = cfg.get("quality_review", {})
    if not isinstance(quality_cfg, dict):
        quality_cfg = {}

    dimensions = _normalize_dimensions(quality_cfg.get("dimensions"))
    if not dimensions:
        dimensions = _normalize_dimensions(DEFAULT_STORY_PIPELINE_PROFILE["quality_review"]["dimensions"])
    dimensions = _ensure_quality_dimensions(dimensions)
    dims_text = ", ".join(f"{row['key']}({row['label']})" for row in dimensions)

    schema = str(quality_cfg.get("json_schema", "") or "").strip()
    if not schema:
        schema = str(DEFAULT_STORY_PIPELINE_PROFILE["quality_review"]["json_schema"])

    rules = _normalize_text_list(quality_cfg.get("rules"))
    if not rules:
        rules = _normalize_text_list(DEFAULT_STORY_PIPELINE_PROFILE["quality_review"]["rules"])
    rules_text = _format_lines(rules, numbered=True)
    contract = str(continuity_contract or "").strip()
    contract_block = ""
    if contract:
        contract_block = (
            "【故事状态合同（用于检查连续性）】\n"
            f"{contract}\n"
            "- 若章节文本违背以上事实、人物关系、时间线或未回收钩子，continuity/coherence 必须低于7，并在 issues 指明冲突点。\n\n"
        )
    scene_card = str(scene_card_contract or "").strip()
    scene_card_block = ""
    if scene_card:
        scene_card_block = (
            "【本章场景执行卡（用于检查兑现度）】\n"
            f"{scene_card}\n"
            "- 若章节文本没有兑现【本章目标】、【场景链】、【反转或失败】、【不可逆代价】或【新钩子】，escalation/hook_density/coherence 必须低于7，并在 issues 指明缺失项。\n"
            "- 若正文输出的事件顺序与执行卡因果链相反或跳过关键阻力，coherence 必须低于7。\n\n"
        )

    return (
        "你是严格的中文小说编辑，请评估以下章节文本质量，并仅返回 JSON。\n"
        f"评分维度（1-10）：{dims_text}。\n"
        "返回格式：\n"
        f"{schema}\n"
        "要求：\n"
        f"{rules_text}\n\n"
        f"{contract_block}"
        f"{scene_card_block}"
        f"主题：{requirement}\n"
        f"题材：{category}\n"
        f"章节标题：{section_title}\n"
        f"章节文本：\n{preview}\n"
    )


def build_polish_prompt(
    *,
    section_title: str,
    section_content: str,
    fix_goal: str,
    target_low: int,
    target_high: int,
    current_chars: int,
    previous_tail: str = "",
    continuity_context: str = "",
) -> str:
    cfg = get_story_pipeline_profile()
    polish_cfg = cfg.get("polish", {})
    if not isinstance(polish_cfg, dict):
        polish_cfg = {}

    rules = _normalize_text_list(polish_cfg.get("rules"))
    if not rules:
        rules = _normalize_text_list(DEFAULT_STORY_PIPELINE_PROFILE["polish"]["rules"])
    lines: list[str] = []
    for line in rules:
        text = line.replace("{fix_goal}", fix_goal)
        text = text.replace("{target_low}", str(target_low))
        text = text.replace("{target_high}", str(target_high))
        text = text.replace("{current_chars}", str(current_chars))
        lines.append(text)
    rules_text = _format_lines(lines, numbered=True)

    continuity_lines: list[str] = []
    tail = str(previous_tail or "").strip()
    if tail:
        continuity_lines.append(f"- 上章收束句：{tail}")
    continuity = str(continuity_context or "").strip()
    if continuity:
        continuity_lines.append(continuity)
    continuity_block = ""
    if continuity_lines:
        continuity_block = (
            "【连贯性资料（必须遵守）】\n"
            + "\n".join(continuity_lines)
            + "\n\n"
        )

    return (
        "你是中文小说精修编辑。请在不改变剧情事实和人物设定的前提下，"
        "对下面章节做一次“真实细腻化”重写。\n"
        "硬性要求：\n"
        f"{rules_text}\n\n"
        f"{continuity_block}"
        f"章节标题：{section_title}\n"
        f"原文：\n{section_content}\n"
    )


def get_polish_fallback_fix() -> str:
    cfg = get_story_pipeline_profile()
    polish_cfg = cfg.get("polish", {})
    if not isinstance(polish_cfg, dict):
        polish_cfg = {}
    fallback = str(polish_cfg.get("fallback_fix", "") or "").strip()
    if fallback:
        return fallback
    return str(DEFAULT_STORY_PIPELINE_PROFILE["polish"]["fallback_fix"])


def build_structure_rewrite_prompt(
    *,
    section_title: str,
    section_content: str,
    fix_goal: str,
    target_low: int,
    target_high: int,
    current_chars: int,
    previous_tail: str = "",
    continuity_context: str = "",
    section_overview_plan: str = "",
    event_promise: str = "",
) -> str:
    cfg = get_story_pipeline_profile()
    rewrite_cfg = cfg.get("structure_rewrite", {})
    if not isinstance(rewrite_cfg, dict):
        rewrite_cfg = {}

    rules = _normalize_text_list(rewrite_cfg.get("rules"))
    if not rules:
        rules = _normalize_text_list(DEFAULT_STORY_PIPELINE_PROFILE["structure_rewrite"]["rules"])
    lines: list[str] = []
    for line in rules:
        text = line.replace("{fix_goal}", fix_goal)
        text = text.replace("{target_low}", str(target_low))
        text = text.replace("{target_high}", str(target_high))
        text = text.replace("{current_chars}", str(current_chars))
        lines.append(text)
    rules_text = _format_lines(lines, numbered=True)

    context_lines: list[str] = []
    tail = str(previous_tail or "").strip()
    if tail:
        context_lines.append(f"- 上章收束句：{tail}")
    continuity = str(continuity_context or "").strip()
    if continuity:
        context_lines.append(continuity)
    overview = str(section_overview_plan or "").strip()
    if overview:
        context_lines.append("【本章剧情任务书】\n" + overview)
    promise = str(event_promise or "").strip()
    if promise:
        context_lines.append(f"- 本章不可逆事件承诺：{promise}")
    context_block = ""
    if context_lines:
        context_block = "【必须遵守的剧情资料】\n" + "\n".join(context_lines) + "\n\n"

    return (
        "你是资深中文小说结构编辑。下面章节存在结构问题，请做一次“剧情重构版”重写。\n"
        f"重构目标：{fix_goal or get_structure_rewrite_fallback_fix()}\n"
        "硬性要求：\n"
        f"{rules_text}\n\n"
        f"{context_block}"
        f"章节标题：{section_title}\n"
        f"原文：\n{section_content}\n"
    )


def get_structure_rewrite_fallback_fix() -> str:
    cfg = get_story_pipeline_profile()
    rewrite_cfg = cfg.get("structure_rewrite", {})
    if not isinstance(rewrite_cfg, dict):
        rewrite_cfg = {}
    fallback = str(rewrite_cfg.get("fallback_fix", "") or "").strip()
    if fallback:
        return fallback
    return str(DEFAULT_STORY_PIPELINE_PROFILE["structure_rewrite"]["fallback_fix"])


def build_memory_ledger_prompt(*, section_title: str, preview: str) -> str:
    cfg = get_story_pipeline_profile()
    memory_cfg = cfg.get("memory_ledger", {})
    if not isinstance(memory_cfg, dict):
        memory_cfg = {}

    schema = str(memory_cfg.get("json_schema", "") or "").strip()
    if not schema:
        schema = str(DEFAULT_STORY_PIPELINE_PROFILE["memory_ledger"]["json_schema"])
    rules = _normalize_text_list(memory_cfg.get("rules"))
    if not rules:
        rules = _normalize_text_list(DEFAULT_STORY_PIPELINE_PROFILE["memory_ledger"]["rules"])
    rules_text = _format_lines(rules, numbered=True)

    return (
        "你是小说连续性编辑。请从以下章节提取“记忆账本”，并仅返回 JSON：\n"
        f"{schema}\n"
        "要求：\n"
        f"{rules_text}\n\n"
        f"章节标题：{section_title}\n"
        f"章节文本：\n{preview}\n"
    )

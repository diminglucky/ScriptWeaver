"""Creativity engine for story prompts."""

from __future__ import annotations

import hashlib
import time


DEFAULT_STORY_CREATIVITY_MODE = "blend"


STORY_CREATIVITY_MODES: dict[str, dict[str, str]] = {
    "stable": {
        "label": "稳健（高一致）",
        "description": "优先保持风格一致和结构稳定，适合复刻已验证风格。",
    },
    "blend": {
        "label": "融合（跨类型）",
        "description": "在主类型基础上混入副类型元素，提升新鲜感且风险可控。",
    },
    "wild": {
        "label": "实验（高多样）",
        "description": "强制引入结构扰动与叙事变化，追求明显差异化。",
    },
}


def normalize_story_creativity_mode(raw: str | None) -> str:
    mode = str(raw or "").strip().lower()
    if mode in STORY_CREATIVITY_MODES:
        return mode
    return DEFAULT_STORY_CREATIVITY_MODE


def list_story_creativity_modes() -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for key, meta in STORY_CREATIVITY_MODES.items():
        rows.append(
            {
                "key": key,
                "label": meta.get("label", key),
                "description": meta.get("description", ""),
            }
        )
    return rows


def _pick(options: list[str], salt: str) -> str:
    if not options:
        return ""
    digest = hashlib.sha256(salt.encode("utf-8")).digest()
    idx = int.from_bytes(digest[:4], "big") % len(options)
    return options[idx]


def build_story_creativity_block(
    mode: str,
    *,
    requirement: str,
    category: str,
    style_hint: str = "",
    stage: str = "story",
    nonce: str = "",
    primary_template_key: str = "",
) -> str:
    mode_key = normalize_story_creativity_mode(mode)
    if mode_key == "stable":
        return ""

    # Use per-run nonce when provided; fallback to high-resolution timestamp.
    stamp = str(nonce or time.time_ns())
    core_seed = f"{stamp}|{requirement}|{category}|{style_hint}|{mode_key}"
    stage_seed = f"{core_seed}|{stage}"
    creative_signature = hashlib.sha1(core_seed.encode("utf-8")).hexdigest()[:8]

    secondary_genre = _pick(
        [
            "悬疑",
            "轻喜剧",
            "社会观察",
            "心理惊悚",
            "科幻设定",
            "成长蜕变",
            "都市权谋",
            "黑色幽默",
        ],
        core_seed + "|genre",
    )
    narrative_view = _pick(
        [
            "第一人称贴身叙事",
            "第三人称限知叙事",
            "双主角交替视角",
            "旁观者证词视角",
        ],
        core_seed + "|pov",
    )
    structure_hook = _pick(
        [
            "倒叙开局",
            "双时间线交错",
            "24小时倒计时推进",
            "伪结局后二次反转",
            "三段式反转阶梯",
        ],
        core_seed + "|structure",
    )
    language_tone = _pick(
        [
            "克制冷感",
            "辛辣讽刺",
            "温柔残酷并置",
            "短句冲击节奏",
        ],
        core_seed + "|tone",
    )

    lines = [
        f"- 创意签名：{creative_signature}",
        f"- 在主类型“{category}”中融合“{secondary_genre}”元素，不能喧宾夺主。",
        f"- 叙事视角采用：{narrative_view}。",
        f"- 结构扰动建议：{structure_hook}。",
        f"- 语言基调偏向：{language_tone}。",
    ]

    # Cross-template fusion: borrow one compatible rule from another template.
    try:
        from .story_templates import STORY_TEMPLATES

        candidates = [k for k in STORY_TEMPLATES.keys() if k != primary_template_key]
        fusion_key = _pick(candidates, core_seed + "|fusion_key")
        fusion_meta = STORY_TEMPLATES.get(fusion_key or "", {})
        fusion_label = str(fusion_meta.get("label", fusion_key or "副模版")).strip() or "副模版"

        outline_rules = [str(x).strip() for x in fusion_meta.get("outline_rules", []) if str(x).strip()]
        story_rules = [str(x).strip() for x in fusion_meta.get("story_rules", []) if str(x).strip()]
        section_rules = [str(x).strip() for x in fusion_meta.get("section_rules", []) if str(x).strip()]

        borrowed_outline = _pick(outline_rules, core_seed + "|fusion_outline")
        borrowed_story = _pick(story_rules, core_seed + "|fusion_story")
        borrowed_section = _pick(section_rules, core_seed + "|fusion_section")

        lines.append(f"- 跨模版融合：保持主模版基调，同时借入「{fusion_label}」的方法。")
        if stage == "outline" and borrowed_outline:
            lines.append(f"- 借入目录规则：{borrowed_outline}")
        elif stage == "section" and borrowed_section:
            lines.append(f"- 借入章节规则：{borrowed_section}")
        elif borrowed_story:
            lines.append(f"- 借入正文规则：{borrowed_story}")
    except Exception:
        # Creativity should never break generation flow.
        pass

    if mode_key == "wild":
        extra_pivot = _pick(
            [
                "在中段引入一次立场反转",
                "在高潮前加入一次价值抉择",
                "把关键真相延后到结尾前一段揭示",
                "安排一次看似胜利实则代价更大的假高潮",
            ],
            stage_seed + "|pivot",
        )
        lines.append(f"- 额外实验约束：{extra_pivot}。")
        lines.append("- 同一桥段不得重复表达，优先新动作、新信息、新关系变化。")

    if stage == "outline":
        lines.append("- 目录层面要显式体现上述结构扰动，不要只在正文阶段才体现。")
    elif stage == "section":
        lines.append("- 本节必须承担一次“信息增量”或“关系位移”，不能只承接不推进。")
    else:
        lines.append("- 正文每3-5段至少兑现一次冲突推进或认知反转。")

    return "\n".join(lines)

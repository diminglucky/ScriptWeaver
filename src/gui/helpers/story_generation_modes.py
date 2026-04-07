"""Story generation mode presets for speed/quality tradeoffs."""

from __future__ import annotations


DEFAULT_STORY_GENERATION_MODE = "balanced"


STORY_GENERATION_MODES: dict[str, dict[str, object]] = {
    "fast": {
        "label": "快速（低延迟）",
        "description": "关闭预览与评审，优先最快速度出稿。",
        "settings": {
            "story_quality_review_enabled": False,
            "story_global_overview_enabled": False,
            "story_overview_before_generate": False,
            "story_preview_before_apply": False,
            "story_outline_alignment_strict": False,
            "story_outline_alignment_max_attempts": 1,
        },
    },
    "balanced": {
        "label": "平衡（推荐）",
        "description": "开启核心一致性与预览流程，在质量和速度之间平衡。",
        "settings": {
            "story_quality_review_enabled": True,
            "story_global_overview_enabled": True,
            "story_overview_before_generate": True,
            "story_preview_before_apply": True,
            "story_outline_alignment_strict": True,
            "story_outline_alignment_max_attempts": 2,
            "story_quality_min_avg": 7.4,
            "story_quality_min_dim": 6.8,
        },
    },
    "strict": {
        "label": "严格（高质量）",
        "description": "强化目录对齐和质检门槛，生成更慢但一致性更高。",
        "settings": {
            "story_quality_review_enabled": True,
            "story_global_overview_enabled": True,
            "story_overview_before_generate": True,
            "story_preview_before_apply": True,
            "story_outline_alignment_strict": True,
            "story_outline_alignment_max_attempts": 4,
            "story_quality_min_avg": 7.8,
            "story_quality_min_dim": 7.2,
        },
    },
    "custom": {
        "label": "自定义",
        "description": "你已手动修改多个开关，不强制覆盖。",
        "settings": {},
    },
}


def normalize_story_generation_mode(raw: str | None) -> str:
    mode = str(raw or "").strip().lower()
    if mode in STORY_GENERATION_MODES:
        return mode
    return DEFAULT_STORY_GENERATION_MODE


def list_story_generation_modes() -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for key, meta in STORY_GENERATION_MODES.items():
        rows.append(
            {
                "key": key,
                "label": str(meta.get("label", key)),
                "description": str(meta.get("description", "")),
            }
        )
    return rows


def get_story_generation_mode_settings(mode: str | None) -> dict[str, object]:
    mode_key = normalize_story_generation_mode(mode)
    profile = STORY_GENERATION_MODES.get(mode_key, STORY_GENERATION_MODES[DEFAULT_STORY_GENERATION_MODE])
    settings = profile.get("settings", {})
    if isinstance(settings, dict):
        return dict(settings)
    return {}

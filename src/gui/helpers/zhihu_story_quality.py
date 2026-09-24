"""Deterministic quality checks for Zhihu-style suspense stories.

The model review remains useful for nuance, but these checks enforce the
observable mechanics that make high-engagement answers readable: a concrete
opening, evidence-led escalation, active choices, and short information-dense
paragraphs.
"""

from __future__ import annotations

import re
from typing import Any


_CONCRETE_ANCHOR_RE = re.compile(
    r"(?:短信|电话|来电|照片|相册|监控|录像|门锁|钥匙|病历|报告|录音|时间|凌晨|夜里|失踪|死亡|尸体|身份证|定位|电梯|邻居|警察)"
)
_SPECIFIC_EVIDENCE_RE = re.compile(
    r"(?:\d{1,2}[点时:：]\d{0,2}|凌晨|深夜|昨晚|今天|第\d+天|一条.{0,18}(?:短信|通知|来电)|"
    r"(?:照片|监控|录像|门锁|钥匙|病历|报告|录音|定位).{0,24}(?:显示|拍到|记录|写着|来自|指向|标记))"
)
_VERIFICATION_ACTION_RE = re.compile(
    r"(?:翻|查看|核对|确认|调取|打开|放大|拨|回拨|询问|追问|报警|报警|录下|拍下|定位|检查|比对|试探|敲门|查到|找到)"
)
_CHOICE_CONSEQUENCE_RE = re.compile(
    r"(?:决定|选择|不得不|只能|冒险|答应|拒绝|删掉|烧掉|交出|留下|逃走|报警|隐瞒|承认|失去|暴露|破裂|代价|后果|来不及)"
)
_ABSTRACT_FEAR_RE = re.compile(r"(?:毛骨悚然|恐怖|害怕|诡异|不安|发毛|细思极恐|说不出的恐惧)")


def inspect_zhihu_story_shape(
    text: str,
    *,
    require_opening: bool = True,
    require_ending: bool = False,
) -> dict[str, Any]:
    """Return local violations and conservative score deductions.

    This is intentionally a detector, not a prose judge. It never rejects a
    story by itself; it supplies concrete issues to the model review/polish
    stage and makes missing mechanics visible in diagnostics.
    """
    raw = str(text or "").replace("\r\n", "\n").strip()
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", raw) if p.strip()]
    opening = raw[:300]
    issues: list[str] = []
    deductions: dict[str, float] = {}
    gate_failures: list[str] = []
    observations: dict[str, Any] = {}

    opening_anchor = _CONCRETE_ANCHOR_RE.search(opening)
    opening_evidence = _SPECIFIC_EVIDENCE_RE.search(opening)
    observations["opening_anchor"] = opening_anchor.group(0) if opening_anchor else ""
    observations["opening_specific_evidence"] = opening_evidence.group(0) if opening_evidence else ""
    if require_opening and not opening_evidence:
        issues.append("开头缺少可验证的生活证据或具体时间点")
        gate_failures.append("opening_evidence")
        deductions.update(detail=1.8, hook_density=2.4)
    early_action = _VERIFICATION_ACTION_RE.search(raw[:900])
    observations["early_verification_action"] = early_action.group(0) if early_action else ""
    if require_opening and not early_action:
        issues.append("前段没有主角主动核对、追问或验证异常的动作")
        gate_failures.append("verification_action")
        deductions.update(coherence=1.5, escalation=1.8)
    choice = _CHOICE_CONSEQUENCE_RE.search(raw)
    observations["choice_consequence"] = choice.group(0) if choice else ""
    if not choice:
        issues.append("正文没有明确选择及其可见后果")
        gate_failures.append("choice_consequence")
        deductions.update(escalation=1.8, coherence=1.0)
    if len(paragraphs) >= 4:
        long_paragraphs = sum(1 for p in paragraphs if len(p) > 260)
        if long_paragraphs / len(paragraphs) > 0.55:
            issues.append("段落过长，信息和动作没有形成短段推进")
            deductions["naturalness"] = 0.7
    if raw and len(raw) >= 600:
        abstract_count = len(_ABSTRACT_FEAR_RE.findall(raw))
        if abstract_count >= 5 and not _VERIFICATION_ACTION_RE.search(raw):
            issues.append("抽象恐惧词过多，缺少证据和验证动作")
            gate_failures.append("abstract_fear_without_evidence")
            deductions.update(detail=1.2, naturalness=0.8)
    if require_ending and raw:
        first_anchor = _CONCRETE_ANCHOR_RE.search(raw[:300])
        if first_anchor and first_anchor.group(0) not in raw[-max(180, len(raw) // 4) :]:
            issues.append("结尾没有回扣开头的关键物件、时间点或证据")
            gate_failures.append("ending_callback")
            deductions.update(escalation=1.2, naturalness=0.8)

    observations["paragraph_count"] = len(paragraphs)
    observations["abstract_fear_count"] = len(_ABSTRACT_FEAR_RE.findall(raw))
    observations["gate_failures"] = gate_failures[:6]

    return {
        "passed": not issues,
        "issues": issues[:4],
        "deductions": deductions,
        "paragraph_count": len(paragraphs),
        "gate_failures": gate_failures[:6],
        "observations": observations,
    }


def merge_local_quality_report(review: dict[str, Any], local: dict[str, Any]) -> dict[str, Any]:
    """Apply local deductions without allowing them to erase model feedback."""
    if not isinstance(review, dict) or not isinstance(local, dict) or local.get("passed"):
        return review
    merged = dict(review)
    # Local checks are advisory signals. The AI verdict remains authoritative;
    # preserve the signal separately so the UI/polisher can inspect it.
    merged["quality_gate_passed"] = bool(local.get("passed", True))
    merged["local_quality_issues"] = list(local.get("issues", []) or [])[:4]
    scores = dict(review.get("scores", {}) or {})
    for key, deduction in dict(local.get("deductions", {}) or {}).items():
        try:
            scores[key] = max(1.0, min(10.0, float(scores.get(key, 7.0)) - float(deduction)))
        except (TypeError, ValueError):
            continue
    # Keep deductions deliberately small: these are clues for the AI review,
    # not a substitute for literary judgment.
    merged["scores"] = scores
    merged["avg_score"] = round(sum(float(scores.get(k, 7.0)) for k in scores) / max(1, len(scores)), 2)
    existing = [str(item).strip() for item in list(review.get("issues", []) or []) if str(item).strip()]
    local_issues = [str(item).strip() for item in list(local.get("issues", []) or []) if str(item).strip()]
    for issue in local_issues:
        if issue and issue not in existing:
            existing.append(str(issue))
    merged["issues"] = existing[:5]
    if not str(merged.get("key_fix", "") or "").strip():
        priority_issue = local_issues[0] if local_issues else (existing[0] if existing else "")
        if priority_issue:
            merged["key_fix"] = priority_issue[:20]
    return merged

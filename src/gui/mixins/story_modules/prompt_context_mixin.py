"""Story template/creativity/memory/RAG context helpers."""

from __future__ import annotations

import re
from pathlib import Path

from ...helpers.story_creativity import (
    DEFAULT_STORY_CREATIVITY_MODE,
    normalize_story_creativity_mode,
)
from ...helpers.story_quality import extract_last_sentence, format_memory_context
from ...helpers.story_templates import (
    get_story_template,
    list_story_template_strategies,
    resolve_story_template,
)


class StoryPromptContextMixin:
    """Context and diagnostic helpers used by story prompt builders."""
    def _get_story_template_profile(self, requirement: str = "", category: str = ""):
        key = ""
        if hasattr(self, "story_template_key"):
            try:
                key = (self.story_template_key.get() or "").strip()
            except Exception:
                key = ""
        strategy = self._get_story_template_strategy()
        return resolve_story_template(
            key,
            strategy,
            nonce=self._get_story_creativity_nonce(),
            requirement=requirement,
            category=category,
        )

    def _get_story_creativity_mode(self) -> str:
        mode = DEFAULT_STORY_CREATIVITY_MODE
        if hasattr(self, "story_creativity_mode"):
            try:
                mode = self.story_creativity_mode.get()
            except Exception:
                mode = DEFAULT_STORY_CREATIVITY_MODE
        return normalize_story_creativity_mode(mode)

    def _get_story_creativity_nonce(self) -> str:
        return str(getattr(self, "_story_creativity_nonce", "") or "").strip()

    def _get_story_memory_ledger(self) -> list[dict]:
        rows = getattr(self, "story_memory_ledger", [])
        if not isinstance(rows, list):
            return []
        return [x for x in rows if isinstance(x, dict)]

    def _get_story_memory_rows_before(self, section_index: int) -> list[dict]:
        try:
            idx = int(section_index)
        except Exception:
            idx = 0
        rows: list[dict] = []
        for row in self._get_story_memory_ledger():
            try:
                chapter_index = int(row.get("chapter_index", -1))
            except Exception:
                continue
            if chapter_index < idx:
                rows.append(row)
        return rows

    def _build_story_memory_context(self, section_index: int, max_items: int = 3) -> str:
        rows = self._get_story_memory_rows_before(section_index)
        if not rows:
            return ""
        return format_memory_context(rows, max_entries=max_items)

    def _build_compressed_story_state(self, section_index: int, previous_content: str = "") -> str:
        """Build a compact state brief so later chapters know what already happened."""
        state_contract = self._build_story_state_contract(section_index, previous_content)
        if state_contract:
            return state_contract

        # Legacy fallback for callers that only have raw previous content and no ledger yet.
        try:
            idx = int(section_index)
        except Exception:
            idx = 0
        rows = self._get_story_memory_rows_before(idx)
        lines: list[str] = []
        if rows:
            recent = rows[-min(5, len(rows)) :]
            facts: list[str] = []
            relations: list[str] = []
            hooks: list[str] = []
            shifts: list[str] = []
            for row in recent:
                title = str(row.get("chapter_title", "") or "").strip()
                prefix = f"《{title}》" if title else "上一章"
                summary = str(row.get("summary", "") or "").strip()
                if summary:
                    facts.append(f"{prefix}{summary[:90]}")
                for item in row.get("plot_points", []) if isinstance(row.get("plot_points", []), list) else []:
                    text = str(item or "").strip()
                    if text:
                        facts.append(text[:70])
                for item in row.get("relation_changes", []) if isinstance(row.get("relation_changes", []), list) else []:
                    text = str(item or "").strip()
                    if text:
                        relations.append(text[:70])
                for item in row.get("unresolved_hooks", []) if isinstance(row.get("unresolved_hooks", []), list) else []:
                    text = str(item or "").strip()
                    if text:
                        hooks.append(text[:80])
                shift = str(row.get("state_shift", "") or "").strip()
                if shift:
                    shifts.append(shift[:60])
            if facts:
                lines.append("【已发生事实（不得改写）】")
                lines.extend(f"- {x}" for x in facts[-8:])
            if relations:
                lines.append("【人物关系/立场现状】")
                lines.extend(f"- {x}" for x in relations[-5:])
            if hooks:
                lines.append("【未回收钩子（本章优先处理并升级）】")
                lines.extend(f"- {x}" for x in hooks[-5:])
            if shifts:
                lines.append("【主角当前状态】")
                lines.extend(f"- {x}" for x in shifts[-3:])
        tail = extract_last_sentence(previous_content or "", max_chars=260)
        if tail:
            lines.append("【最新收束句】")
            lines.append(f"- {tail}")
        if not lines:
            return ""
        lines.append("【压缩上下文使用规则】")
        lines.append("- 本章必须遵守以上事实、关系和未回收钩子，不得重置人物状态。")
        lines.append("- 本章必须至少回收一个旧钩子，并制造一个更高风险的新钩子。")
        return "\n".join(lines).strip()

    def _build_story_state_contract(self, section_index: int, previous_content: str = "") -> str:
        """Build hard continuity constraints from the memory ledger for current chapter."""
        try:
            idx = int(section_index)
        except Exception:
            idx = 0
        rows = self._get_story_memory_rows_before(idx)
        tail = extract_last_sentence(previous_content or "", max_chars=260)
        if not rows and not tail:
            return ""

        recent = rows[-min(6, len(rows)) :] if rows else []
        facts: list[str] = []
        relations: list[str] = []
        hooks: list[str] = []
        states: list[str] = []
        timeline: list[str] = []
        for row in recent:
            try:
                chapter_no = int(row.get("chapter_index", 0)) + 1
            except Exception:
                chapter_no = 0
            title = str(row.get("chapter_title", "") or "").strip()
            prefix = f"第{chapter_no}章《{title}》" if chapter_no else (f"《{title}》" if title else "前章")
            summary = str(row.get("summary", "") or "").strip()
            if summary:
                facts.append(f"{prefix}：{summary[:100]}")
                timeline.append(f"{prefix}后，相关后果仍然有效。")
            plot_points = row.get("plot_points", [])
            if isinstance(plot_points, list):
                for item in plot_points[:4]:
                    text = str(item or "").strip()
                    if text:
                        facts.append(f"{prefix}事实：{text[:90]}")
            relation_changes = row.get("relation_changes", [])
            if isinstance(relation_changes, list):
                for item in relation_changes[:3]:
                    text = str(item or "").strip()
                    if text:
                        relations.append(f"{prefix}关系：{text[:90]}")
            character_states = row.get("character_states", [])
            if isinstance(character_states, list):
                for item in character_states[:5]:
                    text = str(item or "").strip()
                    if text:
                        states.append(f"{prefix}人物：{text[:100]}")
            unresolved_hooks = row.get("unresolved_hooks", [])
            if isinstance(unresolved_hooks, list):
                for item in unresolved_hooks[:3]:
                    text = str(item or "").strip()
                    if text:
                        hooks.append(f"{prefix}未解：{text[:100]}")
            open_threads = row.get("open_threads", [])
            if isinstance(open_threads, list):
                for item in open_threads[:5]:
                    text = str(item or "").strip()
                    if text:
                        hooks.append(f"{prefix}待处理：{text[:100]}")
            timeline_events = row.get("timeline_events", [])
            if isinstance(timeline_events, list):
                for item in timeline_events[:5]:
                    text = str(item or "").strip()
                    if text:
                        timeline.append(f"{prefix}时间线：{text[:110]}")
            shift = str(row.get("state_shift", "") or "").strip()
            if shift:
                states.append(f"{prefix}状态：{shift[:80]}")

        lines: list[str] = []
        if tail:
            lines.append("【即时承接点】")
            lines.append(f"- 本章第一场必须接住：{tail}")
        if facts:
            lines.append("【事实锁定（不得改写/遗忘）】")
            lines.extend(f"- {x}" for x in facts[-10:])
        if relations:
            lines.append("【人物关系与立场锁定】")
            lines.extend(f"- {x}" for x in relations[-8:])
        if states:
            lines.append("【人物当前状态锁定】")
            lines.extend(f"- {x}" for x in states[-5:])
        if hooks:
            lines.append("【未回收钩子队列】")
            lines.extend(f"- {x}" for x in hooks[-8:])
        if timeline:
            lines.append("【时间线约束】")
            lines.extend(f"- {x}" for x in timeline[-4:])

        lines.append("【本章连续性硬规则】")
        lines.append("- 不得改写已发生事实，不得让关系/立场无因复原。")
        lines.append("- 本章至少处理一个未回收钩子；若暂不回收，必须让它造成新的阻力或代价。")
        lines.append("- 新反转必须从上述事实、人物状态或钩子中推出，禁止空降解释。")
        lines.append("- 章末新钩子必须改变下一章行动方案。")
        return "\n".join(lines).strip()

    def _build_story_skill_pack(self) -> str:
        """Return built-in writing skills used as a compact strategy pack."""
        return (
            "【写作 Skills（必须执行）】\n"
            "- 危机阶梯：每章用“目标受阻 → 反击 → 反击有代价/失败 → 新威胁”推进。\n"
            "- 钩子接力：每章先兑现上章一个钩子，再抛出更危险、更具体的新钩子。\n"
            "- 反转合法性：反转必须能从前文细节、人物动机或规则推出，禁止空降设定。\n"
            "- 场景压迫：高潮不靠喊口号，用时间限制、空间封闭、证据消失、关系背叛制造压力。\n"
            "- 不可逆代价：每章至少让主角失去信息优势、关系信任、安全位置或选择余地之一。\n"
            "- 逻辑锁链：任何新行动都必须回应上一章结果，不能跳过后果直接进入新事件。"
        )

    def _build_section_transition_context(self, section_index: int, previous_content: str) -> str:
        """Build compact cross-chapter continuity brief for current section."""
        try:
            idx = int(section_index)
        except Exception:
            idx = 0
        if idx <= 0:
            return ""

        lines: list[str] = []
        tail_sentence = extract_last_sentence(previous_content or "", max_chars=260)
        if tail_sentence:
            lines.append(f"- 上章收束句：{tail_sentence}")

        prev_rows = self._get_story_memory_rows_before(idx)
        if prev_rows:
            last = prev_rows[-1]
            summary = str(last.get("summary", "") or "").strip()
            if summary:
                lines.append(f"- 上章事件摘要：{summary[:90]}")
            relation = last.get("relation_changes", [])
            if isinstance(relation, list) and relation:
                relation_text = "；".join(str(x).strip() for x in relation[:2] if str(x).strip())
                if relation_text:
                    lines.append(f"- 当前关系状态：{relation_text}")
            hooks = last.get("unresolved_hooks", [])
            if isinstance(hooks, list) and hooks:
                hooks_text = "；".join(str(x).strip() for x in hooks[:2] if str(x).strip())
                if hooks_text:
                    lines.append(f"- 待延续伏笔：{hooks_text}")

        if lines:
            lines.append("- 首段必须承接上章结尾后的即时动作/情绪，不得复述原句。")
        return "\n".join(lines).strip()

    def _update_story_diagnostics_panel(self) -> None:
        if not hasattr(self, "story_quality_summary_var") or not hasattr(self, "story_memory_summary_var"):
            return

        quality_enabled = True
        if hasattr(self, "story_quality_review_enabled"):
            try:
                quality_enabled = bool(self.story_quality_review_enabled.get())
            except Exception:
                quality_enabled = True

        if not quality_enabled:
            self.story_quality_summary_var.set("质量评审：已关闭（仅生成，不自动精修）")
        else:
            reports = getattr(self, "chapter_quality_reports", [])
            last_report = None
            if isinstance(reports, list):
                for row in reversed(reports):
                    if isinstance(row, dict) and row:
                        last_report = row
                        break
            if last_report:
                avg = float(last_report.get("avg_score", 0.0) or 0.0)
                scores = last_report.get("scores", {}) if isinstance(last_report.get("scores", {}), dict) else {}
                realism = float(scores.get("realism", 0.0) or 0.0)
                detail = float(scores.get("detail", 0.0) or 0.0)
                escalation = float(scores.get("escalation", 0.0) or 0.0)
                hook_density = float(scores.get("hook_density", 0.0) or 0.0)
                issue = ""
                issues = last_report.get("issues", [])
                if isinstance(issues, list) and issues:
                    issue = str(issues[0] or "").strip()
                key_fix = str(last_report.get("key_fix", "") or "").strip()
                title = str(last_report.get("chapter_title", "") or "").strip()
                self.story_quality_summary_var.set(
                    f"质量评审：{title or '最近章节'} | 平均{avg:.1f} | 真实{realism:.1f} 细节{detail:.1f}"
                    f" 高潮{escalation:.1f} 钩子{hook_density:.1f}"
                    f"{' | 修复: ' + (key_fix or issue) if (key_fix or issue) else ''}"
                )
            else:
                self.story_quality_summary_var.set("质量评审：等待章节生成后自动打分")

        ledger = self._get_story_memory_ledger()
        if ledger:
            last = ledger[-1]
            try:
                chapter_no = int(last.get("chapter_index", len(ledger) - 1)) + 1
            except Exception:
                chapter_no = len(ledger)
            chapter_title = str(last.get("chapter_title", "") or "").strip()
            summary = str(last.get("summary", "") or "").strip()
            hooks = last.get("unresolved_hooks", [])
            hook_text = ""
            if isinstance(hooks, list) and hooks:
                hook_text = str(hooks[0] or "").strip()
            desc = summary[:36] + ("..." if len(summary) > 36 else "") if summary else "已记录"
            self.story_memory_summary_var.set(
                f"记忆账本：第{chapter_no}章《{chapter_title or '未命名'}》 | {desc}"
                f"{' | 伏笔: ' + hook_text if hook_text else ''}"
            )
        else:
            self.story_memory_summary_var.set("记忆账本：暂无章节记忆")

    def _build_enhanced_system_prompt(self, base_system_prompt: str) -> str:
        """在模版 system prompt 基础上追加专业写作标准，提升真实感与连贯性。

        这不是提示词调优，而是建立持久的写作人格和行为准则。
        """
        craft_rules = (
            "\n\n【写作准则（全程遵守）】\n"
            "1. 场景真实：每个场景必须有具体的时间、地点、光线、声音等感官锚点，"
            "读者能'看到'画面而不是'听到'总结。\n"
            "2. 对话驱动：用对话推进剧情和暴露人物性格，对话要口语化、有潜台词，"
            "不同人物的说话方式必须有区分度。\n"
            "3. 动作代替描述：用'她把杯子摔在桌上'代替'她很生气'，"
            "用微动作（攥拳、移开视线、咬嘴唇）传递情绪。\n"
            "4. 因果链清晰：每个情节转折必须有前因，角色的每个重大决定都要有动机铺垫，"
            "不能突然性格反转。\n"
            "5. 禁止总结腔：不要出现'就这样，他们……''从此以后……''这件事让他明白了……'等"
            "旁白式总结，让事件本身说话。\n"
            "6. 节奏控制：紧张场景用短句、快切；情感场景放慢节奏，加入环境细节和内心独白。\n"
            "7. 每段话推进一个信息点，禁止原地踏步或重复已知信息。"
            "\n8. 高潮密度：每章至少两次节奏高点，且后一个高点必须比前一个代价更大。"
            "\n9. 上下文一致：后文必须继承前文事实、关系、伤害、承诺、伏笔和人物心理状态。"
        )
        return base_system_prompt.rstrip() + craft_rules + "\n\n" + self._build_story_skill_pack()

    def _format_story_rules(self, rules):
        items = []
        for rule in (rules or []):
            text = str(rule).strip()
            if text:
                items.append(text)
        if not items:
            return "- 无"
        return "\n".join(f"- {item}" for item in items)

    def _get_rag_min_score(self) -> float:
        raw = 0.12
        if hasattr(self, "rag_min_score"):
            try:
                raw = float(self.rag_min_score.get())
            except Exception:
                raw = 0.12
        return max(0.0, min(1.0, raw))

    def _postprocess_rag_results(self, results):
        rows = list(results or [])
        if not rows:
            return []

        min_score = self._get_rag_min_score()
        accepted = []
        seen = set()

        for chunk, score, meta in rows:
            text = str(chunk or "").strip()
            if not text:
                continue
            try:
                score_value = float(score)
            except Exception:
                score_value = 0.0
            if score_value < min_score:
                continue
            signature = re.sub(r"\s+", " ", text[:260]).strip().lower()
            if not signature or signature in seen:
                continue
            seen.add(signature)
            accepted.append((text, score_value, meta))

        if not accepted:
            for chunk, score, meta in rows:
                text = str(chunk or "").strip()
                if not text:
                    continue
                signature = re.sub(r"\s+", " ", text[:260]).strip().lower()
                if not signature or signature in seen:
                    continue
                seen.add(signature)
                try:
                    score_value = float(score)
                except Exception:
                    score_value = 0.0
                accepted.append((text, score_value, meta))
                if len(accepted) >= 2:
                    break

        top_k = 6
        if hasattr(self, "top_k"):
            try:
                top_k = int(self.top_k.get())
            except Exception:
                top_k = 6
        return accepted[: max(1, top_k)]

    def _build_story_run_banner(self, requirement: str, category: str, rag_rows=None) -> str:
        effective_category, category_note = self._resolve_effective_story_category(requirement, category)
        template = self._get_story_template_profile(requirement=requirement, category=effective_category)
        base_key = str(template.get("base_key", template.get("key", "")) or "").strip()
        resolved_key = str(template.get("resolved_key", template.get("key", "")) or "").strip()
        strategy_key = str(template.get("strategy", self._get_story_template_strategy()) or "").strip()
        strategy_label = strategy_key
        for row in list_story_template_strategies():
            if row.get("key") == strategy_key:
                strategy_label = row.get("label", strategy_key)
                break

        base_label = get_story_template(base_key).get("label", base_key) if base_key else "默认模版"
        resolved_label = template.get("label", resolved_key or "默认模版")

        lines = []
        if base_key and resolved_key and base_key != resolved_key:
            lines.append(f"🎭 本次模版：{resolved_label}（策略：{strategy_label}，基准：{base_label}）")
        else:
            lines.append(f"🎭 本次模版：{resolved_label}（策略：{strategy_label}）")
        if category_note:
            lines.append(f"🧭 题材纠偏：{category_note}")

        rag_items = list(rag_rows or [])
        if rag_items:
            lines.append(f"🔎 RAG检索：命中 {len(rag_items)} 条（阈值≥{self._get_rag_min_score():.2f}）")
            for idx, (_chunk, score, meta) in enumerate(rag_items[:4], start=1):
                source = "未知来源"
                if isinstance(meta, (list, tuple)) and meta:
                    try:
                        source = Path(str(meta[0])).name or str(meta[0])
                    except Exception:
                        source = str(meta[0])
                lines.append(f"  {idx}. {source}（score={float(score):.3f}）")
        return "\n".join(lines)

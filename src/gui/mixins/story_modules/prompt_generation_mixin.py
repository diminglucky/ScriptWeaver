"""Story prompt text-generation builders."""

from __future__ import annotations

from ...helpers.story_creativity import build_story_creativity_block
from ...helpers.story_quality import extract_last_sentence
from ...helpers.story_pipeline_profile import (
    build_emotion_arc_guidelines,
    build_section_transition_guidelines,
)
from ...helpers.story_prompt_profile import (
    get_outline_core_requirements_text,
    get_outline_intro_text,
    get_outline_output_example_text,
    get_section_intro_text,
    get_section_reminder_text,
    get_section_writing_spec_text,
    get_story_intro_text,
    get_story_reminder_text,
    get_story_writing_spec_text,
)
from ...helpers.story_writing_guardrails import (
    build_non_ai_writing_guardrails,
    build_outline_title_guardrails,
    get_chapter_title_limits,
)


class StoryPromptGenerationMixin:
    """Build outline/story/section prompts."""
    def _build_outline_prompt(self, requirement, contexts, category):
        ctx = "\n\n".join(f"【资料{i+1}】\n{c}" for i, c in enumerate(contexts))
        target_chars = self.target_chars.get()
        style_part = ""
        if hasattr(self, "style"):
            try:
                style_part = self.style.get().strip()
            except Exception:
                style_part = ""
        alignment_block, effective_category, _category_note = self._build_requirement_alignment_block(
            requirement,
            category,
            stage="outline",
        )
        template = self._get_story_template_profile(requirement=requirement, category=effective_category)
        template_label = template.get("label", "默认模版")
        outline_focus = template.get("outline_focus", "围绕主题构建起承转合")
        outline_rules = self._format_story_rules(template.get("outline_rules", []))
        outline_guardrails = build_outline_title_guardrails()
        creativity_mode = self._get_story_creativity_mode()
        creativity_rules = build_story_creativity_block(
            creativity_mode,
            requirement=requirement,
            category=effective_category,
            style_hint=style_part,
            stage="outline",
            nonce=self._get_story_creativity_nonce(),
            primary_template_key=template.get("key", ""),
        )
        creativity_part = (
            f"【创新引擎（{creativity_mode}）】\n{creativity_rules}\n\n"
            if creativity_rules
            else ""
        )
        if target_chars <= 3000:
            suggested_sections = "3-4"
        elif target_chars <= 8000:
            suggested_sections = "4-6"
        elif target_chars <= 15000:
            suggested_sections = "6-8"
        else:
            suggested_sections = "8-10"
        chapter_title_min_len, chapter_title_max_len = get_chapter_title_limits()
        outline_intro = get_outline_intro_text()
        outline_core_requirements = get_outline_core_requirements_text(
            suggested_sections=suggested_sections,
            chapter_title_min_len=chapter_title_min_len,
            chapter_title_max_len=chapter_title_max_len,
        )
        outline_output_example = get_outline_output_example_text()

        return (
            f"{outline_intro}\n\n"
            "【核心要求】\n"
            f"{outline_core_requirements}\n\n"
            f"{alignment_block}\n"
            "【模版要求】\n"
            f"- 当前模版：{template_label}\n"
            f"- 模版导向：{outline_focus}\n"
            f"{outline_rules}\n\n"
            "【标题质量约束】\n"
            f"{outline_guardrails}\n\n"
            f"{creativity_part}"
            f"【创作信息】\n"
            f"- 主题/需求：{requirement}\n"
            f"- 种类（最终）：{effective_category}\n"
            f"- 种类（界面）：{category}\n"
            f"- 目标字数：{target_chars}字\n\n"
            f"【参考资料】\n{ctx if ctx else '无特定资料'}\n\n"
            f"{outline_output_example}"
        )

    def _build_prompt(self, requirement, contexts, category, outline=""):
        ctx = "\n\n".join(f"【资料{i+1}】\n{c}" for i, c in enumerate(contexts))
        outline_part = ("\n\n请严格参照下述目录完成写作：\n" + outline.strip()) if outline else ""
        global_overview = ""
        if hasattr(self, "_get_story_global_overview_text"):
            try:
                global_overview = str(self._get_story_global_overview_text() or "").strip()
            except Exception:
                global_overview = ""
        else:
            global_overview = str(getattr(self, "story_global_overview_text", "") or "").strip()
        global_overview_part = (
            "【全书总览蓝图（强约束）】\n"
            f"{global_overview}\n"
            "- 正文必须遵循该蓝图推进，不得偏离主线或破坏既有设定。\n\n"
            if global_overview
            else ""
        )
        style_part = self.style.get().strip()
        target = self.target_chars.get()
        alignment_block, effective_category, _category_note = self._build_requirement_alignment_block(
            requirement,
            category,
            stage="story",
        )
        template = self._get_story_template_profile(requirement=requirement, category=effective_category)
        template_label = template.get("label", "默认模版")
        story_focus = template.get("story_focus", "叙事连贯，冲突清晰，结尾有回扣")
        story_rules = self._format_story_rules(template.get("story_rules", []))
        writing_guardrails = build_non_ai_writing_guardrails()
        emotion_guardrails = build_emotion_arc_guidelines(stage="story")
        creativity_mode = self._get_story_creativity_mode()
        creativity_rules = build_story_creativity_block(
            creativity_mode,
            requirement=requirement,
            category=effective_category,
            style_hint=style_part,
            stage="story",
            nonce=self._get_story_creativity_nonce(),
            primary_template_key=template.get("key", ""),
        )
        creativity_part = (
            f"【创新引擎（{creativity_mode}）】\n{creativity_rules}\n\n"
            if creativity_rules
            else ""
        )
        style_value = style_part if style_part else "自动匹配模版风格"
        min_chars = int(target * 0.9)
        max_chars = int(target * 1.1)
        story_intro = get_story_intro_text()
        story_writing_spec = get_story_writing_spec_text()
        story_reminder = get_story_reminder_text(min_chars=min_chars)
        return (
            f"{story_intro}\n\n"
            "【核心要求】\n"
            f"1. **字数要求（强制）**：必须写足 {min_chars}-{max_chars} 字之间，目标 {target} 字。请务必写够长度，不要过早结束。\n"
            f"2. **模版**：{template_label}\n"
            f"3. **模版导向**：{story_focus}\n"
            f"4. **种类（最终）**：{effective_category}\n"
            f"5. **种类（界面）**：{category}\n"
            f"{alignment_block}\n"
            f"6. **风格倾向**：{style_value}\n"
            f"7. **创作主题/需求**：{requirement}\n\n"
            "【模版规则】\n"
            f"{story_rules}\n\n"
            f"{creativity_part}"
            "【写作规范】\n"
            f"{story_writing_spec}\n\n"
            "【去模板腔与专业度】\n"
            f"{writing_guardrails}\n\n"
            "【情感弧线与真人感】\n"
            f"{emotion_guardrails}\n\n"
            f"{global_overview_part}"
            "【特别提醒】\n"
            f"{story_reminder}\n"
            f"{outline_part}\n\n"
            f"【参考资料】\n{ctx if ctx else '无特定资料，请根据主题自由创作。'}"
        )

    def _build_section_prompt(
        self,
        section,
        section_index,
        total_sections,
        previous_content,
        requirement,
        contexts,
        category,
        style_part,
        target_chars_per_section,
        section_overview_plan="",
    ):
        ctx = "\n\n".join(f"【资料{i+1}】\n{c}" for i, c in enumerate(contexts)) if contexts else ""
        alignment_block, effective_category, _category_note = self._build_requirement_alignment_block(
            requirement,
            category,
            stage="section",
        )
        template = self._get_story_template_profile(requirement=requirement, category=effective_category)
        template_label = template.get("label", "默认模版")
        section_rules = self._format_story_rules(template.get("section_rules", []))
        writing_guardrails = build_non_ai_writing_guardrails()
        emotion_guardrails = build_emotion_arc_guidelines(stage="section")
        transition_guardrails = build_section_transition_guidelines()
        creativity_mode = self._get_story_creativity_mode()
        creativity_rules = build_story_creativity_block(
            creativity_mode,
            requirement=requirement,
            category=effective_category,
            style_hint=style_part,
            stage="section",
            nonce=self._get_story_creativity_nonce(),
            primary_template_key=template.get("key", ""),
        )
        creativity_part = (
            f"【创新引擎（{creativity_mode}）】\n{creativity_rules}\n\n"
            if creativity_rules
            else ""
        )
        style_value = style_part if style_part else "自动匹配模版风格"
        min_chars = int(target_chars_per_section * 0.85)
        max_chars = int(target_chars_per_section * 1.15)
        section_title = section["title"]
        section_items = "\n".join(f"  - {item}" for item in section["items"]) if section["items"] else ""
        context_hint = ""
        prev_window = min(3200, max(1200, int(target_chars_per_section * 1.2)))
        if section_index == 0:
            context_hint = "这是故事的开篇部分，需要在前两段内建立场景、主角出场、核心冲突信号。"
        else:
            # 提取上章结尾关键句，强化衔接
            last_sentence = extract_last_sentence(previous_content or "", max_chars=300)
            if section_index == total_sections - 1:
                context_hint = (
                    f"这是故事的最后部分（第{section_index+1}/{total_sections}章），必须收束全部主线，"
                    "呼应开篇悬念，给出情感落点。\n\n"
                )
            else:
                context_hint = (
                    f"这是故事的第 {section_index + 1}/{total_sections} 部分。\n\n"
                )
            context_hint += (
                f"【上章结尾原文（必须衔接）】\n{last_sentence}\n\n"
                "⚠️ 衔接硬性要求：\n"
                "1. 本章开头的第一段必须紧接上章结尾的场景/动作/情绪，仿佛读者翻页后立刻看到下文；\n"
                "2. 禁止重复上章结尾已描写的事件或对话；\n"
                "3. 保持时间线、地点、人物状态的连续性——上章结尾人物在做什么，本章开头就从那一刻继续；\n"
                "4. 不要用'第二天'/'后来'等大幅跳跃开头，除非蓝图明确要求时间跳跃。\n\n"
                f"前文参考片段（最后{prev_window}字）：\n{previous_content[-prev_window:] if previous_content else '无'}"
            )
        transition_context = self._build_section_transition_context(section_index, previous_content)
        if transition_context:
            context_hint += f"\n\n【跨章衔接线索】\n{transition_context}"
        memory_context = self._build_story_memory_context(section_index, max_items=min(6, max(3, section_index)))
        if memory_context:
            context_hint += (
                "\n\n【记忆账本（最近章节）】\n"
                f"{memory_context}\n"
                "- 必须保持人物状态、关系变化、未回收伏笔的一致性。"
            )
        section_intro = get_section_intro_text(section_no=section_index + 1, total_sections=total_sections)
        section_writing_spec = get_section_writing_spec_text()
        section_reminder = get_section_reminder_text(min_chars=min_chars)
        global_overview = ""
        if hasattr(self, "_get_story_global_overview_text"):
            try:
                global_overview = str(self._get_story_global_overview_text() or "").strip()
            except Exception:
                global_overview = ""
        else:
            global_overview = str(getattr(self, "story_global_overview_text", "") or "").strip()
        global_overview_part = (
            "【全书总览蓝图（必须对齐）】\n"
            f"{global_overview}\n"
            "- 本章必须服务全书主线，不得出现与蓝图冲突的人物动机、事件顺序或结局走向。\n\n"
            if global_overview
            else ""
        )
        overview_plan_part = ""
        if section_overview_plan and str(section_overview_plan).strip():
            # 在蓝图中追加上章实际结尾，确保 AI 同时看到蓝图规划和真实上文
            actual_tail_note = ""
            if section_index > 0 and previous_content:
                actual_tail = extract_last_sentence(previous_content, max_chars=300)
                if actual_tail:
                    actual_tail_note = (
                        f"\n\n⚠️ 注意：上章实际写出的结尾如下（必须从此处接续，蓝图中的【承接上章】仅供参考）：\n"
                        f"{actual_tail}"
                    )
            overview_plan_part = (
                "【已确认章节总览（必须遵循）】\n"
                f"{str(section_overview_plan).strip()}"
                f"{actual_tail_note}\n\n"
            )
        return (
            f"{section_intro}\n\n"
            f"【本节要求】\n"
            f"1. **字数**：必须写足 {min_chars}-{max_chars} 字，目标 {target_chars_per_section} 字\n"
            f"2. **章节主题**：{section_title}\n"
            f"3. **要点**：\n{section_items if section_items else '  根据标题自由发挥'}\n"
            f"4. **模版**：{template_label}\n"
            f"5. **种类（最终）**：{effective_category}\n"
            f"6. **种类（界面）**：{category}\n"
            f"{alignment_block}\n"
            f"7. **风格**：{style_value}\n\n"
            f"【模版规则】\n{section_rules}\n\n"
            f"{creativity_part}"
            f"【上下文】\n{context_hint}\n\n"
            "【写作规范】\n"
            f"{section_writing_spec}\n\n"
            f"【跨章衔接一致性】\n{transition_guardrails}\n\n"
            f"【去模板腔与专业度】\n{writing_guardrails}\n\n"
            f"【情感弧线与真人感】\n{emotion_guardrails}\n\n"
            f"{global_overview_part}"
            f"{overview_plan_part}"
            "【特别提醒】\n"
            f"{section_reminder}\n"
            f"主题/需求：{requirement}\n\n"
            + (f"【参考资料】\n{ctx}\n" if ctx else "")
            + (
                f"⚠️ 最终衔接指令：本章第一段必须从上章结尾的那一刻紧接着写，不得跳跃或重复。\n\n"
                if section_index > 0 else ""
            )
            + "请直接开始写正文，不要任何前缀或标题："
        )

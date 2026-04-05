"""Shot extraction and prompt-building workflows."""

from __future__ import annotations

from tkinter import DISABLED, END, NORMAL, messagebox
import logging
from datetime import datetime
from pathlib import Path

from src.clients.deepseek_client import DeepSeekClient
from src.utils.text import sanitize as _sanitize

from ...helpers.director_script_builder import DirectorScriptBuilder
from .shot_prompt_templates import (
    DEFAULT_SHOT_EXTRACT_MODE_CONFIG,
    SHOT_EXTRACT_MODE_CONFIGS,
    STYLE_INSTRUCTIONS,
)

logger = logging.getLogger(__name__)


def print(*args, **kwargs):  # type: ignore[override]
    logger.info(" ".join(str(a) for a in args))


def _resolve_deepseek_client_cls():
    """Use aggregator module symbol so tests can monkey-patch one stable path."""
    try:
        from . import shot_manager as shot_manager_module  # local import avoids circular init timing issues

        patched = getattr(shot_manager_module, "DeepSeekClient", None)
        if patched is not None:
            return patched
    except Exception:
        pass
    return DeepSeekClient


class ShotPromptMixin:
    """Shot extraction and prompt generation interactions."""
    def _on_recommend_video_mode(self) -> None:
        """智能推荐视频模式"""
        story_text = self.output.get("1.0", END).strip()
        if not story_text:
            messagebox.showwarning("提示", "请先在'故事'页生成或粘贴故事内容")
            return
        
        # 分析故事特征
        story_length = len(story_text)
        
        # 统计场景转换关键词
        scene_keywords = ['突然', '这时', '随后', '接着', '然后', '于是', '转身', '走进', '来到', 
                          '回到', '看到', '听到', '发现', '意识到', '想起', '记得']
        scene_count = sum(story_text.count(kw) for kw in scene_keywords)
        
        # 统计情节复杂度关键词
        complexity_keywords = ['但是', '然而', '不料', '没想到', '原来', '竟然', '居然', 
                               '转折', '突变', '真相', '秘密', '回忆', '闪回']
        complexity_score = sum(story_text.count(kw) for kw in complexity_keywords)
        
        # 统计人物数量（粗略估计）
        character_keywords = ['他', '她', '我', '你', '他们', '她们', '我们']
        has_multiple_characters = sum(story_text.count(kw) for kw in character_keywords) > 20
        
        # 推荐逻辑
        recommendation = ""
        mode = ""
        reason = []
        
        if story_length < 1000:
            mode = "brief"
            recommendation = "🎬 简短视频(8-12)"
            reason.append(f"• 故事较短（{story_length}字）")
            reason.append("• 适合快节奏短视频")
            reason.append("• 8-12个镜头足够覆盖核心情节")
        elif story_length < 2500:
            if complexity_score > 5 or scene_count > 10:
                mode = "video"
                recommendation = "🎬 平衡视频(15-25) ⭐推荐"
                reason.append(f"• 故事长度适中（{story_length}字）")
                reason.append(f"• 情节有一定复杂度（转折词{complexity_score}个）")
                reason.append("• 15-25个镜头能完整呈现故事")
            else:
                mode = "normal"
                recommendation = "🎬 标准视频(15-22)"
                reason.append(f"• 故事长度标准（{story_length}字）")
                reason.append("• 情节相对简单流畅")
                reason.append("• 15-22个镜头刚好合适")
        elif story_length < 5000:
            if complexity_score > 8 or has_multiple_characters:
                mode = "detailed"
                recommendation = "🎬 精细视频(25-40)"
                reason.append(f"• 故事较长（{story_length}字）")
                reason.append(f"• 情节复杂（转折词{complexity_score}个，场景{scene_count}处）")
                reason.append("• 需要25-40个镜头细致呈现")
            else:
                mode = "video"
                recommendation = "🎬 平衡视频(15-25)"
                reason.append(f"• 故事较长（{story_length}字）")
                reason.append("• 情节适中，不太复杂")
                reason.append("• 15-25个镜头平衡完整性和精简度")
        else:
            mode = "detailed"
            recommendation = "🎬 精细视频(25-40)"
            reason.append(f"• 故事很长（{story_length}字）")
            reason.append(f"• 需要充足的镜头数量来完整叙事")
            reason.append("• 25-40个镜头才能展现所有重要时刻")
        
        # 显示推荐结果
        reason_text = "\n".join(reason)
        result = messagebox.askyesno(
            "智能推荐结果", 
            f"📊 故事分析：\n"
            f"字数：{story_length} 字\n"
            f"场景转换：约 {scene_count} 处\n"
            f"情节复杂度：{'高' if complexity_score > 8 else '中' if complexity_score > 4 else '低'}\n\n"
            f"💡 推荐模式：\n{recommendation}\n\n"
            f"📝 推荐理由：\n{reason_text}\n\n"
            f"是否立即使用推荐模式生成分镜？"
        )
        
        if result:
            # 用户确认，直接生成
            self._on_img_extract_shots(mode=mode)
        else:
            self._ui(self.status.set, f"💡 推荐使用 {recommendation}")

    
    def _on_img_extract_shots(self, mode="normal") -> None:
        """从故事生成分镜列表。"""
        story_text = self.output.get("1.0", END).strip()
        if not story_text:
            messagebox.showwarning("提示", "请先在'故事'页生成或粘贴正文内容，然后再生成分镜")
            return

        api_config = self._resolve_story_task_api("image_shot_extract")
        selected_api = api_config.get("provider", "")
        api_key = _sanitize(api_config.get("key", ""))
        base_url = _sanitize(api_config.get("base_url", ""))
        model = _sanitize(api_config.get("model", ""))
        if not api_key:
            messagebox.showwarning("提示", f"请先在故事生成页面配置 {selected_api} 的API Key")
            return

        mode_name, shot_count, instruction = self._get_shot_extract_mode_config(mode)

        import threading

        threading.Thread(
            target=lambda: self._run_shot_extract_task(
                story_text=story_text,
                selected_api=selected_api,
                api_key=api_key,
                base_url=base_url,
                model=model,
                mode_name=mode_name,
                shot_count=shot_count,
                instruction=instruction,
            ),
            daemon=True,
        ).start()

    def _resolve_story_task_api(self, task_key: str) -> dict:
        """解析故事侧任务使用的路由 API 配置。"""
        fallback_provider = None
        if hasattr(self, "quick_story_api"):
            fallback_provider = self.quick_story_api.get()
        if not fallback_provider and hasattr(self, "api_preset"):
            fallback_provider = self.api_preset.get()

        fallback_model = None
        if hasattr(self, "story_model_var"):
            fallback_model = self.story_model_var.get()
        elif hasattr(self, "model"):
            fallback_model = self.model.get()

        return self._resolve_task_api(
            task_key,
            fallback_provider=fallback_provider,
            fallback_model=fallback_model,
        )

    def _run_shot_extract_task(
        self,
        *,
        story_text: str,
        selected_api: str,
        api_key: str,
        base_url: str,
        model: str,
        mode_name: str,
        shot_count: str,
        instruction: str,
    ) -> None:
        """后台执行分镜提取并刷新 UI。"""
        try:
            self.set_busy(True)
            self._ui(self.status.set, f"🎬 正在使用 {selected_api} 生成{mode_name}分镜（目标{shot_count}个）...")
            self._header_status(f"生成{mode_name}分镜...", "🎬")

            client = _resolve_deepseek_client_cls()(api_key=api_key, base_url=base_url, model=model)
            self._ui(self.status.set, f"🤖 {selected_api} 正在分析故事并生成{mode_name}分镜...")

            resp = client.chat(
                [
                    {"role": "system", "content": instruction},
                    {"role": "user", "content": story_text},
                ],
                temperature=max(0.4, self.temperature.get() - 0.2),
            )

            self._ui(self.status.set, "📋 解析分镜头列表...")
            self._header_status("解析分镜中...", "📋")
            shots = self._parse_shot_response(resp)
            if shots:
                self._ui(self.status.set, "✅ 更新分镜显示...")
                self._ui(self._apply_extracted_shots_to_ui, shots, mode_name)
        except Exception as exc:
            self._ui(messagebox.showerror, "错误", str(exc))
            self._header_status("分镜生成失败", "❌")
        finally:
            self.set_busy(False)

    def _apply_extracted_shots_to_ui(self, shots: list[str], mode_name: str) -> None:
        """将分镜提取结果写回 UI。"""
        self.shots_listbox.config(state=NORMAL)
        self.shots_listbox.delete(0, END)
        for index, shot in enumerate(shots):
            display_text = f"{index + 1}. {shot[:80]}..." if len(shot) > 80 else f"{index + 1}. {shot}"
            self.shots_listbox.insert(END, display_text)

        self.parsed_shots = shots
        self.shots_listbox.selection_set(0)
        self.shots_listbox.activate(0)
        self._on_shot_listbox_selected(None)
        self._ui(self.status.set, f"🎬 已生成{mode_name} {len(shots)} 个分镜（点击列表中的分镜即可选择）")
        self._header_status("分镜生成完成", "✅")

    def _get_shot_extract_mode_config(self, mode: str) -> tuple[str, str, str]:
        """返回分镜提取模式名、数量提示和系统指令。"""
        return SHOT_EXTRACT_MODE_CONFIGS.get(mode, DEFAULT_SHOT_EXTRACT_MODE_CONFIG)
    
    
    def _on_shot_listbox_selected(self, event) -> None:
        """当在Listbox中选择分镜时，自动识别并选择参考人物"""
        if not hasattr(self, 'parsed_shots') or not self.parsed_shots:
            return
        
        selection = self.shots_listbox.curselection()
        if not selection:
            return
        
        selected_index = selection[0]
        if selected_index < 0 or selected_index >= len(self.parsed_shots):
            return
        
        # 获取选中的分镜文本
        current_shot = self.parsed_shots[selected_index]
        
        # 显示状态
        self._ui(self.status.set, f"已选择第 {selected_index+1} 个分镜，正在识别人物...")
        
        # 智能识别并自动选择参考人物（延迟执行以确保UI更新）
        self.after(50, lambda: self._auto_select_characters_from_shot(current_shot, ""))
    
    
    def _on_shot_selected(self, event) -> None:
        """兼容性函数：当使用Combobox选择分镜时（已废弃，保留以防代码引用）"""
        # 此函数已被 _on_shot_listbox_selected 替代
        pass
    
    
    def _on_img_prompt_from_current_shot(self) -> None:
        """从当前选中的分镜生成中文图片描述。"""
        selected = self._get_selected_shot_for_prompt()
        if selected is None:
            return
        selected_index, current_shot = selected

        prompt_context = self._prepare_current_shot_prompt_context(selected_index, current_shot)
        if prompt_context is None:
            return

        import threading

        threading.Thread(
            target=lambda: self._run_current_shot_prompt_task(prompt_context),
            daemon=True,
        ).start()

    def _get_selected_shot_for_prompt(self) -> tuple[int, str] | None:
        """返回当前选中的分镜索引与文本。"""
        if not hasattr(self, "parsed_shots") or not self.parsed_shots:
            messagebox.showwarning("提示", "请先生成分镜")
            return None

        selection = self.shots_listbox.curselection()
        if not selection:
            messagebox.showwarning("提示", "请先在列表中选择一个分镜")
            return None

        selected_index = selection[0]
        if selected_index < 0 or selected_index >= len(self.parsed_shots):
            messagebox.showwarning("提示", "请先在列表中选择一个分镜")
            return None

        return selected_index, self.parsed_shots[selected_index]

    def _prepare_current_shot_prompt_context(self, selected_index: int, current_shot: str) -> dict | None:
        """组装当前分镜描述生成所需上下文。"""
        story_text = self.output.get("1.0", END).strip() if hasattr(self, "output") else ""
        scene = self.img_entry_scene.get().strip() if hasattr(self, "img_entry_scene") else ""
        roles = self.img_txt_roles.get("1.0", END).strip() if hasattr(self, "img_txt_roles") else ""
        img_type = self.img_type.get() if hasattr(self, "img_type") else "写实照片"

        style_desc = STYLE_INSTRUCTIONS.get(img_type, f"{img_type}风格")
        is_hunyuan = self._is_hunyuan_image_provider()
        selected_characters = self._get_selected_reference_characters()
        has_photo = any(char.get("photo_path") for char in selected_characters if char)
        inst, char_limit = self._build_current_shot_system_instruction(
            img_type=img_type,
            style_desc=style_desc,
            is_hunyuan=is_hunyuan,
            has_photo=has_photo,
        )

        api_config = self._resolve_story_task_api("image_shot_to_desc")
        selected_api = api_config.get("provider", "")
        api_key = _sanitize(api_config.get("key", ""))
        base_url = _sanitize(api_config.get("base_url", ""))
        model = _sanitize(api_config.get("model", ""))
        if not api_key:
            messagebox.showwarning("提示", f"请先在故事生成页面配置 {selected_api} 的API Key")
            return None

        return {
            "selected_index": selected_index,
            "current_shot": current_shot,
            "story_text": story_text,
            "scene": scene,
            "roles": roles,
            "img_type": img_type,
            "is_hunyuan": is_hunyuan,
            "selected_characters": selected_characters,
            "has_photo": has_photo,
            "inst": inst,
            "char_limit": char_limit,
            "selected_api": selected_api,
            "api_key": api_key,
            "base_url": base_url,
            "model": model,
        }

    def _is_hunyuan_image_provider(self) -> bool:
        """检测当前图片 API 是否是腾讯混元。"""
        if not hasattr(self, "img_api_preset"):
            return False
        preset_name = self.img_api_preset.get()
        return "腾讯混元" in preset_name or "hunyuan" in preset_name.lower()

    def _build_current_shot_system_instruction(
        self,
        *,
        img_type: str,
        style_desc: str,
        is_hunyuan: bool,
        has_photo: bool,
    ) -> tuple[str, str]:
        """根据模式构建系统提示词与字数要求。"""
        if is_hunyuan:
            char_limit = "180字以内"
            if has_photo:
                return (
                    (
                        f"你是专业视觉设计师。这是图生图模式，参考图片已包含人物外貌。\n"
                        f"生成简洁的中文图片描述，用于腾讯混元生成【{img_type}】风格的图片。\n\n"
                        f"【风格】{style_desc}\n\n"
                        f"【只描述动态元素】：\n"
                        f"1. 动作：具体动作（站立、行走、坐下、蹲下、转身等）、手部动作\n"
                        f"2. 表情：具体表情（微笑、严肃、惊讶、沉思、悲伤等）、眼神\n"
                        f"3. 姿势：身体姿态（挺胸、驼背、放松、紧张等）\n"
                        f"4. 场景：地点、物品、光线、氛围\n"
                        f"5. 镜头：景别（全身照/中景/特写）、角度\n\n"
                        f"【禁止描述】：不要描述年龄、性别、发型、脸型、肤色、体型、服装等外貌特征。\n\n"
                        f"【格式示例】：站立、双手插兜、微笑、办公室、自然光、全身照、中景平视\n\n"
                        f"要求：控制在{char_limit}，只输出描述文本。"
                    ),
                    char_limit,
                )
            return (
                (
                    f"你是专业视觉设计师。基于分镜描述，生成简洁精确的中文图片描述，"
                    f"用于腾讯混元生成【{img_type}】风格的图片。\n\n"
                    f"【风格】{style_desc}\n\n"
                    f"【描述元素】：\n"
                    f"1. 人物（如有）：年龄、性别、发型、服饰、表情、动作、姿势\n"
                    f"2. 环境：地点、主要物品、色调\n"
                    f"3. 光线：光源、时间、氛围\n"
                    f"4. 镜头：景别（全身照/中景/特写）、角度、构图\n\n"
                    f"【格式】简洁短语，用顿号和逗号连接。\n"
                    f"示例：25岁女性、黑色长发、白色医生制服、疲惫眼神、双手插口袋、站立、深夜医院走廊、"
                    f"白墙灰地板、顶部日光灯、中景平视、寂静压抑\n\n"
                    f"要求：控制在{char_limit}，如有人物设定请按名字匹配特征，只描述当前分镜中出现的人物。"
                ),
                char_limit,
            )

        if has_photo:
            char_limit = "200-300字"
            return (
                (
                    f"你是专业视觉设计师。这是图生图模式，参考图片已包含人物外貌。\n"
                    f"生成中文图片描述，用于生成高质量的【{img_type}】风格图片。\n\n"
                    f"【风格】{style_desc}\n\n"
                    f"【只描述动态元素】：\n"
                    f"1. 动作：具体动作（站立、行走、坐下、蹲下、转身、跑步等）、手部动作、身体姿势\n"
                    f"2. 表情：具体表情（微笑、严肃、惊讶、沉思、悲伤、愤怒等）、眼神方向\n"
                    f"3. 场景环境：地点、主要物品、背景、光线、天气、氛围\n"
                    f"4. 镜头：景别（全身照/中景/特写）、角度（平视/俯视/仰视）、构图\n\n"
                    f"【禁止描述】：不要描述年龄、性别、发型、脸型、肤色、体型、身高、服装款式颜色等外貌特征。\n\n"
                    f"【输出要求】：\n"
                    f"- 长度：{char_limit}，自然流畅\n"
                    f"- 格式：流畅的中文段落\n"
                    f"- 重点突出动作、表情、场景\n"
                    f"- 必须明确指定镜头景别（全身照/中景/特写）"
                ),
                char_limit,
            )

        char_limit = "300-400字"
        return (
            (
                f"你是专业视觉设计师。基于分镜描述，生成简洁精确的中文图片描述，"
                f"用于生成高质量的【{img_type}】风格图片。\n\n"
                f"【风格】{style_desc}\n\n"
                f"【核心元素】\n"
                f"1. 人物（如有）：年龄、性别、发型、服饰、表情、动作、姿势\n"
                f"2. 环境：地点、主要物品、色调\n"
                f"3. 光线：光源、时间、氛围\n"
                f"4. 镜头：景别（全身照/中景/特写）、角度、构图\n\n"
                f"【输出要求】\n"
                f"- 长度：{char_limit}，自然流畅\n"
                f"- 如有人物设定，按名字匹配特征\n"
                f"- 只描述当前分镜中的人物\n"
                f"- 必须明确指定镜头景别"
            ),
            char_limit,
        )

    def _build_current_shot_user_prompt(
        self,
        *,
        img_type: str,
        current_shot: str,
        story_text: str,
        scene: str,
        roles: str,
        selected_characters: list[dict],
        has_photo: bool,
        context_length: int,
        char_limit: str,
    ) -> str:
        """构建当前分镜图片描述的用户提示词。"""
        user_parts = [f"【目标图片类型】{img_type}\n"]

        if has_photo:
            char_names = [c["name"] for c in selected_characters if c.get("name")]
            user_parts.append(f"【图生图模式】参考图片已包含人物外貌（{', '.join(char_names)}），只需描述动态元素。\n\n")
            user_parts.append("【重要】不要描述人物的外貌特征（年龄、性别、发型、脸型、肤色、体型、服装等静态特征）。\n")
            user_parts.append("只描述：\n")
            user_parts.append("1. 动作（站立、行走、坐下、转身等具体动作）\n")
            user_parts.append("2. 表情（微笑、严肃、惊讶、沉思等具体表情）\n")
            user_parts.append("3. 姿势（手部动作、身体姿态）\n")
            user_parts.append("4. 场景环境（地点、物品、光线、氛围）\n")
            user_parts.append("5. 镜头景别（全身照/中景/特写）\n\n")
        elif roles:
            user_parts.append(f"【‼️ 人物设定档案 - 必须严格遵守】\n{roles}\n\n")
            user_parts.append("⚠️ 人物一致性规则（极其重要）：\n")
            user_parts.append("1. **人物-特征绑定**：以上每个人物的名字与其外貌、服饰特征是永久绑定的\n")
            user_parts.append("2. **按名字匹配**：当分镜中提到某个人物的名字时，必须使用该人物在设定中的所有特征\n")
            user_parts.append("3. **选择性出现**：只描述当前分镜中实际出现的人物，未出现的人物不要描述\n")
            user_parts.append("4. **再次出现一致**：如果某人物在前面的场景没出现，但在当前场景出现，必须使用设定中该人物的特征\n")
            user_parts.append("5. **多人物区分**：如果场景中有多个人物，要清楚区分每个人，按各自的名字使用对应的特征\n")
            user_parts.append("6. **特征不混淆**：绝不允许将A人物的特征用在B人物身上，每个人物的特征独立且固定\n\n")
            user_parts.append("例如：\n")
            user_parts.append("- 如果分镜说「李明走进房间」→ 只描述李明，使用李明的设定特征\n")
            user_parts.append("- 如果分镜说「王芳和李明对话」→ 描述两人，分别使用各自的设定特征\n")
            user_parts.append("- 如果分镜说「一个空房间」→ 不描述任何人物，只描述环境\n")
            user_parts.append("- 如果王芳在前3个场景没出现，第5个场景才出现 → 第5个场景中王芳的特征与设定完全一致\n\n")
        else:
            user_parts.append("【人物设定】从故事上下文和分镜描述中提取人物特征，为每个人物建立档案，")
            user_parts.append("并在该人物每次出现时保持特征一致。不同人物要清楚区分，不要混淆。\n\n")

        user_parts.append(f"【当前分镜描述】\n{current_shot}\n\n")
        user_parts.append(f"【故事上下文】\n{story_text[:context_length] if story_text else '无相关上下文'}\n\n")
        if scene:
            user_parts.append(f"【场景设定】\n{scene}\n\n")

        if not has_photo:
            user_parts.append("【描述生成要求】\n")
            user_parts.append("1. **识别当前场景人物**：仔细阅读当前分镜描述，识别场景中出现的具体人物（根据名字或角色）\n")
            user_parts.append("2. **匹配人物特征**：为每个出现的人物，从人物设定档案中找到对应的特征\n")
            user_parts.append("3. **只描述在场人物**：只描述当前分镜中实际出现的人物，不在场的人物不要提及\n")
            user_parts.append("4. **保持特征一致**：每个人物的年龄、性别、发型、发色、肤色、体型、五官、服饰必须与设定完全一致\n")
            user_parts.append("5. **动态元素变化**：根据分镜要求，只改变表情、动作、姿态等动态元素，静态特征保持不变\n")
            user_parts.append("6. **多人物区分**：如果场景中有多人，要清楚描述每个人的特征，不要混淆或遗漏\n")
            user_parts.append("7. **服饰一致**：除非分镜明确说明换装，否则服装款式、颜色、材质保持一致\n")
            user_parts.append("8. **细节补充**：如果设定中缺少某些细节，可适当添加，但要符合该人物的身份和场景，且后续保持一致\n\n")

        user_parts.append(f"请生成中文图片描述（{char_limit}），体现{img_type}风格。")
        return "".join(user_parts)

    def _truncate_current_shot_description(self, description: str, max_length: int) -> str:
        """按长度截断生成描述，优先在中文标点处停止。"""
        if len(description) <= max_length:
            return description

        truncated = description[:max_length]
        last_punct = max(truncated.rfind("。"), truncated.rfind("，"), truncated.rfind("、"))
        if last_punct > int(max_length * 0.8):
            return truncated[:last_punct + 1]
        return truncated

    def _run_current_shot_prompt_task(self, context: dict) -> None:
        """后台执行当前分镜图片描述生成。"""
        try:
            self.set_busy(True)
            mode_text = "图生图（只生成动作表情）" if context["has_photo"] else "文生图（完整描述）"
            self._ui(
                self.status.set,
                f"📸 正在使用 {context['selected_api']} 生成图片描述（{mode_text}，第{context['selected_index'] + 1}个分镜）...",
            )
            self._header_status("生成图片描述...", "📸")

            client = _resolve_deepseek_client_cls()(
                api_key=context["api_key"],
                base_url=context["base_url"],
                model=context["model"],
            )

            context_length = 500 if context["is_hunyuan"] else 1000
            user_prompt = self._build_current_shot_user_prompt(
                img_type=context["img_type"],
                current_shot=context["current_shot"],
                story_text=context["story_text"],
                scene=context["scene"],
                roles=context["roles"],
                selected_characters=context["selected_characters"],
                has_photo=context["has_photo"],
                context_length=context_length,
                char_limit=context["char_limit"],
            )
            resp = client.chat(
                [
                    {"role": "system", "content": context["inst"]},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=max(0.5, self.temperature.get() - 0.1),
            )

            self._ui(self.status.set, "✅ 更新图片描述...")
            max_desc_length = 200 if context["is_hunyuan"] else 500
            description = self._truncate_current_shot_description(resp.strip(), max_desc_length)

            self._ui(self.img_txt_prompt_cn.delete, "1.0", END)
            self._ui(self.img_txt_prompt_cn.insert, END, description)

            char_count = len(description)
            api_type = "腾讯混元简洁版" if context["is_hunyuan"] else "精简版"
            self._ui(
                self.status.set,
                f"✨ 已生成【{context['img_type']}】{api_type}图片描述（{char_count}字，可编辑后生成）",
            )
            self._header_status("图片描述完成", "✅")
            self.after(100, lambda: self._auto_select_characters_from_shot(context["current_shot"], description))
        except Exception as exc:
            self._ui(messagebox.showerror, "错误", str(exc))
            self._header_status("生成描述失败", "❌")
        finally:
            self.set_busy(False)

    
    def _on_img_prompt_from_shots(self) -> None:
        """从分镜列表生成提示词"""
        if not hasattr(self, 'parsed_shots') or not self.parsed_shots:
            messagebox.showwarning("提示", "请先生成分镜列表")
            return
        shots = "\n".join(self.parsed_shots)
        story_text = self.output.get("1.0", END).strip() if hasattr(self, 'output') else ""
        scene = self.img_entry_scene.get().strip() if hasattr(self, 'img_entry_scene') else ""
        roles = self.img_txt_roles.get("1.0", END).strip() if hasattr(self, 'img_txt_roles') else ""
        
        def task():
            try:
                self.set_busy(True)
                self._ui(self.status.set, "根据分镜生成提示词中...")
                fallback_provider = None
                if hasattr(self, 'quick_story_api'):
                    fallback_provider = self.quick_story_api.get()
                if not fallback_provider and hasattr(self, 'api_preset'):
                    fallback_provider = self.api_preset.get()
                fallback_model = None
                if hasattr(self, 'story_model_var'):
                    fallback_model = self.story_model_var.get()
                elif hasattr(self, 'model'):
                    fallback_model = self.model.get()
                
                api_config = self._resolve_task_api("image_prompt_from_shots", fallback_provider=fallback_provider, fallback_model=fallback_model)
                if not _sanitize(api_config.get("key", "")):
                    self._ui(messagebox.showwarning, "提示", "请先在设置页配置用于生成提示词的API Key")
                    return
                client = _resolve_deepseek_client_cls()( 
                    api_key=_sanitize(api_config.get("key", "")),
                    base_url=_sanitize(api_config.get("base_url", "")),
                    model=_sanitize(api_config.get("model", "")),
                )
                inst = (
                    "你是资深视觉提示词工程师。基于分镜清单与故事上下文，输出单段英文提示词用于文生图，"
                    "确保人物与故事中的设定一致（面部/发型/年龄/服饰/气质），并与所选场景匹配。包含场景/构图/主体细节/表情动作/光线镜头/风格与质感。"
                    "禁止 Markdown，仅输出英文提示词。"
                )
                user = (
                    f"分镜清单：\n{shots}\n\n"
                    f"故事上下文：\n{story_text}\n\n"
                    f"补充场景：{scene or '无'}\n人物设定：{roles or '无'}\n"
                    "请给出最终英文提示词。"
                )
                resp = client.chat([
                    {"role": "system", "content": inst},
                    {"role": "user", "content": user},
                ], temperature=max(0.4, self.temperature.get() - 0.2))
                self._ui(self.img_txt_prompt.delete, "1.0", END)
                self._ui(self.img_txt_prompt.insert, END, resp.strip())
                self._ui(self.status.set, "已根据分镜生成提示词")
            except Exception as e:
                self._ui(messagebox.showerror, "错误", str(e))
            finally:
                self.set_busy(False)
        
        import threading
        threading.Thread(target=task, daemon=True).start()

    

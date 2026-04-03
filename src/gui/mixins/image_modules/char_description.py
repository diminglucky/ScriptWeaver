"""
人物外貌设计功能 - 基于2025最佳实践优化

核心改进：
1. 生成角色DNA（可复用的核心提示词模板）
2. 生成结构化视觉特征
3. 生成禁止漂移说明
"""

from tkinter import DISABLED, NORMAL, END, messagebox
import threading

from ...models.character import Character, CharacterProfile, VisualFeatures, CharacterDNA
from ...services.ai_service import create_ai_service
from ...helpers.character_prompt_builder import CharacterPromptBuilder


class CharacterDescriptionMixin:
    """人物外貌设计功能"""
    
    def _on_generate_character_description(self) -> None:
        """为选中人物设计外貌"""
        context = self._get_selected_character_context()
        if not context:
            return

        index, char, character_name, profile_data = context
        story_text = self.output.get("1.0", END).strip()
        api_config = self._resolve_character_description_api_config()
        selected_model = api_config.get("model", "")
        if selected_model:
            print(f"🤖 使用模型: {selected_model}")

        ai_service = create_ai_service({"__route__": api_config}, "__route__")
        if not ai_service:
            messagebox.showwarning("提示", "API Key 为空，请在配置页面设置")
            return

        self.char_btn_gen_desc.config(state=DISABLED)
        self.status.set(f"🎨 正在为\"{character_name}\"设计外貌...")
        self._header_status("设计外貌...", "🎨")

        threading.Thread(
            target=lambda: self._run_character_description_task(
                index=index,
                char=char,
                character_name=character_name,
                profile_data=profile_data,
                story_text=story_text,
                ai_service=ai_service,
            ),
            daemon=True,
        ).start()

    def _get_selected_character_context(self):
        selection = self.char_listbox.curselection()
        if not selection:
            return None

        index = selection[0]
        char = self.character_list[index]
        if isinstance(char, Character):
            return index, char, char.name, {
                "role": char.profile.role,
                "gender": char.profile.gender,
                "age_hint": char.profile.age_hint,
                "identity": char.profile.identity,
                "personality": char.profile.personality,
                "atmosphere": char.profile.atmosphere,
                "story_role": char.profile.story_role,
                "appearance_hints": char.profile.appearance_hints,
            }
        return index, char, char.get("name", ""), char.get("character_profile", {})

    def _resolve_character_description_api_config(self) -> dict:
        fallback_provider = self._get_character_description_fallback_provider()
        fallback_model = self._get_character_description_fallback_model()
        return self._resolve_task_api(
            "character_description",
            fallback_provider=fallback_provider,
            fallback_model=fallback_model,
        )

    def _get_character_description_fallback_provider(self):
        if hasattr(self, "quick_story_api"):
            value = self.quick_story_api.get()
            if value:
                return value
        if hasattr(self, "api_preset"):
            return self.api_preset.get()
        return None

    def _get_character_description_fallback_model(self):
        if hasattr(self, "char_model_var"):
            return self.char_model_var.get()
        if hasattr(self, "story_model_var"):
            return self.story_model_var.get()
        if hasattr(self, "model"):
            return self.model.get()
        return None

    def _run_character_description_task(
        self,
        index: int,
        char,
        character_name: str,
        profile_data: dict,
        story_text: str,
        ai_service,
    ) -> None:
        try:
            result = ai_service.design_character_appearance(
                character_name=character_name,
                profile=profile_data,
                story_text=story_text,
            )
            description, visual_data, dna_prompt = self._parse_character_description_result(result)
            self._apply_character_description_result(
                index=index,
                char=char,
                description=description,
                visual_data=visual_data,
                dna_prompt=dna_prompt,
            )
            self._ui(self._save_all_characters_info)
            self._ui(self._refresh_character_description_ui, index)
            self._ui(self.status.set, f"✅ 已为\"{character_name}\"设计外貌并生成角色DNA")
            self._header_status("设计完成", "✅")
        except Exception as e:
            import traceback

            traceback.print_exc()
            self._ui(messagebox.showerror, "错误", f"设计失败: {str(e)}")
            self._ui(self.status.set, "❌ 设计失败")
        finally:
            self._ui(self.char_btn_gen_desc.config, state=NORMAL)

    def _parse_character_description_result(self, result: dict) -> tuple[str, dict, str]:
        raw_description = result.get("description", "")
        description = CharacterPromptBuilder.extract_appearance_only(raw_description)
        visual_data = result.get("visual_features", {})
        raw_dna_prompt = result.get("dna_prompt", "")
        dna_prompt = CharacterPromptBuilder.extract_appearance_only(raw_dna_prompt)
        dna_prompt = CharacterPromptBuilder.sanitize_for_image_safety(
            dna_prompt, language="en"
        )
        return description, visual_data, dna_prompt

    def _apply_character_description_result(
        self,
        index: int,
        char,
        description: str,
        visual_data: dict,
        dna_prompt: str,
    ) -> None:
        if isinstance(char, Character):
            self._apply_character_object_description(char, description, visual_data, dna_prompt)
            return
        self.character_list[index]["description"] = description
        if visual_data:
            self.character_list[index]["visual_features"] = visual_data
        if dna_prompt:
            self.character_list[index]["dna_prompt"] = dna_prompt

    def _apply_character_object_description(
        self,
        char: Character,
        description: str,
        visual_data: dict,
        dna_prompt: str,
    ) -> None:
        char.description = description
        if visual_data:
            char.visual = VisualFeatures(
                face_shape=visual_data.get("face_shape", ""),
                eye_features=visual_data.get("eye_features", ""),
                nose_features=visual_data.get("nose_features", ""),
                skin_tone=visual_data.get("skin_tone", ""),
                body_type=visual_data.get("body_type", ""),
                hair_style=visual_data.get("hair_style", ""),
                hair_color=visual_data.get("hair_color", ""),
                default_outfit=visual_data.get("default_outfit", ""),
                unique_marks=visual_data.get("unique_marks", []),
                do_not_change=visual_data.get("do_not_change", []),
            )
        if dna_prompt:
            char.dna.core_prompt = dna_prompt
        else:
            char.build_dna()
        char.dna.negative_features = visual_data.get("do_not_change", [])

    def _refresh_character_description_ui(self, index: int) -> None:
        self._update_character_description_display(index)
        self._update_character_listbox()
        self.char_listbox.selection_set(index)
    
    def _update_character_description_display(self, index: int) -> None:
        """更新描述显示"""
        char = self.character_list[index]
        
        if isinstance(char, Character):
            description = char.description
            visual = char.visual
            dna = char.dna
            char_id = char.character_id
        else:
            description = char.get("description", "")
            visual_data = char.get("visual_features", {})
            visual = VisualFeatures(**visual_data) if visual_data else None
            dna = None
            char_id = char.get("character_id", "")
        
        self.char_txt_desc.config(state=NORMAL)
        self.char_txt_desc.delete("1.0", END)
        
        display = ""
        
        # 显示角色DNA信息
        if dna and dna.core_prompt:
            display += "🧬 ══════ 角色DNA ══════\n"
            display += f"🆔 角色ID: {char_id}\n"
            display += f"📝 核心提示词:\n{dna.core_prompt}\n"
            if dna.negative_features:
                display += f"🚫 禁止漂移: {', '.join(dna.negative_features)}\n"
            display += "════════════════════════\n\n"
        
        # 显示视觉特征
        if visual and (visual.face_shape or visual.unique_marks):
            display += "👤 ══════ 视觉特征 ══════\n"
            if visual.face_shape:
                display += f"脸型: {visual.face_shape}\n"
            if visual.eye_features:
                display += f"眼睛: {visual.eye_features}\n"
            if visual.body_type:
                display += f"体型: {visual.body_type}\n"
            if visual.hair_color and visual.hair_style:
                display += f"发型: {visual.hair_color} {visual.hair_style}\n"
            if visual.unique_marks:
                display += f"🎯 独特标记: {', '.join(visual.unique_marks)}\n"
            display += "════════════════════════\n\n"
        
        display += "📝 ══════ 外貌描述 ══════\n\n"
        display += description
        
        self.char_txt_desc.insert("1.0", display)
        self.char_txt_desc.config(state=DISABLED)
        
        self.char_btn_copy_desc.config(state=NORMAL)
        self.char_btn_gen_photo.config(state=NORMAL)
    
    def _on_copy_character_description(self) -> None:
        """复制描述到剪贴板"""
        description = self.char_txt_desc.get("1.0", END).strip()
        if description:
            self.clipboard_clear()
            self.clipboard_append(description)
            self.status.set("📋 已复制到剪贴板")

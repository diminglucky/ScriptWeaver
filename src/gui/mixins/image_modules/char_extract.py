"""
人物提取功能 - 从故事中提取角色设定
"""

from tkinter import DISABLED, NORMAL, END, messagebox
import threading

from ...models.character import Character, CharacterProfile
from ...services.ai_service import create_ai_service


class CharacterExtractMixin:
    """人物提取功能"""
    
    def _on_extract_characters(self) -> None:
        """从故事中提取角色设定"""
        story_text = self.output.get("1.0", END).strip()
        if not story_text:
            messagebox.showwarning("提示", "请先生成故事内容！")
            return
        
        # 人物提取：根据模型路由选择 API
        fallback_provider = None
        if hasattr(self, 'quick_story_api'):
            fallback_provider = self.quick_story_api.get()
        if not fallback_provider and hasattr(self, 'api_preset'):
            fallback_provider = self.api_preset.get()
        fallback_model = None
        if hasattr(self, 'char_model_var'):
            fallback_model = self.char_model_var.get()
        elif hasattr(self, 'story_model_var'):
            fallback_model = self.story_model_var.get()
        elif hasattr(self, 'model'):
            fallback_model = self.model.get()
        
        api_config = self._resolve_task_api("character_extract", fallback_provider=fallback_provider, fallback_model=fallback_model)
        selected_api = api_config.get("provider", "")
        selected_model = api_config.get("model", "")
        if selected_model:
            print(f"🤖 使用模型: {selected_model}")
        
        ai_service = create_ai_service({"__route__": api_config}, "__route__")
        if not ai_service:
            messagebox.showwarning("提示", "API Key 为空，请在配置页面设置")
            return
        
        self.char_btn_extract.config(state=DISABLED)
        self.char_btn_refresh.config(state=DISABLED)
        self.status.set("🔍 正在分析故事，提取人物设定...")
        if hasattr(self, 'update_header_status'):
            self.update_header_status("分析人物...", "🔍")
        
        def extract_thread():
            try:
                characters_data = ai_service.extract_characters(story_text)
                
                self.character_list = []
                for data in characters_data:
                    char = Character(name=data.get("name", "未知"))
                    char.profile = CharacterProfile(
                        role=data.get("role", ""),
                        gender=data.get("gender", ""),
                        age_hint=data.get("age_hint", ""),
                        identity=data.get("identity", ""),
                        personality=data.get("personality", []),
                        atmosphere=data.get("atmosphere", ""),
                        story_role=data.get("story_role", ""),
                        appearance_hints=data.get("appearance_hints", ""),
                    )
                    self.character_list.append(char)
                
                self.after(0, lambda: self._save_all_characters_info())
                self.after(0, lambda: self._update_character_listbox())
                
                count = len(self.character_list)
                self.after(0, lambda: self.status.set(f"✅ 成功分析 {count} 个人物的设定"))
                if hasattr(self, 'update_header_status'):
                    self.after(0, lambda: self.update_header_status("分析完成", "✅"))
                
            except Exception as e:
                import traceback
                traceback.print_exc()
                self.after(0, lambda: messagebox.showerror("错误", f"提取失败: {str(e)}"))
                self.after(0, lambda: self.status.set("❌ 提取失败"))
            finally:
                self.after(0, lambda: self.char_btn_extract.config(state=NORMAL))
                self.after(0, lambda: self.char_btn_refresh.config(state=NORMAL))
                pass
        
        threading.Thread(target=extract_thread, daemon=True).start()
    
    def _update_character_listbox(self) -> None:
        """更新人物列表框"""
        self.char_listbox.delete(0, END)
        
        role_icons = {"主角": "⭐", "反派": "👿", "配角": "👤", "龙套": "·"}
        
        for char in self.character_list:
            if isinstance(char, Character):
                role, name, has_desc = char.profile.role, char.name, bool(char.description)
                has_dna = bool(char.dna.core_prompt)
            else:
                profile = char.get("character_profile", {})
                role, name = profile.get("role", ""), char.get("name", "")
                has_desc = bool(char.get("description"))
                has_dna = False
            
            icon = role_icons.get(role, "")
            display = f"{icon} {name}" if icon else name
            if has_dna:
                display += " 🧬"  # 有DNA
            elif has_desc:
                display += " ✓"
            
            self.char_listbox.insert(END, display)
        
        if self.character_list:
            self.char_listbox.selection_set(0)
            self.char_listbox.event_generate("<<ListboxSelect>>")
            self._update_reference_character_list()
    
    def _on_character_selected(self, event=None) -> None:
        """选择人物时的回调"""
        selection = self.char_listbox.curselection()
        if not selection:
            return
        
        index = selection[0]
        if index < 0 or index >= len(self.character_list):
            return
        
        char = self.character_list[index]
        
        if isinstance(char, Character):
            name, description, profile = char.name, char.description, char.profile
            has_dna = bool(char.dna.core_prompt)
        else:
            name = char.get("name", "")
            description = char.get("description", "")
            profile_data = char.get("character_profile", {})
            profile = CharacterProfile(**profile_data) if profile_data else None
            has_dna = False
        
        self.char_txt_desc.config(state=NORMAL)
        self.char_txt_desc.delete("1.0", END)
        
        if description:
            display = ""
            if has_dna and isinstance(char, Character):
                display += f"🧬 角色DNA已生成\n"
                display += f"🆔 ID: {char.character_id}\n"
                if char.dna.core_prompt:
                    display += f"📝 核心: {char.dna.core_prompt[:60]}...\n"
                display += "\n═══════ 外貌描述 ═══════\n\n"
            display += description
            self.char_txt_desc.insert("1.0", display)
            self.char_btn_copy_desc.config(state=NORMAL)
            self.char_btn_gen_photo.config(state=NORMAL)
            if hasattr(self, 'char_btn_turnaround'):
                self.char_btn_turnaround.config(state=NORMAL)
        else:
            display = f"【{name}】尚未设计外貌\n\n"
            if profile:
                display += "══════ 人物设定 ══════\n"
                if profile.role: display += f"📌 角色：{profile.role}\n"
                if profile.gender: display += f"👤 性别：{profile.gender}\n"
                if profile.age_hint: display += f"🎂 年龄：{profile.age_hint}\n"
                if profile.identity: display += f"💼 身份：{profile.identity}\n"
                if profile.personality:
                    p = profile.personality
                    display += f"💫 性格：{', '.join(p) if isinstance(p, list) else p}\n"
                if profile.atmosphere: display += f"🌟 气质：{profile.atmosphere}\n"
                display += "\n══════════════════════\n\n"
            display += "💡 点击「设计外貌」按钮，AI将根据人物设定创造性地设计外貌"
            self.char_txt_desc.insert("1.0", display)
            self.char_btn_copy_desc.config(state=DISABLED)
            self.char_btn_gen_photo.config(state=DISABLED)
            if hasattr(self, 'char_btn_turnaround'):
                self.char_btn_turnaround.config(state=DISABLED)
        
        self.char_txt_desc.config(state=DISABLED)
        
        if self.current_project:
            self.char_btn_view_gallery.config(state=NORMAL)
            if hasattr(self, 'char_btn_generate_sheet'):
                self.char_btn_generate_sheet.config(state=NORMAL)
        else:
            self.char_btn_view_gallery.config(state=DISABLED)
            if hasattr(self, 'char_btn_generate_sheet'):
                self.char_btn_generate_sheet.config(state=DISABLED)
        
        self.char_btn_gen_desc.config(state=NORMAL)
    
    def _get_selected_reference_characters(self) -> list:
        """获取选中的参考人物列表"""
        selected_indices = self.ref_character_listbox.curselection()
        selected_characters = []
        
        for idx in selected_indices:
            item_text = self.ref_character_listbox.get(idx)
            if item_text.startswith("✅ ") or item_text.startswith("🧬 "):
                char_name = item_text[2:].strip()
                for char in self.character_list:
                    if isinstance(char, Character):
                        if char.name == char_name and char.primary_photo:
                            selected_characters.append({
                                "name": char_name,
                                "photo_path": char.primary_photo,
                                "description": char.description,
                                "dna": char.dna.core_prompt if char.dna else "",
                            })
                            break
                    else:
                        if char.get("name") == char_name and char.get("photo_path"):
                            selected_characters.append({
                                "name": char_name,
                                "photo_path": char["photo_path"],
                                "description": char.get("description", ""),
                            })
                            break
        
        return selected_characters

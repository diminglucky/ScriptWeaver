"""人物详情编辑功能"""

from tkinter import messagebox, NORMAL, DISABLED
import json
from pathlib import Path

from .character_detail_dialog import CharacterDetailDialog


class CharacterDetailMixin:
    """人物详情编辑功能"""
    
    def _on_edit_character_detail(self) -> None:
        """编辑选中人物的详细信息"""
        selection = self.char_listbox.curselection()
        if not selection:
            messagebox.showwarning("提示", "请先从列表中选择一个人物！")
            return
        
        index = selection[0]
        character = self.character_list[index]
        character_name = character["name"]
        
        # 检查当前项目
        if not self.current_project:
            messagebox.showwarning("提示", "请先创建或打开一个项目！")
            return
        
        # 加载现有的人物详情数据
        char_data_file = self.current_project.project_dir / "characters" / "characters_info.json"
        char_data = {}
        
        if char_data_file.exists():
            try:
                with open(char_data_file, 'r', encoding='utf-8') as f:
                    all_char_data = json.load(f)
                    char_data = all_char_data.get(character_name, {})
            except Exception as e:
                print(f"加载人物数据失败: {e}")
        
        # 如果没有详细数据，使用基本描述初始化
        if not char_data or not char_data.get("appearance"):
            char_data = {
                "name": character_name,
                "description": character.get("description", ""),
                "appearance": {},
                "outfit": {},
                "expressions": {},
                "actions": {}
            }
        
        # 打开编辑对话框
        dialog = CharacterDetailDialog(self, char_data, character_name)
        result = dialog.show()
        
        if result:
            # 保存更新后的数据
            self._save_character_detail(character_name, result)
            
            # 更新列表中的描述（如果有修改）
            if result.get("description"):
                character["description"] = result["description"]
                self.char_txt_desc.config(state=NORMAL)
                self.char_txt_desc.delete("1.0", "end")
                self.char_txt_desc.insert("1.0", result["description"])
                self.char_txt_desc.config(state=DISABLED)
            
            messagebox.showinfo("成功", f"已保存 {character_name} 的详细信息！")
    
    def _save_character_detail(self, character_name: str, char_data: dict) -> None:
        """保存人物详细信息到JSON文件"""
        try:
            if not self.current_project:
                return
            
            # 确保characters目录存在
            char_dir = self.current_project.project_dir / "characters"
            char_dir.mkdir(parents=True, exist_ok=True)
            
            char_data_file = char_dir / "characters_info.json"
            
            # 读取现有数据
            all_char_data = {}
            if char_data_file.exists():
                try:
                    with open(char_data_file, 'r', encoding='utf-8') as f:
                        all_char_data = json.load(f)
                except:
                    pass
            
            # 更新当前人物的数据
            all_char_data[character_name] = char_data
            
            # 保存到文件
            with open(char_data_file, 'w', encoding='utf-8') as f:
                json.dump(all_char_data, f, ensure_ascii=False, indent=2)
            
            print(f"✅ 已保存 {character_name} 的详细信息到 {char_data_file}")
            
        except Exception as e:
            print(f"❌ 保存人物详情失败: {e}")
            import traceback
            traceback.print_exc()



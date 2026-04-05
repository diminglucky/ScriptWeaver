"""人物处理功能"""

from tkinter import filedialog, messagebox

from PIL import Image, ImageTk

from .char_photo_generation_mixin import CharacterPhotoGenerationMixin
from .char_turnaround_mixin import CharacterTurnaroundMixin


class CharacterPhotoMixin(CharacterPhotoGenerationMixin, CharacterTurnaroundMixin):
    """人物 char_photo 功能"""
    def _update_character_photo_preview(self, img: Image.Image) -> None:
        """更新人物照片预览"""
        canvas_width = self.char_canvas.winfo_width()
        canvas_height = self.char_canvas.winfo_height()
        
        # 如果Canvas还没有初始化大小，使用默认值
        if canvas_width <= 1:
            canvas_width = 400
        if canvas_height <= 1:
            canvas_height = 400
        
        img_width, img_height = img.size
        
        # 计算缩放比例
        width_ratio = canvas_width / img_width
        height_ratio = canvas_height / img_height
        scale_ratio = min(width_ratio, height_ratio, 1.0)
        
        new_w = int(img_width * scale_ratio)
        new_h = int(img_height * scale_ratio)
        
        # 缩放图片
        resized_img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
        
        # 转换为PhotoImage
        self.character_preview_photo = ImageTk.PhotoImage(resized_img)
        
        # 更新Label
        self.char_preview.configure(image=self.character_preview_photo, text="")
        
        # 更新Canvas的滚动区域 - 确保图片可以完全滚动查看
        # 如果图片比Canvas大，设置滚动区域为图片尺寸
        # 如果图片比Canvas小，设置滚动区域为Canvas尺寸
        scroll_width = max(new_w, canvas_width)
        scroll_height = max(new_h, canvas_height)
        self.char_canvas.configure(scrollregion=(0, 0, scroll_width, scroll_height))
        
        # 居中显示
        if new_w < canvas_width:
            x_offset = (canvas_width - new_w) // 2
        else:
            x_offset = 0
        
        if new_h < canvas_height:
            y_offset = (canvas_height - new_h) // 2
        else:
            y_offset = 0
        
        self.char_canvas.coords(self.char_canvas_window, x_offset, y_offset)
    
    
    
    
    def _auto_save_character_photo(self, index: int, img: Image.Image, character_name: str) -> str:
        """自动保存人物照片到当前项目的characters文件夹，并保存描述信息"""
        try:
            import re
            import json
            from pathlib import Path
            
            # 检查是否有当前项目
            if not self.current_project:
                messagebox.showwarning("提示", "请先创建或打开一个项目，人物照片将保存到项目目录中")
                return ""
            
            # 确定保存目录：项目目录/characters/
            self.character_photos_dir = self.current_project.project_dir / "characters"
            
            # 确保文件夹存在
            if not self.character_photos_dir.exists():
                print(f"📁 创建人物照片文件夹：{self.character_photos_dir}")
            self.character_photos_dir.mkdir(parents=True, exist_ok=True)
            
            # 验证文件夹创建成功
            if not self.character_photos_dir.exists():
                print(f"❌ 文件夹创建失败：{self.character_photos_dir}")
                return ""
            
            # 生成文件名（只使用人物名称，不加时间戳，这样同一人物会覆盖旧照片）
            clean_name = re.sub(r'[^\w\s\u4e00-\u9fff-]', '', character_name)
            filename = f"{clean_name}.png"
            
            save_path = self.character_photos_dir / filename
            print(f"💾 准备保存到：{save_path}")
            
            img.save(str(save_path))
            
            # 验证文件保存成功
            if not save_path.exists():
                print(f"❌ 文件保存失败：{save_path}")
                return ""
            
            # 更新人物列表中的照片路径（兼容新旧格式）
            from ...models.character import Character
            char = self.character_list[index]
            if isinstance(char, Character):
                char.primary_photo = str(save_path)
                if str(save_path) not in char.photo_paths:
                    char.photo_paths.append(str(save_path))
                # 更新DNA中的锚定图
                if char.dna and not char.dna.anchor_image:
                    char.dna.anchor_image = str(save_path)
            else:
                char["photo_path"] = str(save_path)
            
            # 保存人物描述到 JSON 文件
            characters_info_path = self.character_photos_dir / "characters_info.json"
            
            # 读取现有的描述信息（如果存在）
            characters_info = {}
            if characters_info_path.exists():
                try:
                    with open(characters_info_path, 'r', encoding='utf-8') as f:
                        characters_info = json.load(f)
                except Exception:
                    pass
            
            # 更新当前人物的描述
            characters_info[character_name] = {
                "description": self.character_list[index].get("description", ""),
                "photo_path": str(save_path)
            }
            
            # 保存到文件
            with open(characters_info_path, 'w', encoding='utf-8') as f:
                json.dump(characters_info, f, ensure_ascii=False, indent=2)
            
            print(f"✅ 人物照片已自动保存到项目：{save_path}")
            print(f"📊 文件大小：{save_path.stat().st_size / 1024:.2f} KB")
            print(f"💾 人物描述已保存到：{characters_info_path}")
            return str(save_path)
            
        except Exception as e:
            print(f"❌ 自动保存失败：{str(e)}")
            import traceback
            traceback.print_exc()
            return ""
    
    
    
    
    def _auto_save_character_photo_with_name(self, img: Image.Image, character_name: str, filename: str) -> str:
        """自动保存人物照片（支持自定义文件名，用于多角度生成）"""
        try:
            from pathlib import Path
            
            # 检查是否有当前项目
            if not self.current_project:
                return ""
            
            # 确定保存目录：项目目录/characters/
            self.character_photos_dir = self.current_project.project_dir / "characters"
            self.character_photos_dir.mkdir(parents=True, exist_ok=True)
            
            # 使用提供的文件名
            save_path = self.character_photos_dir / filename
            print(f"💾 保存照片到：{save_path}")
            
            img.save(str(save_path))
            
            if save_path.exists():
                print(f"✅ 照片已保存：{save_path} ({save_path.stat().st_size / 1024:.2f} KB)")
                return str(save_path)
            else:
                print(f"❌ 文件保存失败：{save_path}")
                return ""
            
        except Exception as e:
            print(f"❌ 保存失败：{str(e)}")
            import traceback
            traceback.print_exc()
            return ""
    
    
    
    
    def _on_save_character_photo(self) -> None:
        """额外保存人物照片副本（可选）"""
        if not self.character_last_image:
            messagebox.showwarning("提示", "没有可保存的照片")
            return
        
        selection = self.char_listbox.curselection()
        if not selection:
            return
        
        index = selection[0]
        character = self.character_list[index]
        character_name = character["name"]
        
        # 弹出保存对话框，允许用户保存副本到其他位置
        file_path = filedialog.asksaveasfilename(
            defaultextension=".png",
            filetypes=[("PNG图片", "*.png"), ("JPEG图片", "*.jpg"), ("所有文件", "*.*")],
            initialfile=f"{character_name}_photo.png"
        )
        
        if file_path:
            try:
                self.character_last_image.save(file_path)
                self.status.set(f"✅ 照片副本已保存：{file_path}")
                messagebox.showinfo("成功", f"照片副本已保存到：\n{file_path}")
            except Exception as e:
                messagebox.showerror("错误", f"保存失败：{str(e)}")
    

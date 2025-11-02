"""
增强的项目管理器 - 保存和加载所有生成的内容
"""

import os
import json
import shutil
from datetime import datetime
from typing import Dict, Any, Optional
import tkinter as tk
from tkinter import messagebox


class EnhancedProjectManager:
    """增强的项目管理功能"""
    
    def save_complete_project(self) -> bool:
        """
        保存完整的项目数据，包括：
        - 故事内容
        - 剧本
        - 分镜
        - 人物设定
        - 生成的图片
        - 所有配置
        """
        if not hasattr(self, 'current_project') or not self.current_project:
            return False
        
        # 兼容不同类型的项目对象
        if hasattr(self.current_project, 'project_dir'):
            project_path = str(self.current_project.project_dir)
        elif isinstance(self.current_project, dict):
            project_path = self.current_project.get('path')
        else:
            project_path = str(self.current_project)
        
        if not project_path:
            return False
        
        try:
            # 创建项目数据结构
            if hasattr(self.current_project, 'metadata'):
                project_name = self.current_project.metadata.get('name', 'Unknown')
                created_time = self.current_project.metadata.get('created_at', datetime.now().isoformat())
            elif isinstance(self.current_project, dict):
                project_name = self.current_project.get('name', 'Unknown')
                created_time = self.current_project.get('created_time', datetime.now().isoformat())
            else:
                project_name = 'Unknown'
                created_time = datetime.now().isoformat()
            
            project_data = {
                "version": "2.0",
                "name": project_name,
                "created_time": created_time,
                "last_modified": datetime.now().isoformat(),
                "data": {}
            }
            
            # 1. 保存故事内容
            if hasattr(self, 'output'):
                story_content = self.output.get("1.0", tk.END).strip()
                if story_content:
                    project_data["data"]["story"] = {
                        "content": story_content,
                        "category": self.category.get() if hasattr(self, 'category') else "",
                        "style": self.style.get() if hasattr(self, 'style') else "",
                        "target_chars": self.target_chars.get() if hasattr(self, 'target_chars') else 1800
                    }
            
            # 2. 保存章节信息和目录
            if hasattr(self, 'parsed_sections') and self.parsed_sections:
                project_data["data"]["sections"] = self.parsed_sections
            if hasattr(self, 'current_outline') and self.current_outline:
                project_data["data"]["current_outline"] = self.current_outline
            
            # 3. 保存导演页面数据
            director_data = {}
            
            # 剧本
            if hasattr(self, 'current_script') and self.current_script:
                director_data["script"] = self.current_script
            elif hasattr(self, 'script_text'):
                script_content = self.script_text.get("1.0", tk.END).strip()
                if script_content:
                    director_data["script"] = script_content
            
            # 分镜
            if hasattr(self, 'current_shots') and self.current_shots:
                director_data["shots"] = self.current_shots
            
            # 一致性设定
            if hasattr(self, 'consistency_data') and self.consistency_data:
                director_data["consistency"] = self.consistency_data
            
            # 视频提示词
            if hasattr(self, 'video_prompt_text'):
                prompt_content = self.video_prompt_text.get("1.0", tk.END).strip()
                if prompt_content:
                    director_data["video_prompt"] = prompt_content
            
            if director_data:
                project_data["data"]["director"] = director_data
            
            # 4. 保存图片生成相关数据
            image_data = {}
            
            # 人物列表
            if hasattr(self, 'character_list') and self.character_list:
                image_data["characters"] = self.character_list
            
            # 分镜描述
            if hasattr(self, 'img_txt_shots'):
                shots_content = self.img_txt_shots.get("1.0", tk.END).strip()
                if shots_content:
                    image_data["shot_descriptions"] = shots_content
            
            # 场景设定
            if hasattr(self, 'img_entry_scene'):
                scene = self.img_entry_scene.get().strip()
                if scene:
                    image_data["scene_setting"] = scene
            
            # 人物设定
            if hasattr(self, 'img_txt_roles'):
                roles = self.img_txt_roles.get("1.0", tk.END).strip()
                if roles:
                    image_data["role_settings"] = roles
            
            # 当前提示词
            if hasattr(self, 'img_txt_prompt_cn'):
                prompt_cn = self.img_txt_prompt_cn.get("1.0", tk.END).strip()
                if prompt_cn:
                    image_data["current_prompt_cn"] = prompt_cn
            
            if image_data:
                project_data["data"]["image_generation"] = image_data
            
            # 5. 保存API配置（不包含密钥）
            config_data = {
                "story_api": {
                    "base_url": self.base_url.get() if hasattr(self, 'base_url') else "",
                    "model": self.model.get() if hasattr(self, 'model') else "",
                    "temperature": self.temperature.get() if hasattr(self, 'temperature') else 0.7,
                    "top_k": self.top_k.get() if hasattr(self, 'top_k') else 6
                },
                "image_api": {
                    "preset": self.img_api_preset.get() if hasattr(self, 'img_api_preset') else "",
                    "size": self.img_size.get() if hasattr(self, 'img_size') else "1024x1024",
                    "type": self.img_type.get() if hasattr(self, 'img_type') else "写实照片"
                }
            }
            project_data["data"]["config"] = config_data
            
            # 6. 保存生成的图片列表
            images_info = []
            
            # 人物照片
            characters_dir = os.path.join(project_path, "characters")
            if os.path.exists(characters_dir):
                for file in os.listdir(characters_dir):
                    if file.endswith(('.png', '.jpg', '.jpeg')):
                        images_info.append({
                            "type": "character",
                            "file": file,
                            "path": os.path.join("characters", file)
                        })
            
            # 场景图片
            images_dir = os.path.join(project_path, "images")
            if os.path.exists(images_dir):
                for file in os.listdir(images_dir):
                    if file.endswith(('.png', '.jpg', '.jpeg')):
                        images_info.append({
                            "type": "scene",
                            "file": file,
                            "path": os.path.join("images", file)
                        })
            
            # 分镜图片
            shots_dir = os.path.join(project_path, "director", "shots")
            if os.path.exists(shots_dir):
                for file in os.listdir(shots_dir):
                    if file.endswith(('.png', '.jpg', '.jpeg')):
                        images_info.append({
                            "type": "shot",
                            "file": file,
                            "path": os.path.join("director", "shots", file)
                        })
            
            if images_info:
                project_data["data"]["generated_images"] = images_info
            
            # 保存主项目文件
            project_file = os.path.join(project_path, "project.json")
            with open(project_file, 'w', encoding='utf-8') as f:
                json.dump(project_data, f, ensure_ascii=False, indent=2)
            
            # 同步更新 current_project.metadata（用于刷新项目列表显示）
            if hasattr(self.current_project, 'metadata'):
                # 更新关键元数据字段
                self.current_project.metadata['updated_at'] = datetime.now().isoformat()
                
                # 从保存的数据中提取关键信息
                if "story" in project_data.get("data", {}):
                    story_data = project_data["data"]["story"]
                    self.current_project.metadata['category'] = story_data.get("category", "")
                    self.current_project.metadata['style'] = story_data.get("style", "")
                    self.current_project.metadata['target_chars'] = story_data.get("target_chars", 1800)
                
                # 保存更新后的元数据
                self.current_project._save_metadata()
                print(f"✅ 项目元数据已同步更新")
            
            # 保存状态信息
            if hasattr(self, 'status'):
                self.status.set(f"✅ 项目已保存: {project_name}")
            print(f"✅ 完整项目已保存到: {project_file}")
            
            # 自动保存标记
            self.last_save_time = datetime.now()
            
            return True
            
        except Exception as e:
            error_msg = f"保存项目失败: {str(e)}"
            if hasattr(self, 'status'):
                self.status.set(f"❌ {error_msg}")
            print(f"❌ {error_msg}")
            import traceback
            traceback.print_exc()
            return False
    
    def load_complete_project(self) -> bool:
        """
        加载完整的项目数据到UI
        """
        if not hasattr(self, 'current_project') or not self.current_project:
            return False
        
        # 兼容不同类型的项目对象
        if hasattr(self.current_project, 'project_dir'):
            project_path = str(self.current_project.project_dir)
        elif isinstance(self.current_project, dict):
            project_path = self.current_project.get('path')
        else:
            project_path = str(self.current_project)
        
        if not project_path:
            return False
        
        project_file = os.path.join(project_path, "project.json")
        
        # 检查项目文件
        if not os.path.exists(project_file):
            # 尝试加载旧版本项目
            return self._load_legacy_project(project_path)
        
        try:
            # 加载项目数据
            with open(project_file, 'r', encoding='utf-8') as f:
                project_data = json.load(f)
            
            data = project_data.get("data", {})
            
            # 1. 加载故事内容
            if "story" in data:
                story_data = data["story"]
                if hasattr(self, 'output'):
                    self.output.delete("1.0", tk.END)
                    self.output.insert("1.0", story_data.get("content", ""))
                
                # 恢复生成参数
                if hasattr(self, 'category'):
                    self.category.set(story_data.get("category", ""))
                if hasattr(self, 'style'):
                    self.style.set(story_data.get("style", ""))
                if hasattr(self, 'target_chars'):
                    self.target_chars.set(story_data.get("target_chars", 1800))
            
            # 2. 加载导演数据（剧本和分镜）
            if hasattr(self, '_load_director_data_from_project'):
                print("[DEBUG] 调用 _load_director_data_from_project")
                self._load_director_data_from_project()
            
            # 3. 加载章节信息和目录
            if "sections" in data and hasattr(self, 'parsed_sections'):
                self.parsed_sections = data["sections"]
            if "current_outline" in data and hasattr(self, 'current_outline'):
                self.current_outline = data["current_outline"]
                # 如果有章节选择器，更新它
                if hasattr(self, '_update_section_selector'):
                    self._update_section_selector()
            
            # 3. 加载导演数据
            if "director" in data:
                director_data = data["director"]
                
                # 加载剧本
                if "script" in director_data:
                    self.current_script = director_data["script"]
                    if hasattr(self, 'script_text'):
                        self.script_text.delete("1.0", tk.END)
                        self.script_text.insert("1.0", director_data["script"])
                
                # 加载分镜
                if "shots" in director_data:
                    self.current_shots = director_data["shots"]
                    if hasattr(self, 'shots_list'):
                        self._update_shots_display()
                
                # 加载一致性设定
                if "consistency" in director_data:
                    self.consistency_data = director_data["consistency"]
                    # 更新UI显示
                    char_count = len(self.consistency_data.get("characters", {}))
                    if hasattr(self, 'consistency_status_label'):
                        self.consistency_status_label.config(
                            text=f"已设定 {char_count} 个人物",
                            foreground="green"
                        )
                
                # 加载视频提示词
                if "video_prompt" in director_data and hasattr(self, 'video_prompt_text'):
                    self.video_prompt_text.delete("1.0", tk.END)
                    self.video_prompt_text.insert("1.0", director_data["video_prompt"])
            
            # 4. 加载图片生成数据
            if "image_generation" in data:
                img_data = data["image_generation"]
                
                # 加载人物列表（优先从characters_info.json加载）
                if hasattr(self, '_load_project_characters'):
                    # 使用专门的方法加载人物信息（从characters_info.json）
                    self._load_project_characters()
                elif "characters" in img_data and hasattr(self, 'character_list'):
                    # 回退到project.json中的人物数据
                    self.character_list = img_data["characters"]
                    if hasattr(self, '_update_character_listbox'):
                        self._update_character_listbox()
                    elif hasattr(self, '_update_character_display'):
                        self._update_character_display()
                
                # 加载分镜描述
                if "shot_descriptions" in img_data and hasattr(self, 'img_txt_shots'):
                    self.img_txt_shots.delete("1.0", tk.END)
                    self.img_txt_shots.insert("1.0", img_data["shot_descriptions"])
                
                # 加载场景设定
                if "scene_setting" in img_data and hasattr(self, 'img_entry_scene'):
                    self.img_entry_scene.delete(0, tk.END)
                    self.img_entry_scene.insert(0, img_data["scene_setting"])
                
                # 加载人物设定
                if "role_settings" in img_data and hasattr(self, 'img_txt_roles'):
                    self.img_txt_roles.delete("1.0", tk.END)
                    self.img_txt_roles.insert("1.0", img_data["role_settings"])
                
                # 加载当前提示词
                if "current_prompt_cn" in img_data and hasattr(self, 'img_txt_prompt_cn'):
                    self.img_txt_prompt_cn.delete("1.0", tk.END)
                    self.img_txt_prompt_cn.insert("1.0", img_data["current_prompt_cn"])
            
            # 5. 加载配置
            if "config" in data:
                config = data["config"]
                
                # 故事API配置
                if "story_api" in config:
                    story_config = config["story_api"]
                    if hasattr(self, 'base_url'):
                        self.base_url.set(story_config.get("base_url", ""))
                    if hasattr(self, 'model'):
                        self.model.set(story_config.get("model", ""))
                    if hasattr(self, 'temperature'):
                        self.temperature.set(story_config.get("temperature", 0.7))
                    if hasattr(self, 'top_k'):
                        self.top_k.set(story_config.get("top_k", 6))
                
                # 图片API配置
                if "image_api" in config:
                    img_config = config["image_api"]
                    if hasattr(self, 'img_api_preset'):
                        self.img_api_preset.set(img_config.get("preset", ""))
                    if hasattr(self, 'img_size'):
                        self.img_size.set(img_config.get("size", "1024x1024"))
                    if hasattr(self, 'img_type'):
                        self.img_type.set(img_config.get("type", "写实照片"))
            
            # 更新状态
            if hasattr(self, 'status'):
                project_name = project_data.get('name', '未命名项目')
                self.status.set(f"✅ 已加载项目: {project_name}")
            
            # 显示项目信息
            last_modified = project_data.get("last_modified", "")
            print(f"✅ 项目已完整加载: {project_data.get('name', '')}")
            if hasattr(self, 'status'):
                self.status.set(f"✅ 已加载项目: {project_data.get('name', '')}")
            
            return True
            
        except Exception as e:
            error_msg = f"加载项目失败: {str(e)}"
            print(f"❌ {error_msg}")
            if hasattr(self, 'status'):
                self.status.set(f"❌ {error_msg}")
            import traceback
            traceback.print_exc()
            return False
    
    def _load_legacy_project(self, project_path: str) -> bool:
        """加载旧版本项目（兼容性）"""
        try:
            # 尝试加载故事文件
            story_file = os.path.join(project_path, "story.txt")
            if os.path.exists(story_file) and hasattr(self, 'output'):
                with open(story_file, 'r', encoding='utf-8') as f:
                    self.output.delete("1.0", tk.END)
                    self.output.insert("1.0", f.read())
            
            # 尝试加载项目信息
            project_json = os.path.join(project_path, "project.json")
            if os.path.exists(project_json):
                with open(project_json, 'r', encoding='utf-8') as f:
                    old_data = json.load(f)
                    # 处理旧数据...
            
            # 加载导演数据
            if hasattr(self, 'load_director_project'):
                self.load_director_project(project_path)
            
            return True
            
        except Exception as e:
            print(f"加载旧版本项目失败: {str(e)}")
            return False
    
    def _update_shots_display(self):
        """更新分镜显示"""
        if hasattr(self, 'shots_list') and hasattr(self, 'current_shots'):
            self.shots_list.config(state="normal")
            self.shots_list.delete("1.0", tk.END)
            
            for i, shot in enumerate(self.current_shots, 1):
                shot_num = shot.get("shot_number", i)
                shot_type = shot.get("shot_type", "Unknown")
                description = shot.get("scene_description", "No description")
                
                shot_info = f"【镜头 {shot_num}】{shot_type}\n{description}\n\n"
                self.shots_list.insert("end", shot_info)
            
            self.shots_list.config(state="disabled")
    
    def _update_character_display(self):
        """更新人物显示（只显示名字）"""
        if hasattr(self, 'char_listbox') and hasattr(self, 'character_list'):
            self.char_listbox.delete(0, tk.END)
            for char in self.character_list:
                # 只显示人物名字，不显示描述
                self.char_listbox.insert(tk.END, char['name'])
    
    def enable_auto_save(self, interval_minutes: int = 5):
        """启用自动保存"""
        # 初始化上次保存的内容哈希
        if not hasattr(self, '_last_content_hash'):
            self._last_content_hash = None
        
        def auto_save():
            if hasattr(self, 'current_project') and self.current_project:
                # 检查是否有修改
                if self._check_for_changes():
                    success = self.save_complete_project()
                    if success:
                        timestamp = datetime.now().strftime('%H:%M:%S')
                        print(f"💾 [自动保存] {timestamp}")
                        if hasattr(self, 'status'):
                            # 短暂显示自动保存提示，然后恢复
                            old_status = self.status.get()
                            self.status.set(f"💾 自动保存完成 {timestamp}")
                            self.after(2000, lambda: self.status.set(old_status))
            
            # 继续定时保存
            self.after(interval_minutes * 60 * 1000, auto_save)
        
        # 启动自动保存
        self.after(interval_minutes * 60 * 1000, auto_save)
    
    def _check_for_changes(self) -> bool:
        """检查是否有内容变化"""
        try:
            # 获取当前内容的哈希值
            current_hash = self._get_content_hash()
            
            # 如果是第一次检查，保存哈希并返回True
            if self._last_content_hash is None:
                self._last_content_hash = current_hash
                return True
            
            # 比较哈希值
            if current_hash != self._last_content_hash:
                self._last_content_hash = current_hash
                return True
            
            return False
        except:
            # 如果出错，保守地返回True
            return True
    
    def _get_content_hash(self) -> int:
        """获取当前内容的哈希值"""
        content_parts = []
        
        # 收集所有可能变化的内容
        if hasattr(self, 'output'):
            content_parts.append(self.output.get("1.0", tk.END))
        
        if hasattr(self, 'current_script'):
            content_parts.append(str(self.current_script))
        
        if hasattr(self, 'current_shots'):
            content_parts.append(str(len(self.current_shots)) if self.current_shots else "0")
        
        if hasattr(self, 'consistency_data'):
            content_parts.append(str(len(self.consistency_data.get('characters', {}))))
        
        # 计算哈希
        return hash(tuple(content_parts))

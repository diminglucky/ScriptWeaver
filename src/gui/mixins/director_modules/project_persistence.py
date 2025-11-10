"""
项目持久化 - 保存和加载项目数据
"""

import json
from pathlib import Path
from tkinter import messagebox


class ProjectPersistenceMixin:
    """项目持久化 Mixin"""
    
    def _save_director_project(self):
        """保存导演项目数据"""
        if not hasattr(self, 'current_project') or not self.current_project:
            messagebox.showwarning("提示", "请先创建项目")
            return
        
        project_dir = Path(self.current_project.project_dir)
        
        # 保存分镜数据
        if hasattr(self, 'current_shots') and self.current_shots:
            shots_file = project_dir / "director" / "shots.json"
            shots_file.parent.mkdir(parents=True, exist_ok=True)
            
            # 将 Shot 对象转换为字典以便 JSON 序列化
            shots_list = []
            for shot in self.current_shots:
                # 检查是否是 Shot 对象（有 to_dict 方法）
                if hasattr(shot, 'to_dict'):
                    shots_list.append(shot.to_dict())
                elif isinstance(shot, dict):
                    # 已经是字典，直接使用
                    shots_list.append(shot)
                else:
                    # 其他类型，跳过
                    print(f"警告：无法序列化的分镜对象类型: {type(shot)}")
                    continue
            
            with open(shots_file, 'w', encoding='utf-8') as f:
                json.dump({"shots": shots_list}, f, ensure_ascii=False, indent=2)
        
        messagebox.showinfo("成功", "项目数据已保存")
    
    def _load_director_project(self):
        """加载导演项目数据"""
        if not hasattr(self, 'current_project') or not self.current_project:
            return
        
        project_dir = Path(self.current_project.project_dir)
        shots_file = project_dir / "director" / "shots.json"
        
        if shots_file.exists():
            try:
                with open(shots_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.current_shots = data.get('shots', [])
                    
                    # 更新下拉框（静默刷新）
                    if hasattr(self, '_refresh_shot_combo'):
                        self._refresh_shot_combo(silent=True)
                    
                    # 同时刷新预览页面下拉框
                    if hasattr(self, '_refresh_preview_shot_combo'):
                        self._refresh_preview_shot_combo()
            except Exception as e:
                print(f"加载分镜数据失败: {e}")


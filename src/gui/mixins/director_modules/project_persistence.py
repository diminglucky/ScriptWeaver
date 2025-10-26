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
            
            with open(shots_file, 'w', encoding='utf-8') as f:
                json.dump({"shots": self.current_shots}, f, ensure_ascii=False, indent=2)
        
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
            except Exception as e:
                print(f"加载分镜数据失败: {e}")


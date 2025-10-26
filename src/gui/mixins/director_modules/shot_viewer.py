"""
分镜头可视化查看器 - 独立对话框
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog


class ShotViewerDialog(tk.Toplevel):
    """分镜头查看器对话框"""
    
    def __init__(self, parent, shots: list):
        super().__init__(parent)
        self.parent = parent
        self.shots = shots
        
        self.title(f"🎬 分镜头预览 - 共 {len(self.shots)} 个镜头")
        self.geometry("1200x800")
        self.transient(parent)
        
        self._build_ui()
    
    def _build_ui(self):
        """构建UI"""
        main_frame = ttk.Frame(self)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # 工具栏
        toolbar = ttk.Frame(main_frame)
        toolbar.pack(fill="x", pady=(0, 10))
        
        ttk.Label(toolbar, text=f"共 {len(self.shots)} 个分镜", 
                 font=("Microsoft YaHei", 12, "bold")).pack(side="left", padx=5)
        
        ttk.Button(toolbar, text="💾 导出文本", 
                  command=self._export_shots).pack(side="right", padx=5)
        
        # 内容区
        text_frame = ttk.Frame(main_frame)
        text_frame.pack(fill="both", expand=True)
        
        self.text_widget = tk.Text(text_frame, wrap="word", font=("Consolas", 10))
        scrollbar = ttk.Scrollbar(text_frame, orient="vertical", command=self.text_widget.yview)
        self.text_widget.configure(yscrollcommand=scrollbar.set)
        
        self.text_widget.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # 显示内容
        self._display_shots()
    
    def _display_shots(self):
        """显示分镜"""
        self.text_widget.config(state="normal")
        self.text_widget.delete("1.0", "end")
        
        for idx, shot in enumerate(self.shots, 1):
            self.text_widget.insert("end", "="*80 + "\n")
            self.text_widget.insert("end", f"【镜头 {shot.get('shot_number', idx)}】{shot.get('scene_id', '')} - {shot.get('shot_type', '')}\n")
            self.text_widget.insert("end", "="*80 + "\n\n")
            self.text_widget.insert("end", f"📌 位置: {shot.get('location', '')}\n")
            self.text_widget.insert("end", f"👥 人物: {', '.join(shot.get('characters', []))}\n")
            self.text_widget.insert("end", f"🎨 画面: {shot.get('visual_description', '')}\n")
            self.text_widget.insert("end", f"🎭 动作: {shot.get('action', '')}\n\n")
        
        self.text_widget.config(state="disabled")
    
    def _export_shots(self):
        """导出分镜为文本"""
        file_path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )
        
        if not file_path:
            return
        
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                for idx, shot in enumerate(self.shots, 1):
                    f.write(f"{'='*80}\n")
                    f.write(f"【镜头 {shot.get('shot_number', idx)}】{shot.get('scene_id', '')} - {shot.get('shot_type', '')}\n")
                    f.write(f"{'='*80}\n\n")
                    f.write(f"📌 位置: {shot.get('location', '')}\n")
                    f.write(f"👥 人物: {', '.join(shot.get('characters', []))}\n")
                    f.write(f"🎨 画面: {shot.get('visual_description', '')}\n")
                    f.write(f"🎭 动作: {shot.get('action', '')}\n\n")
            
            messagebox.showinfo("成功", f"已导出到: {file_path}")
        except Exception as e:
            messagebox.showerror("错误", f"导出失败: {e}")


# 向后兼容的Mixin
class ShotViewerMixin:
    """向后兼容的Mixin"""
    def open_shot_viewer(self):
        if not hasattr(self, 'current_shots') or not self.current_shots:
            messagebox.showwarning("提示", "请先生成分镜头")
            return
        
        viewer = ShotViewerDialog(self, self.current_shots)
        viewer.grab_set()

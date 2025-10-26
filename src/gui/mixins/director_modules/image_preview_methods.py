"""
图片预览相关方法
"""

import os
import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk
from pathlib import Path


def add_image_preview_methods(cls):
    """为DirectorMixin添加图片预览方法"""
    
    def _refresh_preview_shot_combo(self):
        """刷新预览页面的分镜下拉框"""
        if not hasattr(self, 'preview_shot_combo'):
            return
        
        options = ["全部分镜"]
        
        if hasattr(self, 'current_shots') and self.current_shots:
            for shot in self.current_shots:
                shot_num = shot.get('shot_number', 0)
                shot_type = shot.get('shot_type', '')
                options.append(f"分镜{shot_num} - {shot_type}")
        
        self.preview_shot_combo['values'] = options
        
        # 保持当前选择或默认选择第一个
        current = self.preview_shot_var.get()
        if current not in options:
            self.preview_shot_var.set("全部分镜")
    
    def _on_preview_shot_selected(self, event=None):
        """当选择分镜时，显示对应的图片"""
        self._refresh_preview_images()
    
    def _refresh_preview_images(self):
        """刷新预览图片"""
        # 清空当前显示
        for widget in self.director_images_scrollable.winfo_children():
            widget.destroy()
        
        if not hasattr(self, 'current_project') or not self.current_project:
            ttk.Label(
                self.director_images_scrollable, 
                text="请先加载项目",
                font=("Microsoft YaHei", 14),
                foreground="gray"
            ).pack(pady=50)
            return
        
        # 获取项目路径
        if hasattr(self.current_project, 'project_dir'):
            project_path = Path(self.current_project.project_dir)
        elif isinstance(self.current_project, dict):
            project_path = Path(self.current_project.get('path', ''))
        else:
            project_path = Path(str(self.current_project))
        
        shots_dir = project_path / "director" / "shots"
        
        if not shots_dir.exists():
            ttk.Label(
                self.director_images_scrollable, 
                text="还没有生成任何图片\n\n请先在【步骤3】中生成分镜图片",
                font=("Microsoft YaHei", 12),
                foreground="gray",
                justify="center"
            ).pack(pady=50)
            return
        
        # 获取所有图片
        all_images = sorted([f for f in os.listdir(shots_dir) if f.endswith(('.png', '.jpg', '.jpeg'))])
        
        if not all_images:
            ttk.Label(
                self.director_images_scrollable, 
                text="目录为空\n\n请先生成分镜图片",
                font=("Microsoft YaHei", 12),
                foreground="gray",
                justify="center"
            ).pack(pady=50)
            return
        
        # 根据选择过滤图片
        selected = self.preview_shot_var.get()
        
        if selected == "全部分镜":
            images_to_show = all_images
            self.preview_info_label.config(text=f"共 {len(images_to_show)} 张图片")
        else:
            # 提取分镜编号
            shot_num = int(selected.split("分镜")[1].split(" ")[0])
            # 过滤该分镜的图片 (格式: shot_001_v1.png)
            images_to_show = [img for img in all_images if img.startswith(f"shot_{shot_num:03d}_")]
            self.preview_info_label.config(text=f"{selected}: {len(images_to_show)} 张图片")
        
        if not images_to_show:
            ttk.Label(
                self.director_images_scrollable, 
                text=f"{selected} 还没有生成图片",
                font=("Microsoft YaHei", 12),
                foreground="gray"
            ).pack(pady=50)
            return
        
        # 显示图片网格
        self._display_images_grid(shots_dir, images_to_show)
    
    def _display_images_grid(self, shots_dir: Path, image_files: list):
        """以网格形式显示图片"""
        col_count = 2  # 每行2张图片
        
        # 存储PhotoImage引用，防止被垃圾回收
        if not hasattr(self, '_preview_image_refs'):
            self._preview_image_refs = []
        self._preview_image_refs.clear()
        
        for idx, img_file in enumerate(image_files):
            row = idx // col_count
            col = idx % col_count
            
            # 图片容器
            img_container = ttk.Frame(self.director_images_scrollable, relief="solid", borderwidth=1)
            img_container.grid(row=row, column=col, padx=10, pady=10, sticky="nsew")
            
            # 文件名标签
            name_label = ttk.Label(
                img_container, 
                text=img_file,
                font=("Consolas", 9),
                foreground="#00aaff"
            )
            name_label.pack(pady=(5, 2))
            
            # 加载并显示图片
            try:
                img_path = shots_dir / img_file
                img = Image.open(img_path)
                
                # 缩放到合适大小
                display_width = 400
                aspect_ratio = img.height / img.width
                display_height = int(display_width * aspect_ratio)
                
                img_resized = img.resize((display_width, display_height), Image.Resampling.LANCZOS)
                photo = ImageTk.PhotoImage(img_resized)
                
                # 图片标签（可点击放大）
                img_label = tk.Label(
                    img_container, 
                    image=photo, 
                    cursor="hand2",
                    bg="#2b2b2b"
                )
                img_label.pack(padx=5, pady=5)
                img_label.bind("<Button-1>", lambda e, path=img_path: self._show_image_fullscreen(path))
                
                # 保存引用
                self._preview_image_refs.append(photo)
                
                # 图片信息
                file_size = os.path.getsize(img_path) / 1024  # KB
                info_text = f"{img.width}×{img.height} | {file_size:.1f} KB"
                info_label = ttk.Label(
                    img_container,
                    text=info_text,
                    font=("Consolas", 8),
                    foreground="gray"
                )
                info_label.pack(pady=(2, 5))
                
                # 删除按钮
                delete_btn = ttk.Button(
                    img_container,
                    text="🗑️ 删除",
                    command=lambda f=img_file: self._delete_preview_image(shots_dir, f),
                    width=12
                )
                delete_btn.pack(pady=(0, 5))
                
            except Exception as e:
                error_label = ttk.Label(
                    img_container,
                    text=f"加载失败\n{str(e)}",
                    foreground="red",
                    justify="center"
                )
                error_label.pack(pady=20)
        
        # 配置网格权重
        for i in range(col_count):
            self.director_images_scrollable.grid_columnconfigure(i, weight=1)
    
    def _show_image_fullscreen(self, image_path: Path):
        """全屏显示图片"""
        dialog = tk.Toplevel(self)
        dialog.title(f"🖼️  {image_path.name}")
        dialog.geometry("1200x900")
        dialog.transient(self)
        dialog.configure(bg="black")
        
        # 加载图片
        img = Image.open(image_path)
        
        # 缩放到窗口大小
        max_width = 1150
        max_height = 850
        
        aspect_ratio = img.width / img.height
        if aspect_ratio > max_width / max_height:
            new_width = max_width
            new_height = int(max_width / aspect_ratio)
        else:
            new_height = max_height
            new_width = int(max_height * aspect_ratio)
        
        img_resized = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
        photo = ImageTk.PhotoImage(img_resized)
        
        # 显示图片
        label = tk.Label(dialog, image=photo, bg="black")
        label.image = photo  # 保持引用
        label.pack(expand=True)
        
        # 关闭按钮
        close_btn = ttk.Button(dialog, text="关闭", command=dialog.destroy)
        close_btn.pack(pady=10)
        
        # ESC键关闭
        dialog.bind("<Escape>", lambda e: dialog.destroy())
    
    def _delete_preview_image(self, shots_dir: Path, img_file: str):
        """删除预览图片"""
        from tkinter import messagebox
        
        if messagebox.askyesno("确认删除", f"确定要删除图片吗？\n\n{img_file}"):
            try:
                img_path = shots_dir / img_file
                os.remove(img_path)
                print(f"[OK] 已删除: {img_file}")
                
                # 刷新显示
                self._refresh_preview_images()
                
                messagebox.showinfo("成功", "图片已删除")
            except Exception as e:
                messagebox.showerror("错误", f"删除失败: {e}")
    
    def _on_preview_mousewheel(self, event):
        """鼠标滚轮滚动"""
        if hasattr(self, 'director_images_canvas'):
            self.director_images_canvas.yview_scroll(int(-1*(event.delta/120)), "units")
    
    # 将方法添加到类
    cls._refresh_preview_shot_combo = _refresh_preview_shot_combo
    cls._on_preview_shot_selected = _on_preview_shot_selected
    cls._refresh_preview_images = _refresh_preview_images
    cls._display_images_grid = _display_images_grid
    cls._show_image_fullscreen = _show_image_fullscreen
    cls._delete_preview_image = _delete_preview_image
    cls._on_preview_mousewheel = _on_preview_mousewheel
    
    return cls


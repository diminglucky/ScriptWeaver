"""
人物照片管理模块
用于浏览、管理和组织人物照片
"""
import tkinter as tk
from tkinter import ttk, messagebox
from PIL import Image, ImageTk
from pathlib import Path
from typing import List, Dict, Optional


class CharacterPhotoGallery(tk.Toplevel):
    """人物照片画廊窗口 - 用于查看和管理所有生成的人物照片"""
    
    def __init__(self, parent, character_name: str, photos_dir: Path, on_photo_select=None):
        super().__init__(parent)
        
        self.character_name = character_name
        self.photos_dir = photos_dir
        self.on_photo_select = on_photo_select
        self.photos: List[Path] = []
        self.photo_widgets: List[tk.Frame] = []
        
        # 窗口设置
        self.title(f"人物照片管理 - {character_name}")
        self.geometry("900x700")
        self.configure(bg="#1e1e1e")
        
        # 创建UI
        self._build_ui()
        
        # 加载照片
        self._load_photos()
        
        # 模态窗口
        self.transient(parent)
        self.grab_set()
    
    def _build_ui(self):
        """构建UI"""
        # 顶部工具栏
        toolbar = tk.Frame(self, bg="#2b2b2b", height=50)
        toolbar.pack(fill="x", padx=0, pady=0)
        toolbar.pack_propagate(False)
        
        # 标题
        title_frame = tk.Frame(toolbar, bg="#2b2b2b")
        title_frame.pack(side="left", padx=20, pady=10)
        
        tk.Label(
            title_frame,
            text=f"👤 {self.character_name}",
            font=("", 14, "bold"),
            bg="#2b2b2b",
            fg="white"
        ).pack(side="left")
        
        tk.Label(
            title_frame,
            text=" 的照片",
            font=("", 12),
            bg="#2b2b2b",
            fg="#888888"
        ).pack(side="left")
        
        # 按钮
        btn_frame = tk.Frame(toolbar, bg="#2b2b2b")
        btn_frame.pack(side="right", padx=20, pady=10)
        
        # 使用更兼容的按钮样式
        refresh_btn = tk.Button(
            btn_frame,
            text="刷新",
            command=self._load_photos,
            width=10,
            height=2,
            font=("Arial", 11, "bold"),
            bg="#4CAF50",
            fg="black",
            relief="raised",
            bd=1,
            cursor="hand2",
            activebackground="#45a049",
            activeforeground="black"
        )
        refresh_btn.pack(side="left", padx=5)
        
        close_btn = tk.Button(
            btn_frame,
            text="关闭",
            command=self.destroy,
            width=10,
            height=2,
            font=("Arial", 11, "bold"),
            bg="#f44336",
            fg="black",
            relief="raised",
            bd=1,
            cursor="hand2",
            activebackground="#d32f2f",
            activeforeground="black"
        )
        close_btn.pack(side="left", padx=5)
        
        # 分隔线
        tk.Frame(self, bg="#444444", height=1).pack(fill="x")
        
        # 滚动区域
        container = tk.Frame(self, bg="#1e1e1e")
        container.pack(fill="both", expand=True, padx=0, pady=0)
        
        # Canvas和滚动条
        v_scroll = ttk.Scrollbar(container, orient="vertical")
        h_scroll = ttk.Scrollbar(container, orient="horizontal")
        
        self.canvas = tk.Canvas(
            container,
            bg="#1e1e1e",
            yscrollcommand=v_scroll.set,
            xscrollcommand=h_scroll.set,
            highlightthickness=0
        )
        
        v_scroll.config(command=self.canvas.yview)
        h_scroll.config(command=self.canvas.xview)
        
        # 布局
        self.canvas.grid(row=0, column=0, sticky="nsew")
        v_scroll.grid(row=0, column=1, sticky="ns")
        h_scroll.grid(row=1, column=0, sticky="ew")
        
        container.grid_rowconfigure(0, weight=1)
        container.grid_columnconfigure(0, weight=1)
        
        # 内容框架
        self.content_frame = tk.Frame(self.canvas, bg="#1e1e1e")
        self.canvas_window = self.canvas.create_window(0, 0, window=self.content_frame, anchor="nw")
        
        # 绑定事件
        self.content_frame.bind("<Configure>", self._on_frame_configure)
        self.canvas.bind("<Configure>", self._on_canvas_configure)
        
        # 绑定鼠标滚轮
        self.canvas.bind("<Enter>", self._bind_mousewheel)
        self.canvas.bind("<Leave>", self._unbind_mousewheel)
    
    def _on_frame_configure(self, event=None):
        """内容框架大小变化"""
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
    
    def _on_canvas_configure(self, event):
        """Canvas大小变化"""
        self.canvas.itemconfig(self.canvas_window, width=event.width)
    
    def _bind_mousewheel(self, event):
        """绑定鼠标滚轮"""
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)
        self.canvas.bind_all("<Button-4>", self._on_mousewheel)
        self.canvas.bind_all("<Button-5>", self._on_mousewheel)
    
    def _unbind_mousewheel(self, event):
        """解绑鼠标滚轮"""
        self.canvas.unbind_all("<MouseWheel>")
        self.canvas.unbind_all("<Button-4>")
        self.canvas.unbind_all("<Button-5>")
    
    def _on_mousewheel(self, event):
        """鼠标滚轮事件"""
        if event.delta:
            self.canvas.yview_scroll(int(-1 * event.delta / 120), "units")
        elif event.num == 4:
            self.canvas.yview_scroll(-1, "units")
        elif event.num == 5:
            self.canvas.yview_scroll(1, "units")
    
    def _load_photos(self):
        """加载人物照片"""
        # 清空现有内容
        for widget in self.content_frame.winfo_children():
            widget.destroy()
        
        self.photos.clear()
        self.photo_widgets.clear()
        
        # 查找照片
        if not self.photos_dir.exists():
            self._show_empty_message()
            return
        
        # 查找该人物的所有照片
        pattern = f"{self.character_name}*.png"
        found_photos = list(self.photos_dir.glob(pattern))
        
        if not found_photos:
            self._show_empty_message()
            return
        
        self.photos = sorted(found_photos, key=lambda p: p.stat().st_mtime, reverse=True)
        
        # 显示照片
        self._display_photos()
    
    def _show_empty_message(self):
        """显示空消息"""
        msg_frame = tk.Frame(self.content_frame, bg="#1e1e1e")
        msg_frame.pack(expand=True, fill="both", padx=50, pady=100)
        
        tk.Label(
            msg_frame,
            text="📷",
            font=("", 48),
            bg="#1e1e1e",
            fg="#444444"
        ).pack()
        
        tk.Label(
            msg_frame,
            text="暂无照片",
            font=("", 14),
            bg="#1e1e1e",
            fg="#666666"
        ).pack(pady=10)
        
        tk.Label(
            msg_frame,
            text=f"还没有为「{self.character_name}」生成照片\n请返回生成照片",
            font=("", 11),
            bg="#1e1e1e",
            fg="#888888",
            justify="center"
        ).pack()
    
    def _display_photos(self):
        """显示照片网格"""
        # 每行3张照片
        columns = 3
        padding = 15
        
        for idx, photo_path in enumerate(self.photos):
            row = idx // columns
            col = idx % columns
            
            photo_frame = self._create_photo_card(photo_path, idx)
            photo_frame.grid(row=row, column=col, padx=padding, pady=padding, sticky="nsew")
            
            self.photo_widgets.append(photo_frame)
        
        # 配置列权重
        for col in range(columns):
            self.content_frame.grid_columnconfigure(col, weight=1)
    
    def _create_photo_card(self, photo_path: Path, index: int) -> tk.Frame:
        """创建照片卡片"""
        card = tk.Frame(self.content_frame, bg="#2b2b2b", relief="flat", borderwidth=0)
        
        # 内容区域
        content = tk.Frame(card, bg="#2b2b2b")
        content.pack(padx=10, pady=10, fill="both", expand=True)
        
        # 加载和调整图片大小
        try:
            img = Image.open(photo_path)
            # 缩略图大小
            thumb_size = (250, 350)
            
            # 使用高质量缩放算法，保持宽高比
            img.thumbnail(thumb_size, Image.Resampling.LANCZOS)
            
            # 如果图片太小，使用高质量放大
            if img.size[0] < thumb_size[0] and img.size[1] < thumb_size[1]:
                # 计算放大比例
                scale_x = thumb_size[0] / img.size[0]
                scale_y = thumb_size[1] / img.size[1]
                scale = min(scale_x, scale_y)
                
                if scale > 1.2:  # 只有在需要显著放大时才放大
                    new_size = (int(img.size[0] * scale), int(img.size[1] * scale))
                    img = img.resize(new_size, Image.Resampling.LANCZOS)
                    # 重新缩放到目标大小
                    img.thumbnail(thumb_size, Image.Resampling.LANCZOS)
            
            photo = ImageTk.PhotoImage(img)
            
            # 图片标签
            img_label = tk.Label(
                content,
                image=photo,
                bg="#2b2b2b",
                cursor="hand2"
            )
            img_label.image = photo  # 保持引用
            img_label.pack(pady=(0, 10))
            
            # 点击查看大图
            img_label.bind("<Button-1>", lambda e, p=photo_path: self._view_full_image(p))
            
        except Exception as e:
            tk.Label(
                content,
                text="加载失败",
                font=("", 10),
                bg="#2b2b2b",
                fg="#ff5555"
            ).pack()
        
        # 信息区域
        info_frame = tk.Frame(content, bg="#2b2b2b")
        info_frame.pack(fill="x")
        
        # 文件名
        filename = photo_path.name
        if len(filename) > 30:
            filename = filename[:27] + "..."
        
        tk.Label(
            info_frame,
            text=filename,
            font=("", 9),
            bg="#2b2b2b",
            fg="#cccccc"
        ).pack(anchor="w", pady=(0, 5))
        
        # 修改时间
        import time
        mtime = photo_path.stat().st_mtime
        time_str = time.strftime("%Y-%m-%d %H:%M", time.localtime(mtime))
        
        tk.Label(
            info_frame,
            text=f"时间: {time_str}",
            font=("", 8),
            bg="#2b2b2b",
            fg="#888888"
        ).pack(anchor="w")
        
        # 按钮区域
        btn_frame = tk.Frame(content, bg="#2b2b2b")
        btn_frame.pack(fill="x", pady=(10, 0))
        
        # 使用按钮
        use_btn = tk.Button(
            btn_frame,
            text="使用",
            command=lambda: self._select_photo(photo_path),
            width=10,
            height=2,
            font=("Arial", 10, "bold"),
            bg="#2196F3",
            fg="black",
            relief="raised",
            bd=1,
            cursor="hand2",
            activebackground="#1976D2",
            activeforeground="black"
        )
        use_btn.pack(side="left", padx=(0, 5))
        
        # 删除按钮
        delete_btn = tk.Button(
            btn_frame,
            text="删除",
            command=lambda: self._delete_photo(photo_path, card),
            width=10,
            height=2,
            font=("Arial", 10, "bold"),
            bg="#f44336",
            fg="black",
            relief="raised",
            bd=1,
            cursor="hand2",
            activebackground="#d32f2f",
            activeforeground="black"
        )
        delete_btn.pack(side="left")
        
        return card
    
    def _view_full_image(self, photo_path: Path):
        """查看完整图片"""
        viewer = ImageViewer(self, photo_path)
    
    def _select_photo(self, photo_path: Path):
        """选择照片"""
        if self.on_photo_select:
            self.on_photo_select(photo_path)
        messagebox.showinfo("成功", f"已选择照片：\n{photo_path.name}")
    
    def _delete_photo(self, photo_path: Path, card_widget):
        """删除照片"""
        result = messagebox.askyesno(
            "确认删除",
            f"确定要删除照片吗？\n\n{photo_path.name}\n\n此操作不可恢复！",
            icon="warning"
        )
        
        if result:
            try:
                photo_path.unlink()
                card_widget.destroy()
                self.photos.remove(photo_path)
                messagebox.showinfo("成功", "照片已删除")
                
                # 如果没有照片了，显示空消息
                if not self.photos:
                    self._load_photos()
                    
            except Exception as e:
                messagebox.showerror("错误", f"删除失败：{str(e)}")


class ImageViewer(tk.Toplevel):
    """图片查看器 - 显示完整大小的图片"""
    
    def __init__(self, parent, image_path: Path):
        super().__init__(parent)
        
        self.image_path = image_path
        
        # 窗口设置
        self.title(f"查看图片 - {image_path.name}")
        self.geometry("1000x800")
        self.configure(bg="#000000")
        
        # 加载和显示图片
        self._display_image()
        
        # 绑定ESC关闭
        self.bind("<Escape>", lambda e: self.destroy())
        
        # 模态窗口
        self.transient(parent)
        self.grab_set()
    
    def _display_image(self):
        """显示图片"""
        try:
            img = Image.open(self.image_path)
            
            # 创建滚动区域
            container = tk.Frame(self, bg="#000000")
            container.pack(fill="both", expand=True)
            
            v_scroll = ttk.Scrollbar(container, orient="vertical")
            h_scroll = ttk.Scrollbar(container, orient="horizontal")
            
            canvas = tk.Canvas(
                container,
                bg="#000000",
                yscrollcommand=v_scroll.set,
                xscrollcommand=h_scroll.set
            )
            
            v_scroll.config(command=canvas.yview)
            h_scroll.config(command=canvas.xview)
            
            canvas.grid(row=0, column=0, sticky="nsew")
            v_scroll.grid(row=0, column=1, sticky="ns")
            h_scroll.grid(row=1, column=0, sticky="ew")
            
            container.grid_rowconfigure(0, weight=1)
            container.grid_columnconfigure(0, weight=1)
            
            # 显示图片
            photo = ImageTk.PhotoImage(img)
            canvas.create_image(0, 0, image=photo, anchor="nw")
            canvas.image = photo  # 保持引用
            
            canvas.config(scrollregion=canvas.bbox("all"))

            # 绑定鼠标滚轮以支持上下/左右滚动（兼容 macOS/Windows/Linux）
            def _on_mousewheel(event):
                # Shift + 滚轮 => 水平滚动
                shift_pressed = bool(event.state & 0x0001)
                if event.delta:
                    delta_units = int(-1 * event.delta / 120) if event.delta else 0
                    if shift_pressed:
                        canvas.xview_scroll(delta_units, "units")
                    else:
                        canvas.yview_scroll(delta_units, "units")
                elif getattr(event, "num", None) in (4, 5):
                    # Linux: Button-4 上滚, Button-5 下滚
                    if shift_pressed:
                        canvas.xview_scroll(-1 if event.num == 4 else 1, "units")
                    else:
                        canvas.yview_scroll(-1 if event.num == 4 else 1, "units")

            canvas.bind("<MouseWheel>", _on_mousewheel)
            canvas.bind("<Button-4>", _on_mousewheel)
            canvas.bind("<Button-5>", _on_mousewheel)
            
            # 底部信息栏
            info_bar = tk.Frame(self, bg="#1e1e1e", height=40)
            info_bar.pack(fill="x", side="bottom")
            info_bar.pack_propagate(False)
            
            info_text = f"📐 {img.width} × {img.height} 像素  |  📄 {self.image_path.name}"
            tk.Label(
                info_bar,
                text=info_text,
                font=("", 10),
                bg="#1e1e1e",
                fg="white"
            ).pack(pady=10)
            
        except Exception as e:
            tk.Label(
                self,
                text=f"❌ 加载图片失败\n\n{str(e)}",
                font=("", 12),
                bg="#000000",
                fg="white"
            ).pack(expand=True)


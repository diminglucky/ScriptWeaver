"""
人物照片画廊组件
用于显示和管理人物的多张照片（不同角度、表情等）
"""

import tkinter as tk
from tkinter import ttk, messagebox
from pathlib import Path
from PIL import Image, ImageTk
from typing import Callable, Optional


class CharacterPhotoGallery(tk.Toplevel):
    """人物照片画廊弹窗"""
    
    def __init__(
        self,
        parent: tk.Tk,
        character_name: str,
        photos_dir: Path,
        on_photo_select: Optional[Callable[[Path], None]] = None
    ):
        super().__init__(parent)
        
        self.character_name = character_name
        self.photos_dir = Path(photos_dir)
        self.on_photo_select = on_photo_select
        self.photos: list[Path] = []
        self.photo_images: list[ImageTk.PhotoImage] = []  # 保持引用防止GC
        
        # 窗口配置
        self.title(f"📷 {character_name} - 照片画廊")
        self.geometry("800x600")
        self.configure(bg="#2b2b2b")
        
        # 使窗口模态
        self.transient(parent)
        self.grab_set()
        
        self._load_photos()
        self._build_ui()
        
        # 居中显示
        self.update_idletasks()
        x = (self.winfo_screenwidth() - self.winfo_width()) // 2
        y = (self.winfo_screenheight() - self.winfo_height()) // 2
        self.geometry(f"+{x}+{y}")
    
    def _load_photos(self) -> None:
        """加载人物的所有照片"""
        if not self.photos_dir.exists():
            return
        
        # 查找该人物的所有照片（支持多种格式）
        patterns = [
            f"{self.character_name}*.png",
            f"{self.character_name}*.jpg",
            f"{self.character_name}*.jpeg",
        ]
        
        for pattern in patterns:
            self.photos.extend(self.photos_dir.glob(pattern))
        
        # 去重并排序
        self.photos = sorted(set(self.photos))
        print(f"📷 找到 {len(self.photos)} 张照片")
    
    def _build_ui(self) -> None:
        """构建界面"""
        # 标题
        title_frame = tk.Frame(self, bg="#2b2b2b")
        title_frame.pack(fill="x", padx=20, pady=10)
        
        title_label = tk.Label(
            title_frame,
            text=f"👤 {self.character_name} 的照片集",
            font=("微软雅黑", 16, "bold"),
            bg="#2b2b2b",
            fg="white"
        )
        title_label.pack(side="left")
        
        count_label = tk.Label(
            title_frame,
            text=f"共 {len(self.photos)} 张",
            font=("微软雅黑", 12),
            bg="#2b2b2b",
            fg="#888888"
        )
        count_label.pack(side="right")
        
        # 照片网格容器
        canvas_frame = tk.Frame(self, bg="#2b2b2b")
        canvas_frame.pack(fill="both", expand=True, padx=20, pady=10)
        
        # 创建带滚动条的画布
        canvas = tk.Canvas(canvas_frame, bg="#2b2b2b", highlightthickness=0)
        scrollbar = ttk.Scrollbar(canvas_frame, orient="vertical", command=canvas.yview)
        
        self.photos_frame = tk.Frame(canvas, bg="#2b2b2b")
        
        canvas.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)
        
        canvas.create_window((0, 0), window=self.photos_frame, anchor="nw")
        
        # 添加照片缩略图
        if self.photos:
            self._add_photo_thumbnails()
        else:
            no_photo_label = tk.Label(
                self.photos_frame,
                text="📭 暂无照片\n请先在人物描述页面生成照片",
                font=("微软雅黑", 14),
                bg="#2b2b2b",
                fg="#888888"
            )
            no_photo_label.pack(pady=100)
        
        # 更新滚动区域
        self.photos_frame.update_idletasks()
        canvas.configure(scrollregion=canvas.bbox("all"))
        
        # 底部按钮
        btn_frame = tk.Frame(self, bg="#2b2b2b")
        btn_frame.pack(fill="x", padx=20, pady=10)
        
        close_btn = ttk.Button(btn_frame, text="关闭", command=self.destroy)
        close_btn.pack(side="right")
    
    def _add_photo_thumbnails(self) -> None:
        """添加照片缩略图"""
        THUMB_SIZE = 150
        COLUMNS = 4
        
        for i, photo_path in enumerate(self.photos):
            row = i // COLUMNS
            col = i % COLUMNS
            
            try:
                # 加载并缩放图片
                img = Image.open(photo_path)
                img.thumbnail((THUMB_SIZE, THUMB_SIZE), Image.Resampling.LANCZOS)
                photo_img = ImageTk.PhotoImage(img)
                self.photo_images.append(photo_img)  # 保持引用
                
                # 创建照片卡片
                card = tk.Frame(self.photos_frame, bg="#3a3a3a", padx=5, pady=5)
                card.grid(row=row*2, column=col, padx=10, pady=10, sticky="n")
                
                # 照片标签
                label = tk.Label(card, image=photo_img, bg="#3a3a3a", cursor="hand2")
                label.pack()
                
                # 文件名标签
                name = photo_path.stem.replace(self.character_name, "").strip("_") or "默认"
                name_label = tk.Label(
                    card,
                    text=name[:15],
                    font=("微软雅黑", 9),
                    bg="#3a3a3a",
                    fg="#cccccc"
                )
                name_label.pack()
                
                # 点击事件
                def on_click(path=photo_path):
                    if self.on_photo_select:
                        self.on_photo_select(path)
                    self._show_full_photo(path)
                
                label.bind("<Button-1>", lambda e, p=photo_path: on_click(p))
                
            except Exception as e:
                print(f"加载照片失败 {photo_path}: {e}")
    
    def _show_full_photo(self, photo_path: Path) -> None:
        """显示完整照片"""
        try:
            # 创建新窗口显示大图
            preview = tk.Toplevel(self)
            preview.title(f"📷 {photo_path.name}")
            preview.configure(bg="#1a1a1a")
            
            # 加载图片
            img = Image.open(photo_path)
            
            # 限制最大尺寸
            max_size = 800
            if img.width > max_size or img.height > max_size:
                img.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
            
            photo_img = ImageTk.PhotoImage(img)
            
            label = tk.Label(preview, image=photo_img, bg="#1a1a1a")
            label.image = photo_img  # 保持引用
            label.pack(padx=20, pady=20)
            
            # 点击关闭
            label.bind("<Button-1>", lambda e: preview.destroy())
            
            # 居中
            preview.update_idletasks()
            x = (preview.winfo_screenwidth() - preview.winfo_width()) // 2
            y = (preview.winfo_screenheight() - preview.winfo_height()) // 2
            preview.geometry(f"+{x}+{y}")
            
        except Exception as e:
            messagebox.showerror("错误", f"无法显示照片：{e}")

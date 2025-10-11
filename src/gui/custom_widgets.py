"""
自定义UI组件
"""

import tkinter as tk
from tkinter import ttk
from typing import Optional, Callable


class ModernButton(tk.Canvas):
    """现代化按钮组件"""
    
    def __init__(self, parent, text="", command=None, variant="primary", icon="", width=120, height=36, **kwargs):
        super().__init__(parent, highlightthickness=0, **kwargs)
        
        self.text = text
        self.command = command
        self.variant = variant
        self.icon = icon
        self.width = width
        self.height = height
        
        # 颜色配置
        self.colors = {
            "primary": {
                "bg": "#1e88e5",
                "hover": "#1976d2",
                "active": "#1565c0",
                "text": "#ffffff"
            },
            "success": {
                "bg": "#43a047",
                "hover": "#388e3c",
                "active": "#2e7d32",
                "text": "#ffffff"
            },
            "danger": {
                "bg": "#e53935",
                "hover": "#d32f2f",
                "active": "#c62828",
                "text": "#ffffff"
            },
            "warning": {
                "bg": "#fb8c00",
                "hover": "#f57c00",
                "active": "#ef6c00",
                "text": "#ffffff"
            },
            "secondary": {
                "bg": "#424242",
                "hover": "#616161",
                "active": "#757575",
                "text": "#ffffff"
            },
            "ghost": {
                "bg": "transparent",
                "hover": "#424242",
                "active": "#616161",
                "text": "#b3b3b3"
            }
        }
        
        self.current_color = self.colors[variant]["bg"]
        self.configure(width=width, height=height, bg=parent["bg"])
        
        self._create_button()
        self._bind_events()
    
    def _create_button(self):
        """创建按钮"""
        # 绘制圆角矩形
        self.rect = self.create_rectangle(
            2, 2, self.width-2, self.height-2,
            fill=self.current_color,
            outline="",
            width=0
        )
        
        # 添加文本
        text_content = f"{self.icon}  {self.text}" if self.icon else self.text
        self.text_id = self.create_text(
            self.width/2, self.height/2,
            text=text_content,
            fill=self.colors[self.variant]["text"],
            font=("SF Pro Display", 11)
        )
    
    def _bind_events(self):
        """绑定事件"""
        self.bind("<Enter>", self._on_hover)
        self.bind("<Leave>", self._on_leave)
        self.bind("<Button-1>", self._on_click)
        self.bind("<ButtonRelease-1>", self._on_release)
    
    def _on_hover(self, event):
        """鼠标悬停"""
        self.itemconfig(self.rect, fill=self.colors[self.variant]["hover"])
        self.configure(cursor="hand2")
    
    def _on_leave(self, event):
        """鼠标离开"""
        self.itemconfig(self.rect, fill=self.colors[self.variant]["bg"])
    
    def _on_click(self, event):
        """点击"""
        self.itemconfig(self.rect, fill=self.colors[self.variant]["active"])
        if self.command:
            self.command()
    
    def _on_release(self, event):
        """释放"""
        self.itemconfig(self.rect, fill=self.colors[self.variant]["hover"])


class ModernEntry(tk.Frame):
    """现代化输入框"""
    
    def __init__(self, parent, placeholder="", show="", **kwargs):
        super().__init__(parent, bg="#2a2a2a", highlightbackground="#424242", highlightthickness=1)
        
        self.placeholder = placeholder
        self.show = show
        
        # 创建输入框
        self.entry = tk.Entry(
            self,
            bg="#2a2a2a",
            fg="#ffffff",
            insertbackground="#ffffff",
            relief="flat",
            bd=0,
            font=("SF Pro Display", 11),
            show=show
        )
        self.entry.pack(padx=8, pady=8, fill="both", expand=True)
        
        # 占位符处理
        if placeholder and not show:
            self._add_placeholder()
        
        # 绑定焦点事件
        self.entry.bind("<FocusIn>", self._on_focus_in)
        self.entry.bind("<FocusOut>", self._on_focus_out)
    
    def _add_placeholder(self):
        """添加占位符"""
        self.entry.insert(0, self.placeholder)
        self.entry.config(fg="#666666")
    
    def _on_focus_in(self, event):
        """获得焦点"""
        self.configure(highlightbackground="#1e88e5")
        if self.entry.get() == self.placeholder and not self.show:
            self.entry.delete(0, "end")
            self.entry.config(fg="#ffffff")
    
    def _on_focus_out(self, event):
        """失去焦点"""
        self.configure(highlightbackground="#424242")
        if not self.entry.get() and not self.show:
            self._add_placeholder()
    
    def get(self):
        """获取值"""
        value = self.entry.get()
        if value == self.placeholder and not self.show:
            return ""
        return value
    
    def set(self, value):
        """设置值"""
        self.entry.delete(0, "end")
        self.entry.insert(0, value)
        if value:
            self.entry.config(fg="#ffffff")


class ModernText(tk.Frame):
    """现代化文本框"""
    
    def __init__(self, parent, placeholder="", **kwargs):
        super().__init__(parent, bg="#2a2a2a", highlightbackground="#424242", highlightthickness=1)
        
        self.placeholder = placeholder
        
        # 创建滚动条
        scrollbar = tk.Scrollbar(self, bg="#1a1a1a", troughcolor="#2a2a2a", width=10)
        scrollbar.pack(side="right", fill="y")
        
        # 创建文本框
        self.text = tk.Text(
            self,
            bg="#2a2a2a",
            fg="#ffffff",
            insertbackground="#ffffff",
            selectbackground="#1e88e5",
            selectforeground="#ffffff",
            relief="flat",
            bd=0,
            font=("SF Pro Display", 11),
            wrap="word",
            yscrollcommand=scrollbar.set,
            **kwargs
        )
        self.text.pack(padx=8, pady=8, fill="both", expand=True)
        scrollbar.config(command=self.text.yview)
        
        # 占位符处理
        if placeholder:
            self._add_placeholder()
        
        # 绑定事件
        self.text.bind("<FocusIn>", self._on_focus_in)
        self.text.bind("<FocusOut>", self._on_focus_out)
    
    def _add_placeholder(self):
        """添加占位符"""
        self.text.insert("1.0", self.placeholder)
        self.text.config(fg="#666666")
    
    def _on_focus_in(self, event):
        """获得焦点"""
        self.configure(highlightbackground="#1e88e5")
        if self.text.get("1.0", "end-1c") == self.placeholder:
            self.text.delete("1.0", "end")
            self.text.config(fg="#ffffff")
    
    def _on_focus_out(self, event):
        """失去焦点"""
        self.configure(highlightbackground="#424242")
        if not self.text.get("1.0", "end-1c").strip():
            self._add_placeholder()
    
    def get(self, *args):
        """获取内容"""
        content = self.text.get(*args) if args else self.text.get("1.0", "end-1c")
        if content == self.placeholder:
            return ""
        return content
    
    def insert(self, *args):
        """插入内容"""
        if self.text.get("1.0", "end-1c") == self.placeholder:
            self.text.delete("1.0", "end")
            self.text.config(fg="#ffffff")
        self.text.insert(*args)
    
    def delete(self, *args):
        """删除内容"""
        self.text.delete(*args)


class ModernLabel(tk.Label):
    """现代化标签"""
    
    def __init__(self, parent, text="", variant="normal", **kwargs):
        
        # 样式配置
        styles = {
            "normal": {
                "font": ("SF Pro Display", 11),
                "fg": "#ffffff",
                "bg": "#1a1a1a"
            },
            "secondary": {
                "font": ("SF Pro Display", 10),
                "fg": "#b3b3b3",
                "bg": "#1a1a1a"
            },
            "title": {
                "font": ("SF Pro Display", 16, "bold"),
                "fg": "#ffffff",
                "bg": "#1a1a1a"
            },
            "heading": {
                "font": ("SF Pro Display", 14, "bold"),
                "fg": "#ffffff",
                "bg": "#1a1a1a"
            },
            "caption": {
                "font": ("SF Pro Display", 9),
                "fg": "#666666",
                "bg": "#1a1a1a"
            }
        }
        
        style = styles.get(variant, styles["normal"])
        
        super().__init__(
            parent,
            text=text,
            font=style["font"],
            fg=style["fg"],
            bg=kwargs.get("bg", style["bg"]),
            **{k: v for k, v in kwargs.items() if k != "bg"}
        )


class ModernCard(tk.Frame):
    """现代化卡片容器"""
    
    def __init__(self, parent, title="", **kwargs):
        super().__init__(
            parent,
            bg="#242424",
            highlightbackground="#3a3a3a",
            highlightthickness=1,
            **kwargs
        )
        
        if title:
            # 标题栏
            title_frame = tk.Frame(self, bg="#2a2a2a", height=40)
            title_frame.pack(fill="x", side="top")
            title_frame.pack_propagate(False)
            
            title_label = ModernLabel(
                title_frame,
                text=title,
                variant="heading",
                bg="#2a2a2a"
            )
            title_label.pack(side="left", padx=15, pady=10)
            
            # 分隔线
            separator = tk.Frame(self, bg="#3a3a3a", height=1)
            separator.pack(fill="x")
        
        # 内容区域
        self.content = tk.Frame(self, bg="#242424")
        self.content.pack(fill="both", expand=True, padx=15, pady=15)


class ModernNotebook(ttk.Notebook):
    """现代化选项卡"""
    
    def __init__(self, parent, **kwargs):
        # 配置样式
        style = ttk.Style()
        style.theme_use('clam')
        
        # 自定义选项卡样式
        style.configure(
            "Modern.TNotebook",
            background="#1a1a1a",
            borderwidth=0,
            relief="flat",
            tabmargins=[0, 0, 0, 0]
        )
        
        style.configure(
            "Modern.TNotebook.Tab",
            background="#242424",
            foreground="#b3b3b3",
            padding=[20, 10],
            borderwidth=0,
            focuscolor="none"
        )
        
        style.map(
            "Modern.TNotebook.Tab",
            background=[
                ("selected", "#1e88e5"),
                ("active", "#2a2a2a")
            ],
            foreground=[
                ("selected", "#ffffff"),
                ("active", "#ffffff")
            ]
        )
        
        super().__init__(parent, style="Modern.TNotebook", **kwargs)


class ModernProgressBar(tk.Canvas):
    """现代化进度条"""
    
    def __init__(self, parent, width=300, height=4, **kwargs):
        super().__init__(
            parent,
            width=width,
            height=height,
            bg="#1a1a1a",
            highlightthickness=0,
            **kwargs
        )
        
        self.width = width
        self.height = height
        
        # 背景
        self.create_rectangle(0, 0, width, height, fill="#2a2a2a", outline="")
        
        # 进度条
        self.progress_bar = self.create_rectangle(0, 0, 0, height, fill="#1e88e5", outline="")
        
        self.set_progress(0)
    
    def set_progress(self, value):
        """设置进度（0-100）"""
        value = max(0, min(100, value))
        progress_width = (value / 100) * self.width
        self.coords(self.progress_bar, 0, 0, progress_width, self.height)


class ModernScrollbar(tk.Scrollbar):
    """现代化滚动条"""
    
    def __init__(self, parent, **kwargs):
        super().__init__(
            parent,
            bg="#2a2a2a",
            troughcolor="#1a1a1a",
            activebackground="#1e88e5",
            width=10,
            relief="flat",
            bd=0,
            **kwargs
        )

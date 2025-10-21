"""
自定义组件库 - 精致美学设计
提供现代化、美观的自定义组件
"""

import tkinter as tk
from tkinter import ttk
from .theme import Theme, Styles


class ModernButton(tk.Button):
    """现代化按钮 - 支持多种样式"""
    
    def __init__(self, parent, variant="primary", **kwargs):
        # 获取样式
        style = Styles.get_button_style(variant)
        
        # 合并kwargs和style，kwargs优先
        config = {**style, **kwargs}
        
        super().__init__(parent, **config)
        
        # 添加悬停效果
        self.default_bg = config.get('bg', Theme.PRIMARY)
        self.hover_bg = config.get('activebackground', Theme.PRIMARY_LIGHT)
        
        self.bind('<Enter>', self._on_enter)
        self.bind('<Leave>', self._on_leave)
    
    def _on_enter(self, event):
        """鼠标进入时"""
        self.config(bg=self.hover_bg)
    
    def _on_leave(self, event):
        """鼠标离开时"""
        self.config(bg=self.default_bg)


class ModernCard(tk.Frame):
    """现代化卡片容器 - 带边框和圆角视觉效果"""
    
    def __init__(self, parent, variant="card", padding=16, **kwargs):
        style = Styles.get_frame_style(variant)
        config = {**style, **kwargs}
        
        super().__init__(parent, **config)
        
        # 内部容器，提供padding
        self.inner_frame = tk.Frame(self, bg=config.get('bg', Theme.SURFACE))
        self.inner_frame.pack(fill="both", expand=True, padx=padding, pady=padding)
    
    def add_widget(self, widget_class, **kwargs):
        """在卡片内添加组件"""
        return widget_class(self.inner_frame, **kwargs)


class ModernEntry(tk.Entry):
    """现代化输入框 - 精致设计"""
    
    def __init__(self, parent, placeholder="", **kwargs):
        style = Styles.get_entry_style()
        config = {**style, **kwargs}
        
        super().__init__(parent, **config)
        
        self.placeholder = placeholder
        self.placeholder_active = False
        
        # 如果有占位符，显示它
        if placeholder:
            self._show_placeholder()
            self.bind('<FocusIn>', self._on_focus_in)
            self.bind('<FocusOut>', self._on_focus_out)
    
    def _show_placeholder(self):
        """显示占位符"""
        if not self.get():
            self.insert(0, self.placeholder)
            self.config(fg=Theme.TEXT_HINT)
            self.placeholder_active = True
    
    def _hide_placeholder(self):
        """隐藏占位符"""
        if self.placeholder_active:
            self.delete(0, tk.END)
            self.config(fg=Theme.TEXT_PRIMARY)
            self.placeholder_active = False
    
    def _on_focus_in(self, event):
        """获得焦点时"""
        self._hide_placeholder()
        self.config(highlightbackground=Theme.BORDER_FOCUS)
    
    def _on_focus_out(self, event):
        """失去焦点时"""
        if not self.get():
            self._show_placeholder()
        self.config(highlightbackground=Theme.BORDER)
    
    def get_value(self):
        """获取真实值（排除占位符）"""
        if self.placeholder_active:
            return ""
        return self.get()


class ModernText(tk.Text):
    """现代化文本框 - 精致设计"""
    
    def __init__(self, parent, placeholder="", **kwargs):
        style = Styles.get_text_style()
        config = {**style, **kwargs}
        
        super().__init__(parent, **config)
        
        self.placeholder = placeholder
        self.placeholder_active = False
        
        # 如果有占位符，显示它
        if placeholder:
            self._show_placeholder()
            self.bind('<FocusIn>', self._on_focus_in)
            self.bind('<FocusOut>', self._on_focus_out)
    
    def _show_placeholder(self):
        """显示占位符"""
        if not self.get("1.0", "end-1c"):
            self.insert("1.0", self.placeholder)
            self.tag_add("placeholder", "1.0", "end")
            self.tag_config("placeholder", foreground=Theme.TEXT_HINT)
            self.placeholder_active = True
    
    def _hide_placeholder(self):
        """隐藏占位符"""
        if self.placeholder_active:
            self.delete("1.0", tk.END)
            self.placeholder_active = False
    
    def _on_focus_in(self, event):
        """获得焦点时"""
        self._hide_placeholder()
        self.config(highlightbackground=Theme.BORDER_FOCUS)
    
    def _on_focus_out(self, event):
        """失去焦点时"""
        if not self.get("1.0", "end-1c").strip():
            self._show_placeholder()
        self.config(highlightbackground=Theme.BORDER)
    
    def get_value(self):
        """获取真实值（排除占位符）"""
        if self.placeholder_active:
            return ""
        return self.get("1.0", "end-1c")


class ModernLabel(tk.Label):
    """现代化标签 - 精致设计"""
    
    def __init__(self, parent, variant="normal", **kwargs):
        style = Styles.get_label_style(variant)
        config = {**style, **kwargs}
        
        super().__init__(parent, **config)


class StatusIndicator(tk.Canvas):
    """状态指示器 - 发光效果"""
    
    def __init__(self, parent, size=10, **kwargs):
        super().__init__(
            parent,
            width=size,
            height=size,
            bg=kwargs.get('bg', Theme.BG_PRIMARY),
            highlightthickness=0
        )
        
        self.size = size
        self._status = "ready"
        
        # 绘制初始状态
        self._draw_status()
    
    def set_status(self, status):
        """
        设置状态
        status: 'ready', 'working', 'success', 'error', 'warning'
        """
        self._status = status
        self._draw_status()
    
    def _draw_status(self):
        """根据状态绘制指示器"""
        self.delete("all")
        
        colors = {
            "ready": (Theme.INFO, Theme.INFO_LIGHT),
            "working": (Theme.PRIMARY, Theme.PRIMARY_LIGHT),
            "success": (Theme.SUCCESS, Theme.SUCCESS_LIGHT),
            "error": (Theme.ERROR, Theme.ERROR_LIGHT),
            "warning": (Theme.WARNING, Theme.WARNING_LIGHT)
        }
        
        fill, outline = colors.get(self._status, colors["ready"])
        
        # 绘制外圈发光
        self.create_oval(
            0, 0, self.size, self.size,
            fill=fill,
            outline=outline,
            width=2
        )


class ModernProgressBar(tk.Canvas):
    """现代化进度条 - 渐变效果"""
    
    def __init__(self, parent, width=200, height=6, **kwargs):
        super().__init__(
            parent,
            width=width,
            height=height,
            bg=Theme.BG_TERTIARY,
            highlightthickness=0,
            **kwargs
        )
        
        self.width = width
        self.height = height
        self.progress = 0
        
        # 背景
        self.create_rectangle(
            0, 0, width, height,
            fill=Theme.BG_TERTIARY,
            outline=""
        )
        
        # 进度条
        self.progress_bar = self.create_rectangle(
            0, 0, 0, height,
            fill=Theme.PRIMARY,
            outline=""
        )
    
    def set_progress(self, value):
        """设置进度 (0-100)"""
        self.progress = max(0, min(100, value))
        new_width = (self.width * self.progress) / 100
        
        # 更新进度条
        self.coords(self.progress_bar, 0, 0, new_width, self.height)
        
        # 根据进度改变颜色
        if self.progress < 30:
            color = Theme.ERROR
        elif self.progress < 70:
            color = Theme.WARNING
        else:
            color = Theme.SUCCESS
        
        self.itemconfig(self.progress_bar, fill=color)


class ModernSwitch(tk.Canvas):
    """现代化开关 - iOS风格"""
    
    def __init__(self, parent, width=50, height=26, command=None, **kwargs):
        super().__init__(
            parent,
            width=width,
            height=height,
            bg=kwargs.get('bg', Theme.BG_CARD),
            highlightthickness=0,
            cursor="hand2"
        )
        
        self.width = width
        self.height = height
        self.command = command
        self.is_on = False
        
        # 绘制开关
        self._draw()
        
        # 绑定点击事件
        self.bind('<Button-1>', self._toggle)
    
    def _draw(self):
        """绘制开关"""
        self.delete("all")
        
        # 背景轨道
        bg_color = Theme.PRIMARY if self.is_on else Theme.BG_TERTIARY
        self.create_oval(
            0, 0, self.height, self.height,
            fill=bg_color,
            outline=""
        )
        self.create_oval(
            self.width - self.height, 0,
            self.width, self.height,
            fill=bg_color,
            outline=""
        )
        self.create_rectangle(
            self.height / 2, 0,
            self.width - self.height / 2, self.height,
            fill=bg_color,
            outline=""
        )
        
        # 滑块
        slider_x = self.width - self.height + 2 if self.is_on else 2
        self.create_oval(
            slider_x, 2,
            slider_x + self.height - 4, self.height - 2,
            fill="#FFFFFF",
            outline=""
        )
    
    def _toggle(self, event=None):
        """切换状态"""
        self.is_on = not self.is_on
        self._draw()
        
        if self.command:
            self.command(self.is_on)
    
    def get(self):
        """获取状态"""
        return self.is_on
    
    def set(self, value):
        """设置状态"""
        self.is_on = bool(value)
        self._draw()


class ModernTooltip:
    """现代化提示框"""
    
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tooltip_window = None
        
        widget.bind('<Enter>', self._show)
        widget.bind('<Leave>', self._hide)
    
    def _show(self, event=None):
        """显示提示框"""
        if self.tooltip_window:
            return
        
        x = self.widget.winfo_rootx() + self.widget.winfo_width() // 2
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 5
        
        self.tooltip_window = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")
        
        # 提示框样式
        frame = tk.Frame(
            tw,
            bg=Theme.SURFACE_ELEVATED,
            highlightthickness=1,
            highlightbackground=Theme.BORDER_ACCENT
        )
        frame.pack()
        
        label = tk.Label(
            frame,
            text=self.text,
            bg=Theme.SURFACE_ELEVATED,
            fg=Theme.TEXT_PRIMARY,
            font=(Theme.FONT_FAMILY, Theme.FONT_SIZE_SMALL),
            padx=12,
            pady=6
        )
        label.pack()
    
    def _hide(self, event=None):
        """隐藏提示框"""
        if self.tooltip_window:
            self.tooltip_window.destroy()
            self.tooltip_window = None

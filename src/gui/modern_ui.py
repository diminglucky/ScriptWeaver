"""
现代化UI主窗口 - 采用主流设计语言
"""

import tkinter as tk
from tkinter import ttk
import os
from pathlib import Path
from datetime import datetime

from .theme import Theme, Styles, Icons
from .custom_widgets import ModernButton, ModernCard, ModernEntry, StatusIndicator
from .mixins.story_modules import StoryMixin
from .mixins.image_modules import ImageMixin
from .mixins.project_mixin import ProjectMixin
from .mixins.config_modules import ConfigMixin
from .mixins.kb_mixin import KbMixin
from .mixins.ui_mixin import UiMixin


class ModernUI(tk.Tk, ProjectMixin, StoryMixin, ImageMixin, KbMixin, ConfigMixin, UiMixin):
    """现代化UI应用 - 主流设计风格"""
    
    def __init__(self):
        super().__init__()
        
        # 窗口配置
        self.title("AI Story Creator - 智能故事创作平台")
        self.geometry("1440x900")
        self.minsize(1280, 720)
        
        # 设置窗口背景色
        self.configure(bg=Theme.BG_SECONDARY)
        
        # 加载环境变量
        from dotenv import load_dotenv
        load_dotenv()
        
        # 初始化所有必需的变量
        self._init_variables()
        
        # 应用现代化样式
        self._setup_modern_styles()
        
        # 创建主布局
        self._create_layout()
        
        # 构建UI
        self._build_modern_ui()
        
        # 启动后自动加载配置
        self.after(100, self._auto_load_api_config)
    
    def _init_variables(self):
        """初始化所有必需的变量"""
        # 路径配置
        self.data_dir = tk.StringVar(value=str(Path("data/raw").resolve()))
        self.index_dir = tk.StringVar(value=str(Path("index").resolve()))
        
        # API配置
        self.api_key = tk.StringVar(value=os.getenv("DEEPSEEK_API_KEY", ""))
        self.base_url = tk.StringVar(value=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1"))
        self.model = tk.StringVar(value=os.getenv("DEEPSEEK_MODEL", "deepseek-chat"))
        
        # 生成参数
        self.top_k = tk.IntVar(value=6)
        self.temperature = tk.DoubleVar(value=0.7)
        self.category = tk.StringVar(value="职场")
        self.style = tk.StringVar(value="情感起伏/反转/细节描写/有画面感/口语化")
        self.target_chars = tk.IntVar(value=1800)
        self.model_only = tk.BooleanVar(value=True)
        
        # 故事内容
        self.current_outline: str | None = None
        
        # 项目管理
        from src.project_manager import ProjectManager
        self.project_manager = ProjectManager()
        self.current_project = None
        
        # 章节管理
        self.parsed_sections: list[dict] = []
        self.generated_content: str = ""
    
    def _setup_modern_styles(self):
        """设置现代化ttk组件样式"""
        self.ttk_style = ttk.Style()
        self.ttk_style.theme_use('clam')
        
        # 配置Notebook - 现代化标签页
        self.ttk_style.configure(
            "Modern.TNotebook",
            background=Theme.BG_PRIMARY,
            borderwidth=0,
            relief="flat",
            tabmargins=[0, 0, 0, 0]
        )
        self.ttk_style.configure(
            "Modern.TNotebook.Tab",
            background=Theme.BG_PRIMARY,
            foreground=Theme.TEXT_SECONDARY,
            padding=[24, 12],
            borderwidth=0,
            focuscolor="none",
            font=(Theme.FONT_FAMILY, 12, "normal")
        )
        self.ttk_style.map(
            "Modern.TNotebook.Tab",
            background=[
                ("selected", Theme.BG_PRIMARY),
                ("active", Theme.BG_SECONDARY),
                ("!active", Theme.BG_PRIMARY)
            ],
            foreground=[
                ("selected", Theme.TEXT_PRIMARY),
                ("active", Theme.TEXT_PRIMARY),
                ("!active", Theme.TEXT_SECONDARY)
            ]
        )
        
        # 配置Frame
        self.ttk_style.configure(
            "Modern.TFrame",
            background=Theme.BG_PRIMARY,
            borderwidth=0
        )
        
        # 配置LabelFrame - 现代卡片
        self.ttk_style.configure(
            "Card.TLabelframe",
            background=Theme.SURFACE,
            foreground=Theme.TEXT_PRIMARY,
            borderwidth=0,
            relief="flat"
        )
        self.ttk_style.configure(
            "Card.TLabelframe.Label",
            background=Theme.SURFACE,
            foreground=Theme.TEXT_PRIMARY,
            font=(Theme.FONT_FAMILY, Theme.FONT_SIZE_MEDIUM, "normal")
        )
        
        # 配置Button - 现代按钮
        self.ttk_style.configure(
            "Primary.TButton",
            background=Theme.PRIMARY,
            foreground=Theme.TEXT_ON_PRIMARY,
            borderwidth=0,
            relief="flat",
            padding=[20, 10],
            font=(Theme.FONT_FAMILY, 12, "normal")
        )
        self.ttk_style.map(
            "Primary.TButton",
            background=[
                ("active", Theme.PRIMARY_DARK),
                ("pressed", Theme.PRIMARY_DARK),
                ("disabled", Theme.BG_TERTIARY)
            ],
            foreground=[
                ("active", Theme.TEXT_ON_PRIMARY),
                ("disabled", Theme.TEXT_DISABLED)
            ]
        )
        
        # 配置Entry
        self.ttk_style.configure(
            "Modern.TEntry",
            fieldbackground=Theme.SURFACE,
            foreground=Theme.TEXT_PRIMARY,
            borderwidth=1,
            bordercolor=Theme.BORDER,
            insertcolor=Theme.PRIMARY
        )
        self.ttk_style.map(
            "Modern.TEntry",
            fieldbackground=[("focus", Theme.SURFACE)],
            bordercolor=[("focus", Theme.BORDER_FOCUS)]
        )
        
        # 配置Combobox
        self.ttk_style.configure(
            "Modern.TCombobox",
            fieldbackground=Theme.SURFACE,
            background=Theme.SURFACE,
            foreground=Theme.TEXT_PRIMARY,
            borderwidth=1,
            bordercolor=Theme.BORDER,
            arrowcolor=Theme.TEXT_SECONDARY
        )
        self.ttk_style.map(
            "Modern.TCombobox",
            fieldbackground=[("focus", Theme.SURFACE)],
            bordercolor=[("focus", Theme.BORDER_FOCUS)]
        )
    
    def _create_layout(self):
        """创建主布局结构"""
        # 主容器
        self.main_container = tk.Frame(self, bg=Theme.BG_SECONDARY)
        self.main_container.pack(fill="both", expand=True)
        
        # 左侧边栏
        self._create_sidebar()
        
        # 右侧内容区
        self._create_content_area()
    
    def _create_sidebar(self):
        """创建左侧边栏 - 导航"""
        self.sidebar = tk.Frame(self.main_container, bg=Theme.BG_PRIMARY, width=240)
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)
        
        # Logo区域
        logo_frame = tk.Frame(self.sidebar, bg=Theme.BG_PRIMARY, height=80)
        logo_frame.pack(fill="x")
        logo_frame.pack_propagate(False)
        
        # Logo内容
        logo_inner = tk.Frame(logo_frame, bg=Theme.BG_PRIMARY)
        logo_inner.place(relx=0.5, rely=0.5, anchor="center")
        
        # 图标
        icon_label = tk.Label(
            logo_inner,
            text="✨",
            font=(Theme.FONT_FAMILY, 24),
            bg=Theme.BG_PRIMARY,
            fg=Theme.PRIMARY
        )
        icon_label.pack(side="left", padx=(0, 12))
        
        # 标题
        title_label = tk.Label(
            logo_inner,
            text="AI Story",
            font=(Theme.FONT_FAMILY, 18, "bold"),
            bg=Theme.BG_PRIMARY,
            fg=Theme.TEXT_PRIMARY
        )
        title_label.pack(side="left")
        
        # 分隔线
        tk.Frame(self.sidebar, bg=Theme.DIVIDER, height=1).pack(fill="x", padx=20, pady=(0, 20))
        
        # 导航菜单
        self.nav_buttons = []
        self._create_nav_button("📁", "项目管理", 0)
        self._create_nav_button("📝", "故事创作", 1)
        self._create_nav_button("🎨", "图片生成", 2)
        self._create_nav_button("⚙️", "设置", 3)
        
        # 底部信息
        bottom_frame = tk.Frame(self.sidebar, bg=Theme.BG_PRIMARY)
        bottom_frame.pack(side="bottom", fill="x", pady=20)
        
        # 用户信息
        user_frame = tk.Frame(bottom_frame, bg=Theme.BG_SECONDARY)
        user_frame.pack(fill="x", padx=20, pady=10)
        
        user_inner = tk.Frame(user_frame, bg=Theme.BG_SECONDARY)
        user_inner.pack(padx=16, pady=12)
        
        tk.Label(
            user_inner,
            text="👤",
            font=(Theme.FONT_FAMILY, 16),
            bg=Theme.BG_SECONDARY,
            fg=Theme.TEXT_SECONDARY
        ).pack(side="left", padx=(0, 10))
        
        tk.Label(
            user_inner,
            text="创作者",
            font=(Theme.FONT_FAMILY, 13),
            bg=Theme.BG_SECONDARY,
            fg=Theme.TEXT_PRIMARY
        ).pack(side="left")
        
        # 版本信息
        tk.Label(
            bottom_frame,
            text="v2.0 Professional",
            font=(Theme.FONT_FAMILY, 11),
            bg=Theme.BG_PRIMARY,
            fg=Theme.TEXT_HINT
        ).pack()
    
    def _create_nav_button(self, icon, text, index):
        """创建导航按钮"""
        btn_frame = tk.Frame(self.sidebar, bg=Theme.BG_PRIMARY)
        btn_frame.pack(fill="x", padx=12, pady=4)
        
        btn = tk.Frame(btn_frame, bg=Theme.BG_PRIMARY, cursor="hand2")
        btn.pack(fill="x")
        
        # 内容
        inner = tk.Frame(btn, bg=Theme.BG_PRIMARY)
        inner.pack(fill="x", padx=16, pady=12)
        
        tk.Label(
            inner,
            text=icon,
            font=(Theme.FONT_FAMILY, 16),
            bg=Theme.BG_PRIMARY,
            fg=Theme.TEXT_SECONDARY
        ).pack(side="left", padx=(0, 12))
        
        label = tk.Label(
            inner,
            text=text,
            font=(Theme.FONT_FAMILY, 13),
            bg=Theme.BG_PRIMARY,
            fg=Theme.TEXT_SECONDARY
        )
        label.pack(side="left")
        
        # 存储组件
        btn.icon = icon
        btn.label = label
        btn.inner = inner
        btn.index = index
        
        # 绑定事件
        for widget in [btn, inner, label]:
            widget.bind("<Button-1>", lambda e, idx=index: self._on_nav_click(idx))
            widget.bind("<Enter>", lambda e, b=btn: self._on_nav_hover(b, True))
            widget.bind("<Leave>", lambda e, b=btn: self._on_nav_hover(b, False))
        
        self.nav_buttons.append(btn)
        
        # 默认选中第一个
        if index == 0:
            self._select_nav(0)
    
    def _on_nav_hover(self, btn, enter):
        """导航按钮悬停效果"""
        if enter and not hasattr(btn, 'selected'):
            btn.configure(bg=Theme.BG_HOVER)
            btn.inner.configure(bg=Theme.BG_HOVER)
            for child in btn.inner.winfo_children():
                child.configure(bg=Theme.BG_HOVER)
        elif not enter and not hasattr(btn, 'selected'):
            btn.configure(bg=Theme.BG_PRIMARY)
            btn.inner.configure(bg=Theme.BG_PRIMARY)
            for child in btn.inner.winfo_children():
                child.configure(bg=Theme.BG_PRIMARY)
    
    def _on_nav_click(self, index):
        """导航按钮点击"""
        self._select_nav(index)
        if hasattr(self, 'content_notebook'):
            self.content_notebook.select(index)
    
    def _select_nav(self, index):
        """选中导航项"""
        for i, btn in enumerate(self.nav_buttons):
            if i == index:
                btn.selected = True
                btn.configure(bg=Theme.PRIMARY_SUBTLE)
                btn.inner.configure(bg=Theme.PRIMARY_SUBTLE)
                btn.label.configure(fg=Theme.PRIMARY)
                for child in btn.inner.winfo_children():
                    if isinstance(child, tk.Label):
                        child.configure(bg=Theme.PRIMARY_SUBTLE)
                        if child.cget("text") == btn.icon:
                            child.configure(fg=Theme.PRIMARY)
            else:
                if hasattr(btn, 'selected'):
                    delattr(btn, 'selected')
                btn.configure(bg=Theme.BG_PRIMARY)
                btn.inner.configure(bg=Theme.BG_PRIMARY)
                btn.label.configure(fg=Theme.TEXT_SECONDARY)
                for child in btn.inner.winfo_children():
                    if isinstance(child, tk.Label):
                        child.configure(bg=Theme.BG_PRIMARY, fg=Theme.TEXT_SECONDARY)
    
    def _create_content_area(self):
        """创建右侧内容区"""
        self.content_area = tk.Frame(self.main_container, bg=Theme.BG_SECONDARY)
        self.content_area.pack(side="left", fill="both", expand=True)
        
        # 顶部栏
        self._create_header()
        
        # 内容区域
        self.content_frame = tk.Frame(self.content_area, bg=Theme.BG_SECONDARY)
        self.content_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # 创建内容notebook（隐藏标签）
        self.content_notebook = ttk.Notebook(self.content_frame, style="Hidden.TNotebook")
        self.content_notebook.pack(fill="both", expand=True)
        
        # 隐藏notebook标签
        self.ttk_style.configure("Hidden.TNotebook", tabposition="")
        
        # 创建页面
        self.page_project = tk.Frame(self.content_notebook, bg=Theme.BG_SECONDARY)
        self.page_story = tk.Frame(self.content_notebook, bg=Theme.BG_SECONDARY)
        self.page_image = tk.Frame(self.content_notebook, bg=Theme.BG_SECONDARY)
        self.page_settings = tk.Frame(self.content_notebook, bg=Theme.BG_SECONDARY)
        
        self.content_notebook.add(self.page_project)
        self.content_notebook.add(self.page_story)
        self.content_notebook.add(self.page_image)
        self.content_notebook.add(self.page_settings)
    
    def _create_header(self):
        """创建顶部栏"""
        header = tk.Frame(self.content_area, bg=Theme.BG_PRIMARY, height=60)
        header.pack(fill="x")
        header.pack_propagate(False)
        
        # 内容
        header_inner = tk.Frame(header, bg=Theme.BG_PRIMARY)
        header_inner.pack(fill="both", expand=True, padx=20)
        
        # 页面标题
        self.page_title = tk.Label(
            header_inner,
            text="项目管理",
            font=(Theme.FONT_FAMILY, 20, "bold"),
            bg=Theme.BG_PRIMARY,
            fg=Theme.TEXT_PRIMARY
        )
        self.page_title.place(rely=0.5, anchor="w")
        
        # 右侧操作区
        right_frame = tk.Frame(header_inner, bg=Theme.BG_PRIMARY)
        right_frame.place(relx=1, rely=0.5, anchor="e")
        
        # 搜索框
        search_frame = tk.Frame(right_frame, bg=Theme.SURFACE)
        search_frame.pack(side="left", padx=(0, 16))
        
        search_icon = tk.Label(
            search_frame,
            text="🔍",
            font=(Theme.FONT_FAMILY, 14),
            bg=Theme.SURFACE,
            fg=Theme.TEXT_HINT
        )
        search_icon.pack(side="left", padx=(12, 8))
        
        search_entry = tk.Entry(
            search_frame,
            font=(Theme.FONT_FAMILY, 12),
            bg=Theme.SURFACE,
            fg=Theme.TEXT_PRIMARY,
            bd=0,
            width=20,
            insertbackground=Theme.PRIMARY
        )
        search_entry.pack(side="left", pady=8)
        search_entry.insert(0, "搜索...")
        search_entry.bind("<FocusIn>", lambda e: search_entry.delete(0, tk.END) if search_entry.get() == "搜索..." else None)
        search_entry.bind("<FocusOut>", lambda e: search_entry.insert(0, "搜索...") if not search_entry.get() else None)
        
        tk.Label(search_frame, bg=Theme.SURFACE, width=1).pack(side="left", padx=8)
        
        # 通知图标
        notif_btn = tk.Label(
            right_frame,
            text="🔔",
            font=(Theme.FONT_FAMILY, 18),
            bg=Theme.BG_PRIMARY,
            fg=Theme.TEXT_SECONDARY,
            cursor="hand2"
        )
        notif_btn.pack(side="left", padx=8)
        
        # 设置图标
        settings_btn = tk.Label(
            right_frame,
            text="⚙️",
            font=(Theme.FONT_FAMILY, 18),
            bg=Theme.BG_PRIMARY,
            fg=Theme.TEXT_SECONDARY,
            cursor="hand2"
        )
        settings_btn.pack(side="left", padx=8)
    
    def _build_modern_ui(self):
        """构建现代化UI内容"""
        # 使用原有mixin构建页面
        self._build_project_page()
        self._build_story_page()
        self._build_image_page()
        self._build_settings_page()
        
        # 应用现代化样式
        self._apply_modern_theme()
    
    def _build_settings_page(self):
        """构建设置页面"""
        # 标题
        title = tk.Label(
            self.page_settings,
            text="设置",
            font=(Theme.FONT_FAMILY, 24, "bold"),
            bg=Theme.BG_SECONDARY,
            fg=Theme.TEXT_PRIMARY
        )
        title.pack(anchor="w", pady=(0, 20))
        
        # 设置卡片
        card = ModernCard(self.page_settings, variant="card", padding=24)
        card.pack(fill="x", pady=10)
        
        settings_label = card.add_widget(
            tk.Label,
            text="系统设置",
            font=(Theme.FONT_FAMILY, 16, "bold"),
            bg=Theme.SURFACE,
            fg=Theme.TEXT_PRIMARY
        )
        settings_label.pack(anchor="w", pady=(0, 16))
        
        # 设置项
        self._create_setting_item(card, "深色模式", "开启深色主题")
        self._create_setting_item(card, "自动保存", "每5分钟自动保存")
        self._create_setting_item(card, "通知提醒", "开启系统通知")
    
    def _create_setting_item(self, parent, title, desc):
        """创建设置项"""
        item_frame = parent.add_widget(tk.Frame, bg=Theme.SURFACE)
        item_frame.pack(fill="x", pady=8)
        
        # 左侧文本
        text_frame = tk.Frame(item_frame, bg=Theme.SURFACE)
        text_frame.pack(side="left")
        
        tk.Label(
            text_frame,
            text=title,
            font=(Theme.FONT_FAMILY, 13),
            bg=Theme.SURFACE,
            fg=Theme.TEXT_PRIMARY
        ).pack(anchor="w")
        
        tk.Label(
            text_frame,
            text=desc,
            font=(Theme.FONT_FAMILY, 11),
            bg=Theme.SURFACE,
            fg=Theme.TEXT_SECONDARY
        ).pack(anchor="w")
        
        # 右侧开关
        from .custom_widgets import ModernSwitch
        switch = ModernSwitch(item_frame, bg=Theme.SURFACE)
        switch.pack(side="right")
    
    def _apply_modern_theme(self):
        """应用现代化主题到已创建的组件"""
        # 更新页面背景
        for page in [self.page_project, self.page_story, self.page_image]:
            page.configure(bg=Theme.BG_SECONDARY)
            self._apply_theme_to_children(page)
    
    def _apply_theme_to_children(self, widget):
        """递归应用主题到所有子组件"""
        try:
            widget_class = widget.winfo_class()
            
            # 跳过ttk组件
            if widget_class in ["TCombobox", "TSpinbox", "TNotebook", "TButton", "TEntry", "TFrame", "TLabelframe"]:
                for child in widget.winfo_children():
                    self._apply_theme_to_children(child)
                return
            
            # 应用主题
            if widget_class == "Frame":
                widget.configure(bg=Theme.BG_SECONDARY)
            elif widget_class == "Label":
                current_bg = widget.cget("bg")
                if current_bg in ["#2b2b2b", "#1e1e1e", "SystemButtonFace", ""]:
                    widget.configure(bg=Theme.BG_SECONDARY)
            
            # 递归处理子组件
            for child in widget.winfo_children():
                self._apply_theme_to_children(child)
        except:
            pass





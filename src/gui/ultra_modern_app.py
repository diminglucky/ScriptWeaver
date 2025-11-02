"""
Ultra Modern UI - 极致现代化设计
采用最新设计趋势：宽屏布局、玻璃态效果、流畅动画
"""

import tkinter as tk
from tkinter import ttk
import os
from pathlib import Path
from datetime import datetime

from .theme import Theme, Styles, Icons
from .mixins.story_modules import StoryMixin
from .mixins.image_modules import ImageMixin
from .mixins.project_mixin import ProjectMixin
from .mixins.config_modules import ConfigMixin
from .mixins.kb_mixin import KbMixin
from .mixins.ui_mixin import UiMixin


class UltraModernTheme(Theme):
    """增强版现代主题 - 更精致的配色和效果"""
    
    # 新增主色调 - 渐变紫蓝
    PRIMARY_GRADIENT_START = "#7C3AED"  # Purple-600
    PRIMARY_GRADIENT_END = "#4F46E5"    # Indigo-600
    PRIMARY_SUBTLE = "#1E1B3A"  # 主色的微妙背景变体
    
    # 新增特殊颜色
    GLASS_OVERLAY = "rgba(255, 255, 255, 0.05)"  # 玻璃态叠加
    SURFACE_ELEVATED = "#1A1B23"  # 抬高的表面
    SURFACE_SPOTLIGHT = "#1F2028"  # 聚光灯区域
    
    # 新增文本颜色
    TEXT_ACCENT = "#A78BFA"  # Purple-400 - 强调文本
    TEXT_ON_PRIMARY = "#FFFFFF"  # 主色上的文本
    
    # 新增边框
    BORDER_ACCENT = "#5B21B6"  # Purple-800
    BORDER_GLASS = "rgba(139, 92, 246, 0.3)"  # 玻璃态边框
    
    # 新增状态颜色变体
    SUCCESS_LIGHT = "#34D399"  # Emerald-400
    WARNING_LIGHT = "#FBBF24"  # Amber-400
    ERROR_LIGHT = "#F87171"    # Red-400
    
    # 新增装饰颜色
    GRADIENT_PURPLE = "linear-gradient(135deg, #667EEA 0%, #764BA2 100%)"
    GRADIENT_BLUE = "linear-gradient(135deg, #667EEA 0%, #4F46E5 100%)"
    GRADIENT_CYAN = "linear-gradient(135deg, #06B6D4 0%, #3B82F6 100%)"
    
    # 圆角增强
    RADIUS_ROUND = 24  # 更圆润
    RADIUS_PILL = 999  # 药丸形状


class UltraModernApp(tk.Tk, ProjectMixin, StoryMixin, ImageMixin, KbMixin, ConfigMixin, UiMixin):
    """
    Ultra Modern UI应用 - 极致现代化设计
    
    设计特点：
    - 1680x960 黄金比例窗口（21:12 ≈ 16:9.14）
    - 侧边栏 + 主内容区 + 右侧面板三栏布局
    - 玻璃态效果和柔和渐变
    - 流畅的交互动画
    - 卡片化内容展示
    - 现代化导航体验
    """
    
    def __init__(self):
        super().__init__()
        
        # === 窗口配置 - 现代化尺寸 ===
        self.title("✨ AI Story Creator Pro - 智能创作平台")
        
        # 黄金比例窗口：1680x960 (21:12)
        window_width = 1680
        window_height = 960
        
        # 居中显示
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        x = (screen_width - window_width) // 2
        y = (screen_height - window_height) // 2
        
        self.geometry(f"{window_width}x{window_height}+{x}+{y}")
        self.minsize(1400, 800)  # 最小尺寸
        
        # 设置窗口背景
        self.configure(bg=UltraModernTheme.BG_PRIMARY)
        
        # 尝试设置窗口图标（可选）
        try:
            self.iconphoto(True, tk.PhotoImage(data=self._get_app_icon_data()))
        except:
            pass
        
        # 加载环境变量
        from dotenv import load_dotenv
        load_dotenv()
        
        # 初始化变量
        self._init_variables()
        
        # 应用超现代样式
        self._setup_ultra_modern_styles()
        
        # 创建主布局
        self._create_main_layout()
        
        # 构建UI内容
        self._build_ui()
        
        # 应用主题
        self._apply_modern_theme()
        
        # 启动动画和自动功能
        self.after(100, self._auto_load_api_config)
        self.after(100, self._start_animations)
        
        # 启用自动保存（每5分钟）
        if hasattr(self, 'enable_auto_save'):
            self.enable_auto_save(interval_minutes=5)
            print("✅ 自动保存功能已启用（每5分钟）")
    
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
        self.use_project_stories = tk.BooleanVar(value=False)  # 是否使用项目故事作为知识库
        
        # 故事内容
        self.current_outline: str | None = None
        
        # 项目管理
        from src.project_manager import ProjectManager
        self.project_manager = ProjectManager()
        self.current_project = None
        
        # 章节管理
        self.parsed_sections: list[dict] = []
        self.generated_content: str = ""
        
        # UI状态
        self.current_page = 0
        self.sidebar_expanded = True
    
    def _setup_ultra_modern_styles(self):
        """设置超现代化ttk组件样式"""
        self.ttk_style = ttk.Style()
        self.ttk_style.theme_use('clam')
        
        # === Notebook样式 - 极简隐藏 ===
        self.ttk_style.configure(
            "UltraModern.TNotebook",
            background=UltraModernTheme.BG_SECONDARY,
            borderwidth=0,
            tabmargins=[0, 0, 0, 0]
        )
        # 完全隐藏标签页
        self.ttk_style.layout("UltraModern.TNotebook.Tab", [])
        
        # === Frame样式 ===
        self.ttk_style.configure(
            "UltraModern.TFrame",
            background=UltraModernTheme.BG_SECONDARY,
            borderwidth=0
        )
        
        self.ttk_style.configure(
            "Card.TFrame",
            background=UltraModernTheme.SURFACE,
            borderwidth=0
        )
        
        # === LabelFrame样式 - 现代卡片 ===
        self.ttk_style.configure(
            "UltraModern.TLabelframe",
            background=UltraModernTheme.SURFACE,
            foreground=UltraModernTheme.TEXT_PRIMARY,
            borderwidth=0,
            relief="flat"
        )
        self.ttk_style.configure(
            "UltraModern.TLabelframe.Label",
            background=UltraModernTheme.SURFACE,
            foreground=UltraModernTheme.TEXT_PRIMARY,
            font=(UltraModernTheme.FONT_FAMILY, 14, "bold"),
            padding=[0, 0, 0, 12]
        )
        
        # === Button样式 - 现代按钮 ===
        self.ttk_style.configure(
            "UltraModern.TButton",
            background=UltraModernTheme.PRIMARY,
            foreground=UltraModernTheme.TEXT_ON_PRIMARY,
            borderwidth=0,
            relief="flat",
            padding=[28, 14],
            font=(UltraModernTheme.FONT_FAMILY, 13, "bold")
        )
        self.ttk_style.map(
            "UltraModern.TButton",
            background=[
                ("active", UltraModernTheme.PRIMARY_LIGHT),
                ("pressed", UltraModernTheme.PRIMARY_DARK),
                ("disabled", UltraModernTheme.BG_TERTIARY)
            ],
            foreground=[
                ("disabled", UltraModernTheme.TEXT_DISABLED)
            ]
        )
        
        # === Entry样式 ===
        self.ttk_style.configure(
            "UltraModern.TEntry",
            fieldbackground=UltraModernTheme.SURFACE,
            foreground=UltraModernTheme.TEXT_PRIMARY,
            borderwidth=2,
            bordercolor=UltraModernTheme.BORDER,
            insertcolor=UltraModernTheme.PRIMARY,
            padding=[16, 12]
        )
        self.ttk_style.map(
            "UltraModern.TEntry",
            fieldbackground=[("focus", UltraModernTheme.SURFACE_DARK)],
            bordercolor=[("focus", UltraModernTheme.BORDER_FOCUS)]
        )
        
        # === Combobox样式 ===
        self.ttk_style.configure(
            "UltraModern.TCombobox",
            fieldbackground=UltraModernTheme.SURFACE,
            background=UltraModernTheme.SURFACE,
            foreground=UltraModernTheme.TEXT_PRIMARY,
            borderwidth=2,
            bordercolor=UltraModernTheme.BORDER,
            arrowcolor=UltraModernTheme.TEXT_ACCENT,
            padding=[16, 12]
        )
        self.ttk_style.map(
            "UltraModern.TCombobox",
            fieldbackground=[("focus", UltraModernTheme.SURFACE_DARK)],
            bordercolor=[("focus", UltraModernTheme.BORDER_FOCUS)]
        )
    
    def _create_main_layout(self):
        """创建主布局 - 三栏式现代布局"""
        # === 主容器 ===
        self.main_container = tk.Frame(self, bg=UltraModernTheme.BG_PRIMARY)
        self.main_container.pack(fill="both", expand=True)
        
        # === 左侧导航栏 ===
        self._create_sidebar()
        
        # === 中央内容区 ===
        self._create_content_area()
        
        # === 右侧信息面板（可选，默认隐藏）===
        # self._create_right_panel()
    
    def _create_sidebar(self):
        """创建左侧导航栏 - 优雅的垂直导航"""
        # 侧边栏容器 - 固定宽度280px
        self.sidebar = tk.Frame(
            self.main_container,
            bg=UltraModernTheme.BG_PRIMARY,
            width=280
        )
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)
        
        # === Logo区域 - 品牌标识 ===
        logo_area = tk.Frame(self.sidebar, bg=UltraModernTheme.BG_PRIMARY, height=100)
        logo_area.pack(fill="x")
        logo_area.pack_propagate(False)
        
        # Logo容器 - 居中
        logo_container = tk.Frame(logo_area, bg=UltraModernTheme.BG_PRIMARY)
        logo_container.place(relx=0.5, rely=0.5, anchor="center")
        
        # 精致的Logo图标 - 渐变圆形
        logo_canvas = tk.Canvas(
            logo_container,
            width=50,
            height=50,
            bg=UltraModernTheme.BG_PRIMARY,
            highlightthickness=0
        )
        logo_canvas.pack(side="left", padx=(0, 16))
        
        # 外圈光晕
        logo_canvas.create_oval(
            0, 0, 50, 50,
            fill="",
            outline=UltraModernTheme.PRIMARY_LIGHT,
            width=2
        )
        # 主圆 - 渐变效果（通过多层模拟）
        logo_canvas.create_oval(
            5, 5, 45, 45,
            fill=UltraModernTheme.PRIMARY,
            outline=""
        )
        # 内圈高光
        logo_canvas.create_oval(
            10, 10, 40, 40,
            fill="",
            outline=UltraModernTheme.PRIMARY_LIGHT,
            width=1
        )
        # Logo图标
        logo_canvas.create_text(
            25, 25,
            text="✨",
            font=(UltraModernTheme.FONT_FAMILY, 24),
            fill="#FFFFFF"
        )
        
        # Logo文字
        logo_text_frame = tk.Frame(logo_container, bg=UltraModernTheme.BG_PRIMARY)
        logo_text_frame.pack(side="left")
        
        tk.Label(
            logo_text_frame,
            text="Story Creator",
            font=(UltraModernTheme.FONT_FAMILY, 18, "bold"),
            bg=UltraModernTheme.BG_PRIMARY,
            fg=UltraModernTheme.TEXT_PRIMARY
        ).pack(anchor="w")
        
        tk.Label(
            logo_text_frame,
            text="AI Powered",
            font=(UltraModernTheme.FONT_FAMILY, 10),
            bg=UltraModernTheme.BG_PRIMARY,
            fg=UltraModernTheme.TEXT_ACCENT
        ).pack(anchor="w")
        
        # === 精致分隔线 ===
        separator = tk.Frame(
            self.sidebar,
            bg=UltraModernTheme.DIVIDER_LIGHT,
            height=1
        )
        separator.pack(fill="x", padx=24, pady=(0, 24))
        
        # === 导航菜单区域 ===
        nav_area = tk.Frame(self.sidebar, bg=UltraModernTheme.BG_PRIMARY)
        nav_area.pack(fill="both", expand=True, padx=16)
        
        # 创建导航按钮
        self.nav_buttons = []
        nav_items = [
            {"icon": "📁", "text": "项目管理", "desc": "管理你的创作项目"},
            {"icon": "📝", "text": "故事创作", "desc": "AI智能故事生成"},
            {"icon": "🎨", "text": "图片生成", "desc": "创作精美配图"},
            {"icon": "⚙️", "text": "系统设置", "desc": "配置和偏好设置"}
        ]
        
        for i, item in enumerate(nav_items):
            self._create_nav_item(nav_area, item, i)
        
        # 默认选中第一项
        self._select_nav(0)
        
        # === 底部区域 ===
        bottom_area = tk.Frame(self.sidebar, bg=UltraModernTheme.BG_PRIMARY)
        bottom_area.pack(side="bottom", fill="x", pady=24, padx=16)
        
        # 用户信息卡片 - 精致设计
        user_card = tk.Frame(
            bottom_area,
            bg=UltraModernTheme.SURFACE_ELEVATED,
            highlightthickness=1,
            highlightbackground=UltraModernTheme.BORDER
        )
        user_card.pack(fill="x", pady=(0, 16))
        
        user_inner = tk.Frame(user_card, bg=UltraModernTheme.SURFACE_ELEVATED)
        user_inner.pack(padx=16, pady=14)
        
        # 用户头像
        avatar_canvas = tk.Canvas(
            user_inner,
            width=40,
            height=40,
            bg=UltraModernTheme.SURFACE_ELEVATED,
            highlightthickness=0
        )
        avatar_canvas.pack(side="left", padx=(0, 12))
        avatar_canvas.create_oval(
            0, 0, 40, 40,
            fill=UltraModernTheme.PRIMARY,
            outline=UltraModernTheme.PRIMARY_LIGHT,
            width=2
        )
        avatar_canvas.create_text(
            20, 20,
            text="👤",
            font=(UltraModernTheme.FONT_FAMILY, 18),
            fill="#FFFFFF"
        )
        
        # 用户信息
        user_info = tk.Frame(user_inner, bg=UltraModernTheme.SURFACE_ELEVATED)
        user_info.pack(side="left", fill="both", expand=True)
        
        tk.Label(
            user_info,
            text="创作者",
            font=(UltraModernTheme.FONT_FAMILY, 13, "bold"),
            bg=UltraModernTheme.SURFACE_ELEVATED,
            fg=UltraModernTheme.TEXT_PRIMARY
        ).pack(anchor="w")
        
        tk.Label(
            user_info,
            text="专业版用户",
            font=(UltraModernTheme.FONT_FAMILY, 10),
            bg=UltraModernTheme.SURFACE_ELEVATED,
            fg=UltraModernTheme.TEXT_SECONDARY
        ).pack(anchor="w")
        
        # 版本信息
        version_label = tk.Label(
            bottom_area,
            text="v2.0 Professional Edition",
            font=(UltraModernTheme.FONT_FAMILY, 10),
            bg=UltraModernTheme.BG_PRIMARY,
            fg=UltraModernTheme.TEXT_HINT
        )
        version_label.pack()
    
    def _create_nav_item(self, parent, item, index):
        """创建导航项 - 精致的卡片式设计"""
        # 导航项容器
        nav_item = tk.Frame(parent, bg=UltraModernTheme.BG_PRIMARY, cursor="hand2")
        nav_item.pack(fill="x", pady=6)
        
        # 内部容器
        inner = tk.Frame(nav_item, bg=UltraModernTheme.BG_PRIMARY)
        inner.pack(fill="x", padx=12, pady=14)
        
        # 图标
        icon_label = tk.Label(
            inner,
            text=item["icon"],
            font=(UltraModernTheme.FONT_FAMILY, 20),
            bg=UltraModernTheme.BG_PRIMARY,
            fg=UltraModernTheme.TEXT_SECONDARY
        )
        icon_label.pack(side="left", padx=(0, 14))
        
        # 文本区域
        text_frame = tk.Frame(inner, bg=UltraModernTheme.BG_PRIMARY)
        text_frame.pack(side="left", fill="both", expand=True)
        
        text_label = tk.Label(
            text_frame,
            text=item["text"],
            font=(UltraModernTheme.FONT_FAMILY, 14, "bold"),
            bg=UltraModernTheme.BG_PRIMARY,
            fg=UltraModernTheme.TEXT_SECONDARY,
            anchor="w"
        )
        text_label.pack(anchor="w")
        
        desc_label = tk.Label(
            text_frame,
            text=item["desc"],
            font=(UltraModernTheme.FONT_FAMILY, 10),
            bg=UltraModernTheme.BG_PRIMARY,
            fg=UltraModernTheme.TEXT_HINT,
            anchor="w"
        )
        desc_label.pack(anchor="w")
        
        # 选中指示器（初始隐藏）
        indicator = tk.Frame(
            nav_item,
            bg=UltraModernTheme.PRIMARY,
            width=4
        )
        
        # 存储引用
        nav_item.inner = inner
        nav_item.icon_label = icon_label
        nav_item.text_label = text_label
        nav_item.desc_label = desc_label
        nav_item.indicator = indicator
        nav_item.index = index
        
        # 绑定事件
        widgets = [nav_item, inner, icon_label, text_frame, text_label, desc_label]
        for widget in widgets:
            widget.bind("<Button-1>", lambda e, idx=index: self._on_nav_click(idx))
            widget.bind("<Enter>", lambda e, item=nav_item: self._on_nav_hover(item, True))
            widget.bind("<Leave>", lambda e, item=nav_item: self._on_nav_hover(item, False))
        
        self.nav_buttons.append(nav_item)
    
    def _on_nav_hover(self, nav_item, is_enter):
        """导航项悬停效果"""
        # 只在未选中时显示悬停效果
        if not hasattr(nav_item, 'selected') or not nav_item.selected:
            if is_enter:
                nav_item.configure(bg=UltraModernTheme.BG_HOVER)
                nav_item.inner.configure(bg=UltraModernTheme.BG_HOVER)
                nav_item.icon_label.configure(bg=UltraModernTheme.BG_HOVER)
                nav_item.text_label.configure(bg=UltraModernTheme.BG_HOVER, fg=UltraModernTheme.TEXT_PRIMARY)
                nav_item.desc_label.configure(bg=UltraModernTheme.BG_HOVER)
            else:
                nav_item.configure(bg=UltraModernTheme.BG_PRIMARY)
                nav_item.inner.configure(bg=UltraModernTheme.BG_PRIMARY)
                nav_item.icon_label.configure(bg=UltraModernTheme.BG_PRIMARY)
                nav_item.text_label.configure(bg=UltraModernTheme.BG_PRIMARY, fg=UltraModernTheme.TEXT_SECONDARY)
                nav_item.desc_label.configure(bg=UltraModernTheme.BG_PRIMARY)
    
    def _on_nav_click(self, index):
        """导航项点击事件"""
        self._select_nav(index)
        if hasattr(self, 'content_notebook'):
            self.content_notebook.select(index)
            # 更新页面标题
            page_titles = ["项目管理", "故事创作", "图片生成", "系统设置"]
            if hasattr(self, 'page_title_label'):
                self.page_title_label.config(text=page_titles[index])
    
    def _select_nav(self, index):
        """选中导航项 - 精致的视觉反馈"""
        for i, nav_item in enumerate(self.nav_buttons):
            if i == index:
                # 选中状态
                nav_item.selected = True
                nav_item.configure(bg=UltraModernTheme.PRIMARY_SUBTLE)
                nav_item.inner.configure(bg=UltraModernTheme.PRIMARY_SUBTLE)
                nav_item.icon_label.configure(
                    bg=UltraModernTheme.PRIMARY_SUBTLE,
                    fg=UltraModernTheme.PRIMARY
                )
                nav_item.text_label.configure(
                    bg=UltraModernTheme.PRIMARY_SUBTLE,
                    fg=UltraModernTheme.PRIMARY
                )
                nav_item.desc_label.configure(
                    bg=UltraModernTheme.PRIMARY_SUBTLE,
                    fg=UltraModernTheme.TEXT_SECONDARY
                )
                # 显示指示器
                nav_item.indicator.place(x=0, y=0, relheight=1)
            else:
                # 未选中状态
                nav_item.selected = False
                nav_item.configure(bg=UltraModernTheme.BG_PRIMARY)
                nav_item.inner.configure(bg=UltraModernTheme.BG_PRIMARY)
                nav_item.icon_label.configure(
                    bg=UltraModernTheme.BG_PRIMARY,
                    fg=UltraModernTheme.TEXT_SECONDARY
                )
                nav_item.text_label.configure(
                    bg=UltraModernTheme.BG_PRIMARY,
                    fg=UltraModernTheme.TEXT_SECONDARY
                )
                nav_item.desc_label.configure(
                    bg=UltraModernTheme.BG_PRIMARY,
                    fg=UltraModernTheme.TEXT_HINT
                )
                # 隐藏指示器
                nav_item.indicator.place_forget()
    
    def _create_content_area(self):
        """创建中央内容区 - 宽敞的工作空间"""
        # 内容区容器
        self.content_area = tk.Frame(
            self.main_container,
            bg=UltraModernTheme.BG_SECONDARY
        )
        self.content_area.pack(side="left", fill="both", expand=True)
        
        # === 顶部导航栏 ===
        self._create_top_bar()
        
        # === 主内容区 ===
        # 添加内边距，让内容更有呼吸感
        content_wrapper = tk.Frame(
            self.content_area,
            bg=UltraModernTheme.BG_SECONDARY
        )
        content_wrapper.pack(fill="both", expand=True, padx=32, pady=(0, 32))
        
        # Notebook（隐藏标签）
        self.content_notebook = ttk.Notebook(
            content_wrapper,
            style="UltraModern.TNotebook"
        )
        self.content_notebook.pack(fill="both", expand=True)
        
        # 创建页面
        self.page_project = tk.Frame(
            self.content_notebook,
            bg=UltraModernTheme.BG_SECONDARY
        )
        self.page_story = tk.Frame(
            self.content_notebook,
            bg=UltraModernTheme.BG_SECONDARY
        )
        self.page_image = tk.Frame(
            self.content_notebook,
            bg=UltraModernTheme.BG_SECONDARY
        )
        self.page_config = tk.Frame(
            self.content_notebook,
            bg=UltraModernTheme.BG_SECONDARY
        )
        
        self.content_notebook.add(self.page_project)
        self.content_notebook.add(self.page_story)
        self.content_notebook.add(self.page_image)
        self.content_notebook.add(self.page_config)
        
        # === 底部状态栏 ===
        self._create_status_bar()
    
    def _create_top_bar(self):
        """创建顶部栏 - 现代化设计"""
        # 顶部栏容器
        top_bar = tk.Frame(
            self.content_area,
            bg=UltraModernTheme.BG_SECONDARY,
            height=80
        )
        top_bar.pack(fill="x")
        top_bar.pack_propagate(False)
        
        # 内容容器
        top_content = tk.Frame(top_bar, bg=UltraModernTheme.BG_SECONDARY)
        top_content.pack(fill="both", expand=True, padx=32, pady=20)
        
        # === 左侧：页面标题 ===
        left_frame = tk.Frame(top_content, bg=UltraModernTheme.BG_SECONDARY)
        left_frame.pack(side="left")
        
        self.page_title_label = tk.Label(
            left_frame,
            text="项目管理",
            font=(UltraModernTheme.FONT_FAMILY, 26, "bold"),
            bg=UltraModernTheme.BG_SECONDARY,
            fg=UltraModernTheme.TEXT_PRIMARY
        )
        self.page_title_label.pack(anchor="w")
        
        # 面包屑导航
        breadcrumb = tk.Label(
            left_frame,
            text="首页 / 项目管理",
            font=(UltraModernTheme.FONT_FAMILY, 11),
            bg=UltraModernTheme.BG_SECONDARY,
            fg=UltraModernTheme.TEXT_HINT
        )
        breadcrumb.pack(anchor="w", pady=(4, 0))
        
        # === 右侧：工具栏 ===
        right_frame = tk.Frame(top_content, bg=UltraModernTheme.BG_SECONDARY)
        right_frame.pack(side="right")
        
        # 搜索框 - 精致设计
        search_container = tk.Frame(
            right_frame,
            bg=UltraModernTheme.SURFACE,
            highlightthickness=1,
            highlightbackground=UltraModernTheme.BORDER
        )
        search_container.pack(side="left", padx=(0, 16))
        
        search_icon = tk.Label(
            search_container,
            text="🔍",
            font=(UltraModernTheme.FONT_FAMILY, 14),
            bg=UltraModernTheme.SURFACE,
            fg=UltraModernTheme.TEXT_HINT
        )
        search_icon.pack(side="left", padx=(14, 8))
        
        search_entry = tk.Entry(
            search_container,
            font=(UltraModernTheme.FONT_FAMILY, 12),
            bg=UltraModernTheme.SURFACE,
            fg=UltraModernTheme.TEXT_PRIMARY,
            bd=0,
            width=24,
            insertbackground=UltraModernTheme.PRIMARY
        )
        search_entry.pack(side="left", pady=12, padx=(0, 14))
        search_entry.insert(0, "搜索项目、故事...")
        
        # 搜索框占位符效果
        def on_search_focus_in(e):
            if search_entry.get() == "搜索项目、故事...":
                search_entry.delete(0, tk.END)
                search_entry.config(fg=UltraModernTheme.TEXT_PRIMARY)
        
        def on_search_focus_out(e):
            if not search_entry.get():
                search_entry.insert(0, "搜索项目、故事...")
                search_entry.config(fg=UltraModernTheme.TEXT_HINT)
        
        search_entry.bind("<FocusIn>", on_search_focus_in)
        search_entry.bind("<FocusOut>", on_search_focus_out)
        search_entry.config(fg=UltraModernTheme.TEXT_HINT)
        
        # 通知按钮 - 精致圆形
        notif_btn = self._create_icon_button(
            right_frame,
            "🔔",
            lambda: self._show_notification("暂无新通知")
        )
        notif_btn.pack(side="left", padx=6)
        
        # 帮助按钮
        help_btn = self._create_icon_button(
            right_frame,
            "❓",
            lambda: self._show_help()
        )
        help_btn.pack(side="left", padx=6)
    
    def _create_icon_button(self, parent, icon, command):
        """创建图标按钮 - 圆形设计"""
        btn_size = 44
        
        canvas = tk.Canvas(
            parent,
            width=btn_size,
            height=btn_size,
            bg=UltraModernTheme.BG_SECONDARY,
            highlightthickness=0,
            cursor="hand2"
        )
        
        # 背景圆形
        bg_circle = canvas.create_oval(
            0, 0, btn_size, btn_size,
            fill=UltraModernTheme.SURFACE,
            outline=UltraModernTheme.BORDER,
            width=1
        )
        
        # 图标
        icon_text = canvas.create_text(
            btn_size // 2, btn_size // 2,
            text=icon,
            font=(UltraModernTheme.FONT_FAMILY, 18),
            fill=UltraModernTheme.TEXT_SECONDARY
        )
        
        # 悬停效果
        def on_enter(e):
            canvas.itemconfig(bg_circle, fill=UltraModernTheme.BG_HOVER)
            canvas.itemconfig(icon_text, fill=UltraModernTheme.TEXT_PRIMARY)
        
        def on_leave(e):
            canvas.itemconfig(bg_circle, fill=UltraModernTheme.SURFACE)
            canvas.itemconfig(icon_text, fill=UltraModernTheme.TEXT_SECONDARY)
        
        def on_click(e):
            command()
        
        canvas.bind("<Enter>", on_enter)
        canvas.bind("<Leave>", on_leave)
        canvas.bind("<Button-1>", on_click)
        
        return canvas
    
    def _create_status_bar(self):
        """创建底部状态栏 - 精致信息栏"""
        # 分隔线
        tk.Frame(
            self.content_area,
            bg=UltraModernTheme.DIVIDER,
            height=1
        ).pack(fill="x", side="bottom")
        
        # 状态栏容器
        status_bar = tk.Frame(
            self.content_area,
            bg=UltraModernTheme.BG_PRIMARY,
            height=40
        )
        status_bar.pack(fill="x", side="bottom")
        status_bar.pack_propagate(False)
        
        # === 左侧：状态信息 ===
        left_status = tk.Frame(status_bar, bg=UltraModernTheme.BG_PRIMARY)
        left_status.pack(side="left", padx=32, pady=10)
        
        # 状态指示点
        status_dot = tk.Canvas(
            left_status,
            width=12,
            height=12,
            bg=UltraModernTheme.BG_PRIMARY,
            highlightthickness=0
        )
        status_dot.pack(side="left", padx=(0, 10))
        status_dot.create_oval(
            0, 0, 12, 12,
            fill=UltraModernTheme.SUCCESS,
            outline=UltraModernTheme.SUCCESS_LIGHT,
            width=2
        )
        
        # 状态文本
        if not hasattr(self, 'status'):
            self.status = tk.StringVar(value="系统就绪 · 一切正常")
        
        status_label = tk.Label(
            left_status,
            textvariable=self.status,
            font=(UltraModernTheme.FONT_FAMILY, 11),
            bg=UltraModernTheme.BG_PRIMARY,
            fg=UltraModernTheme.TEXT_SECONDARY
        )
        status_label.pack(side="left")
        
        # === 右侧：系统信息 ===
        right_status = tk.Frame(status_bar, bg=UltraModernTheme.BG_PRIMARY)
        right_status.pack(side="right", padx=32, pady=10)
        
        # 时间显示
        self.time_label = tk.Label(
            right_status,
            text="",
            font=(UltraModernTheme.FONT_FAMILY, 11),
            bg=UltraModernTheme.BG_PRIMARY,
            fg=UltraModernTheme.TEXT_HINT
        )
        self.time_label.pack(side="right", padx=(16, 0))
        
        # 分隔符
        tk.Label(
            right_status,
            text="·",
            font=(UltraModernTheme.FONT_FAMILY, 11),
            bg=UltraModernTheme.BG_PRIMARY,
            fg=UltraModernTheme.BORDER_LIGHT
        ).pack(side="right", padx=10)
        
        # 版本标签
        tk.Label(
            right_status,
            text="Pro v2.0",
            font=(UltraModernTheme.FONT_FAMILY, 11, "bold"),
            bg=UltraModernTheme.BG_PRIMARY,
            fg=UltraModernTheme.TEXT_HINT
        ).pack(side="right")
        
        # 启动时间更新
        self._update_time()
    
    def _update_time(self):
        """更新时间显示"""
        try:
            now = datetime.now().strftime("%H:%M:%S")
            if hasattr(self, 'time_label'):
                self.time_label.config(text=now)
            self.after(1000, self._update_time)
        except:
            pass
    
    def _apply_modern_theme(self):
        """应用现代化主题到已创建的组件"""
        if hasattr(self, 'notebook'):
            self.notebook.configure(style="UltraModern.TNotebook")
            self.notebook.pack_configure(padx=0, pady=0)
        
        # 更新页面背景
        for page in [self.page_project, self.page_story, self.page_image]:
            page.configure(bg=UltraModernTheme.BG_SECONDARY)
            self._apply_theme_to_children(page)
    
    def _apply_theme_to_children(self, widget):
        """递归应用主题到所有子组件"""
        try:
            widget_class = widget.winfo_class()
            
            # 跳过ttk组件
            if widget_class.startswith("T"):
                for child in widget.winfo_children():
                    self._apply_theme_to_children(child)
                return
            
            # 应用主题
            if widget_class == "Frame":
                widget.configure(bg=UltraModernTheme.BG_SECONDARY)
            elif widget_class == "Label":
                current_bg = widget.cget("bg")
                if current_bg in ["#2b2b2b", "#1e1e1e", "SystemButtonFace", ""]:
                    widget.configure(bg=UltraModernTheme.BG_SECONDARY)
            
            # 递归处理子组件
            for child in widget.winfo_children():
                self._apply_theme_to_children(child)
        except:
            pass
    
    def _start_animations(self):
        """启动UI动画效果（占位，未来可扩展）"""
        pass
    
    def _show_notification(self, message):
        """显示通知（占位方法）"""
        if hasattr(self, 'status'):
            self.status.set(f"💬 {message}")
    
    def _show_help(self):
        """显示帮助（占位方法）"""
        if hasattr(self, 'status'):
            self.status.set("📖 帮助文档：访问项目主页查看详细文档")
    
    def _get_app_icon_data(self):
        """获取应用图标数据（占位，返回空）"""
        return ""
    
    def update_header_status(self, text: str, icon: str = "🔄", color: str = None):
        """更新顶部状态（兼容性方法）"""
        if hasattr(self, 'status'):
            self.status.set(f"{icon} {text}")


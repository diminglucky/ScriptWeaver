"""
现代化UI主窗口 - 使用原有Mixin功能，应用现代化主题
"""

import tkinter as tk
from tkinter import ttk
import os
from pathlib import Path
from datetime import datetime

from .theme import Theme, Styles, Icons
from .mixins.story_mixin import StoryMixin
from .mixins.image_mixin import ImageMixin
from .mixins.project_mixin import ProjectMixin
from .mixins.config_mixin import ConfigMixin
from .mixins.kb_mixin import KbMixin
from .mixins.ui_mixin import UiMixin


class ModernApp(tk.Tk, ProjectMixin, StoryMixin, ImageMixin, KbMixin, ConfigMixin, UiMixin):
    """现代化专业UI应用 - 整合所有原有功能"""
    
    def __init__(self):
        super().__init__()
        
        # 窗口配置
        self.title("AI Story Creator Pro - 智能故事创作平台")
        self.geometry("1400x900")
        self.minsize(1200, 700)
        
        # 设置窗口背景色
        self.configure(bg=Theme.BG_PRIMARY)
        
        # 加载环境变量
        from dotenv import load_dotenv
        load_dotenv()
        
        # 初始化所有必需的变量（原有功能需要）
        self._init_variables()
        
        # 应用现代化样式
        self._setup_modern_styles()
        
        # 创建现代化的顶部栏
        self._create_modern_header()
        
        # 调用原有的UI构建方法（来自UiMixin）
        # 这会创建完整的notebook和所有页面
        self._build_ui()
        
        # 应用现代化主题到现有组件
        self._apply_modern_theme()
        
        # 创建现代化状态栏
        self._create_modern_status_bar()
        
        # 更新时间显示
        self._update_time()
        
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
        
        # 配置Notebook（主选项卡） - 大小始终保持一致
        self.ttk_style.configure(
            "TNotebook",
            background=Theme.BG_PRIMARY,
            borderwidth=0,
            relief="flat",
            tabmargins=[0, 0, 0, 0]  # 移除额外边距
        )
        self.ttk_style.configure(
            "TNotebook.Tab",
            background=Theme.BG_SECONDARY,
            foreground=Theme.TEXT_SECONDARY,
            padding=[32, 16],  # 固定padding
            borderwidth=0,
            focuscolor="none",
            lightcolor=Theme.BG_SECONDARY,
            darkcolor=Theme.BG_SECONDARY,
            bordercolor=Theme.BG_SECONDARY,
            font=(Theme.FONT_FAMILY, 13, "normal")
        )
        self.ttk_style.map(
            "TNotebook.Tab",
            background=[
                ("selected", Theme.SURFACE),
                ("active", Theme.BG_HOVER),
                ("!active", Theme.BG_SECONDARY)
            ],
            foreground=[
                ("selected", Theme.TEXT_PRIMARY),
                ("active", Theme.TEXT_PRIMARY),
                ("!active", Theme.TEXT_SECONDARY)
            ],
            # 确保所有状态的 padding 一致
            padding=[
                ("selected", [32, 16]),
                ("active", [32, 16]),
                ("!active", [32, 16])
            ]
        )
        
        # 配置Frame
        self.ttk_style.configure(
            "TFrame",
            background=Theme.BG_SECONDARY,
            borderwidth=0
        )
        
        # 配置LabelFrame - 卡片式设计
        self.ttk_style.configure(
            "TLabelframe",
            background=Theme.SURFACE,
            foreground=Theme.TEXT_PRIMARY,
            borderwidth=1,
            bordercolor=Theme.BORDER,
            relief="flat"
        )
        self.ttk_style.configure(
            "TLabelframe.Label",
            background=Theme.SURFACE,
            foreground=Theme.TEXT_PRIMARY,
            font=(Theme.FONT_FAMILY, Theme.FONT_SIZE_MEDIUM, "bold"),
            padding=[8, 4]
        )
        
        # 配置Button - 更大更舒适
        self.ttk_style.configure(
            "TButton",
            background=Theme.PRIMARY,
            foreground=Theme.TEXT_PRIMARY,
            borderwidth=0,
            relief="flat",
            padding=[24, 12],  # 增大按钮
            font=(Theme.FONT_FAMILY, 13, "normal")  # 增大字体
        )
        self.ttk_style.map(
            "TButton",
            background=[
                ("active", Theme.PRIMARY_LIGHT),
                ("pressed", Theme.PRIMARY_DARK),
                ("disabled", Theme.BG_TERTIARY)
            ],
            foreground=[
                ("active", Theme.TEXT_PRIMARY),
                ("disabled", Theme.TEXT_DISABLED)
            ]
        )
        
        # 配置Entry
        self.ttk_style.configure(
            "TEntry",
            fieldbackground=Theme.BG_TERTIARY,
            foreground=Theme.TEXT_PRIMARY,
            borderwidth=1,
            insertcolor=Theme.TEXT_PRIMARY
        )
        
        # 配置Combobox
        self.ttk_style.configure(
            "TCombobox",
            fieldbackground=Theme.BG_TERTIARY,
            background=Theme.BG_TERTIARY,
            foreground=Theme.TEXT_PRIMARY,
            borderwidth=1,
            arrowcolor=Theme.TEXT_SECONDARY
        )
    
    def _create_modern_header(self):
        """创建现代化顶部标题栏 - 专业设计"""
        # 主标题栏容器
        header = tk.Frame(self, bg=Theme.BG_PRIMARY, height=64)
        header.pack(fill="x", side="top")
        header.pack_propagate(False)
        
        # 左侧：Logo和标题
        left_frame = tk.Frame(header, bg=Theme.BG_PRIMARY)
        left_frame.pack(side="left", padx=24, pady=12)
        
        # 精致的应用图标
        icon_canvas = tk.Canvas(
            left_frame,
            width=40,
            height=40,
            bg=Theme.BG_PRIMARY,
            highlightthickness=0
        )
        icon_canvas.pack(side="left", padx=(0, 16))
        
        # 绘制带渐变效果的图标
        icon_canvas.create_oval(
            0, 0, 40, 40,
            fill=Theme.PRIMARY,
            outline="",
            width=0
        )
        # 内圈发光效果
        icon_canvas.create_oval(
            4, 4, 36, 36,
            fill="",
            outline=Theme.PRIMARY_LIGHT,
            width=2
        )
        # 图标
        icon_canvas.create_text(
            20, 20,
            text="✨",
            font=(Theme.FONT_FAMILY, 18),
            fill=Theme.TEXT_PRIMARY
        )
        
        # 标题区域
        title_frame = tk.Frame(left_frame, bg=Theme.BG_PRIMARY)
        title_frame.pack(side="left")
        
        # 主标题
        main_title = tk.Label(
            title_frame,
            text="AI Story Creator Pro",
            font=(Theme.FONT_FAMILY, 18, "bold"),
            bg=Theme.BG_PRIMARY,
            fg=Theme.TEXT_PRIMARY
        )
        main_title.pack(anchor="w")
        
        # 副标题
        subtitle = tk.Label(
            title_frame,
            text="智能创作平台",
            font=(Theme.FONT_FAMILY, 11),
            bg=Theme.BG_PRIMARY,
            fg=Theme.TEXT_HINT
        )
        subtitle.pack(anchor="w")
        
        # 右侧：状态提示和用户信息
        right_frame = tk.Frame(header, bg=Theme.BG_PRIMARY)
        right_frame.pack(side="right", padx=24, pady=12)
        
        # 创建一个容器来放置状态提示和用户信息
        right_container = tk.Frame(right_frame, bg=Theme.BG_PRIMARY)
        right_container.pack(side="left")
        
        # 状态提示区域（在用户卡片左边）
        status_card = tk.Frame(
            right_container,
            bg=Theme.SURFACE,
            relief="flat"
        )
        status_card.pack(side="left", padx=(0, 12))
        
        # 状态内容
        status_inner = tk.Frame(status_card, bg=Theme.SURFACE)
        status_inner.pack(padx=16, pady=8)
        
        # 状态图标（会根据状态动态更新）
        self.header_status_icon = tk.Label(
            status_inner,
            text="✅",
            font=(Theme.FONT_FAMILY, 14),
            bg=Theme.SURFACE,
            fg=Theme.TEXT_SECONDARY
        )
        self.header_status_icon.pack(side="left", padx=(0, 8))
        
        # 状态文本
        self.header_status_text = tk.Label(
            status_inner,
            text="就绪",
            font=(Theme.FONT_FAMILY, Theme.FONT_SIZE_NORMAL),
            bg=Theme.SURFACE,
            fg=Theme.TEXT_PRIMARY
        )
        self.header_status_text.pack(side="left")
        
        # 用户卡片（带微妙背景）
        user_card = tk.Frame(
            right_container,
            bg=Theme.SURFACE,
            relief="flat"
        )
        user_card.pack(side="left")
        
        # 内部内容
        user_inner = tk.Frame(user_card, bg=Theme.SURFACE)
        user_inner.pack(padx=16, pady=8)
        
        tk.Label(
            user_inner,
            text="👤",
            font=(Theme.FONT_FAMILY, 16),
            bg=Theme.SURFACE,
            fg=Theme.TEXT_SECONDARY
        ).pack(side="left", padx=(0, 10))
        
        tk.Label(
            user_inner,
            text="diming",
            font=(Theme.FONT_FAMILY, Theme.FONT_SIZE_NORMAL),
            bg=Theme.SURFACE,
            fg=Theme.TEXT_PRIMARY
        ).pack(side="left")
        
        # 微妙的分隔线（渐变效果）
        separator = tk.Frame(self, bg=Theme.DIVIDER, height=1)
        separator.pack(fill="x")
    
    def _apply_modern_theme(self):
        """将现代化主题应用到已创建的组件"""
        # 应用到主notebook
        if hasattr(self, 'notebook'):
            self.notebook.configure(style="TNotebook")
            # 添加边距，让选项卡更有呼吸感
            self.notebook.pack_configure(padx=0, pady=0)
            
            # 更新页面背景 - 使用更深的背景色
            for page in [self.page_project, self.page_story, self.page_image]:
                page.configure(bg=Theme.BG_CARD)
                self._apply_theme_to_children(page)
        
        # 优化内部notebook（story_notebook等）
        if hasattr(self, 'story_notebook'):
            self.story_notebook.configure(style="TNotebook")
    
    def _apply_theme_to_children(self, widget):
        """递归应用主题到所有子组件"""
        try:
            # 跳过某些特殊组件
            widget_class = widget.winfo_class()
            
            # 跳过 Combobox、Spinbox 等复杂的 ttk 组件
            if widget_class in ["TCombobox", "TSpinbox", "TNotebook", "TButton", "TEntry", "TFrame", "TLabelframe"]:
                # TTK组件已经通过样式配置，跳过
                for child in widget.winfo_children():
                    self._apply_theme_to_children(child)
                return
            
            # 只处理基本的 tk 组件
            if widget_class == "Frame":
                widget.configure(bg=Theme.BG_SECONDARY)
            elif widget_class == "Label":
                # 检查是否有特殊样式，避免覆盖
                current_bg = widget.cget("bg")
                if current_bg in ["#2b2b2b", "#1e1e1e", "SystemButtonFace", ""]:
                    widget.configure(bg=Theme.BG_SECONDARY)
            elif widget_class == "Text":
                # 保持原有的Text配置
                pass
            elif widget_class == "Entry":
                # 保持原有的Entry配置
                pass
            
            # 递归处理子组件
            for child in widget.winfo_children():
                self._apply_theme_to_children(child)
        except Exception as e:
            # 忽略无法配置的组件，避免崩溃
            pass
    
    def _create_modern_status_bar(self):
        """创建现代化底部状态栏 - 专业设计"""
        # 微妙的分隔线
        tk.Frame(self, bg=Theme.DIVIDER, height=1).pack(fill="x", side="bottom")
        
        # 状态栏容器
        status_bar = tk.Frame(self, bg=Theme.BG_PRIMARY, height=32)
        status_bar.pack(fill="x", side="bottom")
        status_bar.pack_propagate(False)
        
        # 左侧：状态区域（带背景卡片）
        left_frame = tk.Frame(status_bar, bg=Theme.BG_PRIMARY)
        left_frame.pack(side="left", fill="y", padx=20, pady=6)
        
        # 状态指示器 - 更精致
        self.status_indicator = tk.Canvas(
            left_frame,
            width=8,
            height=8,
            bg=Theme.BG_PRIMARY,
            highlightthickness=0
        )
        self.status_indicator.pack(side="left", padx=(0, 12))
        self.status_indicator.create_oval(0, 0, 8, 8, fill=Theme.SUCCESS, outline="")
        
        # 状态文本
        if not hasattr(self, 'status'):
            self.status = tk.StringVar(value="系统就绪")
        
        self.status_label = tk.Label(
            left_frame,
            textvariable=self.status,
            font=(Theme.FONT_FAMILY, 11),
            bg=Theme.BG_PRIMARY,
            fg=Theme.TEXT_SECONDARY
        )
        self.status_label.pack(side="left")
        
        # 右侧：信息区域
        right_frame = tk.Frame(status_bar, bg=Theme.BG_PRIMARY)
        right_frame.pack(side="right", fill="y", padx=20, pady=6)
        
        # 版本标签 - 带图标
        version_container = tk.Frame(right_frame, bg=Theme.BG_PRIMARY)
        version_container.pack(side="right")
        
        tk.Label(
            version_container,
            text="🎯",
            font=(Theme.FONT_FAMILY, 10),
            bg=Theme.BG_PRIMARY,
            fg=Theme.TEXT_DISABLED
        ).pack(side="left", padx=(10, 4))
        
        tk.Label(
            version_container,
            text="v2.0.0",
            font=(Theme.FONT_FAMILY, 10),
            bg=Theme.BG_PRIMARY,
            fg=Theme.TEXT_DISABLED
        ).pack(side="left")
        
        # 微妙的分隔符
        tk.Label(
            right_frame,
            text="•",
            font=(Theme.FONT_FAMILY, 10),
            bg=Theme.BG_PRIMARY,
            fg=Theme.BORDER
        ).pack(side="right", padx=8)
        
        # 时间显示 - 带图标
        time_container = tk.Frame(right_frame, bg=Theme.BG_PRIMARY)
        time_container.pack(side="right")
        
        tk.Label(
            time_container,
            text="🕐",
            font=(Theme.FONT_FAMILY, 10),
            bg=Theme.BG_PRIMARY,
            fg=Theme.TEXT_DISABLED
        ).pack(side="left", padx=(0, 6))
        
        self.time_label = tk.Label(
            time_container,
            text="",
            font=(Theme.FONT_FAMILY, 11),
            bg=Theme.BG_PRIMARY,
            fg=Theme.TEXT_SECONDARY
        )
        self.time_label.pack(side="left")
    
    def _update_time(self):
        """更新时间显示"""
        try:
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            if hasattr(self, 'time_label'):
                self.time_label.config(text=now)
            self.after(1000, self._update_time)
        except:
            pass
    
    def update_header_status(self, text: str, icon: str = "🔄", color: str = None):
        """
        更新顶部状态栏的显示
        
        参数:
            text: 要显示的状态文本
            icon: 状态图标，默认为🔄（处理中）
            color: 文本颜色（可选），如果不指定则使用默认颜色
        
        常用图标:
            🔄 - 处理中
            ✅ - 完成/就绪
            ⏳ - 等待中
            📝 - 生成中
            🎨 - 图片生成中
            ❌ - 错误
            ⚠️ - 警告
        """
        try:
            if hasattr(self, 'header_status_icon') and hasattr(self, 'header_status_text'):
                self.header_status_icon.config(text=icon)
                self.header_status_text.config(text=text)
                if color:
                    self.header_status_text.config(fg=color)
                else:
                    # 根据图标自动选择颜色
                    if icon == "✅":
                        self.header_status_text.config(fg=Theme.TEXT_PRIMARY)
                    elif icon == "❌":
                        self.header_status_text.config(fg="#ef5350")  # 红色
                    elif icon == "⚠️":
                        self.header_status_text.config(fg="#ffa726")  # 橙色
                    elif icon in ["🔄", "📝", "🎨", "⏳"]:
                        self.header_status_text.config(fg="#42a5f5")  # 蓝色（进行中）
                    else:
                        self.header_status_text.config(fg=Theme.TEXT_PRIMARY)
                # 强制刷新UI
                self.update_idletasks()
        except Exception as e:
            print(f"更新状态栏失败: {e}")

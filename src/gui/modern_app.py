"""
现代化UI主窗口 - 使用原有Mixin功能，应用现代化主题
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


class ModernApp(tk.Tk, ProjectMixin, StoryMixin, ImageMixin, KbMixin, ConfigMixin, UiMixin):
    """现代化专业UI应用 - 整合所有原有功能"""
    
    def __init__(self):
        super().__init__()
        
        # 窗口配置 - 简约专业
        self.title("AI Story Creator Pro")
        
        # 使用舒适的尺寸：1500x850 (更精致的比例)
        window_width = 1500
        window_height = 850
        
        # 窗口居中显示
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        x = (screen_width - window_width) // 2
        y = (screen_height - window_height) // 2
        
        self.geometry(f"{window_width}x{window_height}+{x}+{y}")
        self.minsize(1200, 700)  # 最小尺寸
        
        # 设置窗口背景色
        self.configure(bg=Theme.BG_PRIMARY)
        
        # 加载环境变量
        from dotenv import load_dotenv
        load_dotenv()
        
        # 初始化所有必需的变量（原有功能需要）
        self._init_variables()
        
        # 统一Tk基础组件的暗色默认配色
        self._setup_tk_defaults()
        
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
        """设置现代化ttk组件样式 - 极致美学"""
        self.ttk_style = ttk.Style()
        self.ttk_style.theme_use('clam')
        
        # 配置Notebook（主选项卡） - 精致的标签页设计
        self.ttk_style.configure(
            "TNotebook",
            background=Theme.BG_PRIMARY,
            borderwidth=0,
            relief="flat",
            tabmargins=[0, 0, 0, 0]
        )
        self.ttk_style.configure(
            "TNotebook.Tab",
            background=Theme.BG_PRIMARY,
            foreground=Theme.TEXT_SECONDARY,
            padding=[16, 8],  # 更紧凑的padding
            borderwidth=0,
            focuscolor="none",
            lightcolor=Theme.BG_PRIMARY,
            darkcolor=Theme.BG_PRIMARY,
            bordercolor=Theme.BG_PRIMARY,
            font=(Theme.FONT_FAMILY, 11, "normal")  # 更小的字体
        )
        self.ttk_style.map(
            "TNotebook.Tab",
            background=[
                ("selected", Theme.BG_SECONDARY),
                ("active", Theme.BG_HOVER),
                ("!active", Theme.BG_PRIMARY)
            ],
            foreground=[
                ("selected", Theme.TEXT_PRIMARY),  # 选中时使用主文本色
                ("active", Theme.TEXT_PRIMARY),
                ("!active", Theme.TEXT_SECONDARY)
            ],
            padding=[
                ("selected", [16, 8]),
                ("active", [16, 8]),
                ("!active", [16, 8])
            ]
        )
        
        # 配置Frame - 更精致的背景
        self.ttk_style.configure(
            "TFrame",
            background=Theme.BG_CARD,
            borderwidth=0
        )
        
        # 配置LabelFrame - 精致卡片设计
        self.ttk_style.configure(
            "TLabelframe",
            background=Theme.BG_CARD,
            foreground=Theme.TEXT_PRIMARY,
            borderwidth=0,
            relief="flat"
        )
        self.ttk_style.configure(
            "TLabelframe.Label",
            background=Theme.BG_CARD,
            foreground=Theme.TEXT_PRIMARY,
            font=(Theme.FONT_FAMILY, 12, "normal"),  # 更小的字体
            padding=[12, 6]  # 更紧凑的padding
        )
        
        # 配置Button - 更合理的紧凑中性色（默认）
        self.ttk_style.configure(
            "TButton",
            background=Theme.SURFACE_LIGHT,
            foreground=Theme.TEXT_PRIMARY,
            borderwidth=1,
            relief="flat",
            padding=[10, 6],
            font=(Theme.FONT_FAMILY, 11, "normal")
        )
        self.ttk_style.map(
            "TButton",
            background=[
                ("active", Theme.BG_HOVER),
                ("pressed", Theme.BG_TERTIARY),
                ("disabled", Theme.BG_TERTIARY)
            ],
            foreground=[
                ("disabled", Theme.TEXT_DISABLED)
            ]
        )

        # 强调按钮（主操作）
        self.ttk_style.configure(
            "Accent.TButton",
            background=Theme.PRIMARY,
            foreground="#FFFFFF",
            borderwidth=0,
            relief="flat",
            padding=[12, 6],
            font=(Theme.FONT_FAMILY, 11, "normal")
        )
        self.ttk_style.map(
            "Accent.TButton",
            background=[
                ("active", Theme.PRIMARY_LIGHT),
                ("pressed", Theme.PRIMARY_DARK),
                ("disabled", Theme.BG_TERTIARY)
            ],
            foreground=[
                ("disabled", Theme.TEXT_DISABLED)
            ]
        )

        # 幽灵按钮（最小视觉重量）
        self.ttk_style.configure(
            "Ghost.TButton",
            background=Theme.BG_PRIMARY,
            foreground=Theme.TEXT_SECONDARY,
            borderwidth=0,
            relief="flat",
            padding=[8, 4],
            font=(Theme.FONT_FAMILY, 11, "normal")
        )
        self.ttk_style.map(
            "Ghost.TButton",
            background=[
                ("active", Theme.BG_HOVER),
                ("pressed", Theme.BG_TERTIARY)
            ],
            foreground=[
                ("active", Theme.TEXT_PRIMARY)
            ]
        )
        
        # 配置Entry - 精致输入框
        self.ttk_style.configure(
            "TEntry",
            fieldbackground=Theme.SURFACE,
            foreground=Theme.TEXT_PRIMARY,
            borderwidth=1,  # 更细的边框
            bordercolor=Theme.BORDER,
            insertcolor=Theme.PRIMARY,
            padding=[8, 4]  # 更紧凑的padding
        )
        self.ttk_style.map(
            "TEntry",
            fieldbackground=[("focus", Theme.SURFACE_DARK)],
            bordercolor=[("focus", Theme.BORDER_FOCUS)]
        )
        
        # 配置Combobox - 精致下拉框
        self.ttk_style.configure(
            "TCombobox",
            fieldbackground=Theme.SURFACE,
            background=Theme.SURFACE,
            foreground=Theme.TEXT_PRIMARY,
            borderwidth=1,  # 更细的边框
            bordercolor=Theme.BORDER,
            arrowcolor=Theme.TEXT_ACCENT,
            padding=[8, 4]  # 更紧凑的padding
        )
        self.ttk_style.map(
            "TCombobox",
            fieldbackground=[("focus", Theme.SURFACE_DARK)],
            bordercolor=[("focus", Theme.BORDER_FOCUS)],
            arrowcolor=[("focus", Theme.PRIMARY_LIGHT)]
        )
        
        # 配置Treeview - 深色风格
        self.ttk_style.configure(
            "Treeview",
            background=Theme.BG_TERTIARY,
            fieldbackground=Theme.BG_TERTIARY,
            foreground=Theme.TEXT_PRIMARY,
            borderwidth=0
        )
        self.ttk_style.map(
            "Treeview",
            background=[("selected", Theme.PRIMARY)],
            foreground=[("selected", Theme.TEXT_ON_PRIMARY)]
        )
        self.ttk_style.configure(
            "Treeview.Heading",
            background=Theme.BG_PRIMARY,
            foreground=Theme.TEXT_SECONDARY,
            relief="flat"
        )
        self.ttk_style.map(
            "Treeview.Heading",
            background=[("active", Theme.BG_HOVER)],
            foreground=[("active", Theme.TEXT_PRIMARY)]
        )
        
        # 配置Scrollbar - 深色风格（ttk）
        self.ttk_style.configure(
            "TScrollbar",
            background=Theme.BG_TERTIARY,
            troughcolor=Theme.BG_SECONDARY,
            bordercolor=Theme.BORDER,
            arrowcolor=Theme.TEXT_SECONDARY
        )
    
    def _create_modern_header(self):
        """创建简约顶部栏 - PyCharm风格"""
        # 主标题栏容器 - 简约高度
        header = tk.Frame(self, bg=Theme.BG_PRIMARY, height=48)
        header.pack(fill="x", side="top")
        header.pack_propagate(False)
        
        # 左侧：简约标题
        left_frame = tk.Frame(header, bg=Theme.BG_PRIMARY)
        left_frame.pack(side="left", padx=20, pady=12)
        
        # 简约标题 - 无图标
        main_title = tk.Label(
            left_frame,
            text="AI Story Creator Pro",
            font=(Theme.FONT_FAMILY, 12, "normal"),  # 更小的字体
            bg=Theme.BG_PRIMARY,
            fg=Theme.TEXT_PRIMARY
        )
        main_title.pack(anchor="w")
        
        # 右侧：简约状态指示
        right_frame = tk.Frame(header, bg=Theme.BG_PRIMARY)
        right_frame.pack(side="right", padx=20, pady=12)
        
        # 简约状态文本
        self.header_status_text = tk.Label(
            right_frame,
            text="就绪",
            font=(Theme.FONT_FAMILY, 11),
            bg=Theme.BG_PRIMARY,
            fg=Theme.TEXT_SECONDARY
        )
        self.header_status_text.pack(side="left")
        
        # 简约分隔线
        separator = tk.Frame(self, bg=Theme.BORDER, height=1)
        separator.pack(fill="x")
    
    def _apply_modern_theme(self):
        """将现代化主题应用到已创建的组件 - 和谐美学"""
        # 应用到主notebook
        if hasattr(self, 'notebook'):
            self.notebook.configure(style="TNotebook")
            # 紧凑边距 - PyCharm风格
            self.notebook.pack_configure(padx=12, pady=(8, 12))
            
            # 更新页面背景 - 使用和谐的背景色
            for page in [self.page_project, self.page_story, self.page_image]:
                page.configure(bg=Theme.BG_SECONDARY)
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
                widget.configure(
                    bg=Theme.SURFACE,
                    fg=Theme.TEXT_PRIMARY,
                    insertbackground=Theme.PRIMARY,
                    selectbackground=Theme.PRIMARY,
                    selectforeground=Theme.TEXT_ON_PRIMARY
                )
            elif widget_class == "Entry":
                widget.configure(
                    bg=Theme.SURFACE,
                    fg=Theme.TEXT_PRIMARY,
                    insertbackground=Theme.PRIMARY
                )
            elif widget_class == "Canvas":
                widget.configure(bg=Theme.BG_SECONDARY)
            
            # 递归处理子组件
            for child in widget.winfo_children():
                self._apply_theme_to_children(child)
        except Exception as e:
            # 忽略无法配置的组件，避免崩溃
            pass

    def _setup_tk_defaults(self):
        """统一Tk经典组件的暗色默认外观，避免白色背景块"""
        try:
            # 全局默认
            self.option_add("*Background", Theme.BG_SECONDARY)
            self.option_add("*Foreground", Theme.TEXT_PRIMARY)
            self.option_add("*selectBackground", Theme.PRIMARY)
            self.option_add("*selectForeground", Theme.TEXT_ON_PRIMARY)
            
            # 经典组件专属
            self.option_add("*Entry.Background", Theme.SURFACE)
            self.option_add("*Entry.Foreground", Theme.TEXT_PRIMARY)
            self.option_add("*Text.Background", Theme.SURFACE)
            self.option_add("*Text.Foreground", Theme.TEXT_PRIMARY)
            self.option_add("*Listbox.Background", Theme.BG_TERTIARY)
            self.option_add("*Listbox.Foreground", Theme.TEXT_PRIMARY)
        except Exception:
            pass
    
    def _create_modern_status_bar(self):
        """创建简约底部状态栏 - PyCharm风格"""
        # 简约分隔线
        tk.Frame(self, bg=Theme.BORDER, height=1).pack(fill="x", side="bottom")
        
        # 状态栏容器 - 紧凑
        status_bar = tk.Frame(self, bg=Theme.BG_PRIMARY, height=28)
        status_bar.pack(fill="x", side="bottom")
        status_bar.pack_propagate(False)
        
        # 左侧：状态文本
        left_frame = tk.Frame(status_bar, bg=Theme.BG_PRIMARY)
        left_frame.pack(side="left", fill="y", padx=12, pady=6)
        
        # 状态文本 - 简约
        if not hasattr(self, 'status'):
            self.status = tk.StringVar(value="就绪")
        
        self.status_label = tk.Label(
            left_frame,
            textvariable=self.status,
            font=(Theme.FONT_FAMILY, 10),
            bg=Theme.BG_PRIMARY,
            fg=Theme.TEXT_SECONDARY
        )
        self.status_label.pack(side="left")
        
        # 右侧：版本信息
        right_frame = tk.Frame(status_bar, bg=Theme.BG_PRIMARY)
        right_frame.pack(side="right", fill="y", padx=12, pady=6)
        
        # 时间显示
        self.time_label = tk.Label(
            right_frame,
            text="",
            font=(Theme.FONT_FAMILY, 10),
            bg=Theme.BG_PRIMARY,
            fg=Theme.TEXT_HINT
        )
        self.time_label.pack(side="right", padx=(12, 0))
        
        # 分隔符
        tk.Label(
            right_frame,
            text="|",
            font=(Theme.FONT_FAMILY, 10),
            bg=Theme.BG_PRIMARY,
            fg=Theme.BORDER_LIGHT
        ).pack(side="right", padx=8)
        
        # 版本
        tk.Label(
            right_frame,
            text="v2.0",
            font=(Theme.FONT_FAMILY, 10),
            bg=Theme.BG_PRIMARY,
            fg=Theme.TEXT_HINT
        ).pack(side="right")
    
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

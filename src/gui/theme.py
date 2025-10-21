"""
专业UI主题配置
"""

class Theme:
    """现代化深色主题配置 - 专业设计系统"""
    
    # 主色调 - 精致渐变蓝紫色系
    PRIMARY = "#6366F1"  # 主色 - Indigo-500
    PRIMARY_DARK = "#4F46E5"  # Indigo-600
    PRIMARY_LIGHT = "#818CF8"  # Indigo-400
    PRIMARY_GLOW = "rgba(99, 102, 241, 0.5)"  # 发光效果
    
    # 强调色 - 现代渐变
    ACCENT = "#06B6D4"  # Cyan-500
    ACCENT_DARK = "#0891B2"  # Cyan-600
    ACCENT_LIGHT = "#22D3EE"  # Cyan-400
    
    # 状态色 - 精致配色
    SUCCESS = "#10B981"  # Emerald-500
    WARNING = "#F59E0B"  # Amber-500
    ERROR = "#EF4444"  # Red-500
    INFO = "#3B82F6"  # Blue-500
    
    # 背景色 - 精致层次
    BG_PRIMARY = "#0A0B0F"  # 主背景 - 更深
    BG_SECONDARY = "#13141B"  # 次要背景
    BG_TERTIARY = "#1C1D26"  # 第三背景
    BG_HOVER = "#252631"  # 悬停背景
    BG_SELECTED = "#2D2E3D"  # 选中背景
    BG_CARD = "#16171F"  # 卡片背景
    
    # 表面色 - 玻璃态效果
    SURFACE = "#18191F"  # 表面色
    SURFACE_LIGHT = "#22232B"  # 浅表面
    SURFACE_DARK = "#0E0F14"  # 深表面
    SURFACE_GLASS = "rgba(30, 31, 40, 0.8)"  # 玻璃态
    
    # 文本色 - 精致对比
    TEXT_PRIMARY = "#F1F3F9"  # 主文本
    TEXT_SECONDARY = "#9CA3AF"  # 次要文本 - Gray-400
    TEXT_DISABLED = "#4B5563"  # 禁用文本 - Gray-600
    TEXT_HINT = "#6B7280"  # 提示文本 - Gray-500
    TEXT_ACCENT = "#A78BFA"  # 强调文本 - Purple-400
    TEXT_ON_PRIMARY = "#FFFFFF"  # 主色上的文本
    
    # 边框色
    BORDER = "#282A36"  # 边框色
    BORDER_LIGHT = "#32343E"  # 浅边框
    BORDER_FOCUS = "#6366F1"  # 焦点边框
    BORDER_SUBTLE = "#1F2028"  # 微妙边框
    
    # 分隔线
    DIVIDER = "#1E1F29"
    DIVIDER_LIGHT = "#252631"
    
    # 字体配置
    FONT_FAMILY = "SF Pro Display, PingFang SC, Microsoft YaHei, Segoe UI, Arial"
    FONT_FAMILY_MONO = "SF Mono, Monaco, Consolas, Courier New"
    
    # 字体大小
    FONT_SIZE_TINY = 10
    FONT_SIZE_SMALL = 11
    FONT_SIZE_NORMAL = 12
    FONT_SIZE_MEDIUM = 14
    FONT_SIZE_LARGE = 16
    FONT_SIZE_XLARGE = 18
    FONT_SIZE_TITLE = 20
    FONT_SIZE_HEADER = 24
    
    # 间距
    PADDING_TINY = 4
    PADDING_SMALL = 8
    PADDING_NORMAL = 12
    PADDING_MEDIUM = 16
    PADDING_LARGE = 20
    PADDING_XLARGE = 24
    
    # 圆角
    RADIUS_SMALL = 4
    RADIUS_NORMAL = 6
    RADIUS_LARGE = 8
    RADIUS_XLARGE = 12
    
    # 阴影
    SHADOW_SMALL = "0 2px 4px rgba(0,0,0,0.2)"
    SHADOW_NORMAL = "0 4px 8px rgba(0,0,0,0.3)"
    SHADOW_LARGE = "0 8px 16px rgba(0,0,0,0.4)"
    
    # 动画时长（毫秒）
    ANIMATION_FAST = 150
    ANIMATION_NORMAL = 300
    ANIMATION_SLOW = 500


class Styles:
    """组件样式定义"""
    
    @staticmethod
    def get_button_style(variant="primary"):
        """获取按钮样式 - 现代设计"""
        if variant == "primary":
            return {
                "font": (Theme.FONT_FAMILY, Theme.FONT_SIZE_NORMAL, "600"),
                "bg": Theme.PRIMARY,
                "fg": Theme.TEXT_PRIMARY,
                "activebackground": Theme.PRIMARY_LIGHT,
                "activeforeground": Theme.TEXT_PRIMARY,
                "relief": "flat",
                "bd": 0,
                "padx": 20,
                "pady": 10,
                "cursor": "hand2",
                "highlightthickness": 0,
                "borderwidth": 0
            }
        elif variant == "secondary":
            return {
                "font": (Theme.FONT_FAMILY, Theme.FONT_SIZE_NORMAL, "normal"),
                "bg": Theme.SURFACE_LIGHT,
                "fg": Theme.TEXT_PRIMARY,
                "activebackground": Theme.BG_HOVER,
                "activeforeground": Theme.TEXT_PRIMARY,
                "relief": "flat",
                "bd": 0,
                "padx": 18,
                "pady": 9,
                "cursor": "hand2",
                "highlightthickness": 1,
                "highlightbackground": Theme.BORDER,
                "highlightcolor": Theme.BORDER_FOCUS,
                "borderwidth": 0
            }
        elif variant == "danger":
            return {
                "font": (Theme.FONT_FAMILY, Theme.FONT_SIZE_NORMAL, "600"),
                "bg": Theme.ERROR,
                "fg": Theme.TEXT_PRIMARY,
                "activebackground": "#DC2626",
                "activeforeground": Theme.TEXT_PRIMARY,
                "relief": "flat",
                "bd": 0,
                "padx": 18,
                "pady": 9,
                "cursor": "hand2",
                "highlightthickness": 0,
                "borderwidth": 0
            }
        elif variant == "success":
            return {
                "font": (Theme.FONT_FAMILY, Theme.FONT_SIZE_NORMAL, "600"),
                "bg": Theme.SUCCESS,
                "fg": Theme.TEXT_PRIMARY,
                "activebackground": "#059669",
                "activeforeground": Theme.TEXT_PRIMARY,
                "relief": "flat",
                "bd": 0,
                "padx": 18,
                "pady": 9,
                "cursor": "hand2",
                "highlightthickness": 0,
                "borderwidth": 0
            }
        elif variant == "ghost":
            return {
                "font": (Theme.FONT_FAMILY, Theme.FONT_SIZE_NORMAL, "normal"),
                "bg": "transparent",
                "fg": Theme.TEXT_SECONDARY,
                "activebackground": Theme.BG_HOVER,
                "activeforeground": Theme.TEXT_PRIMARY,
                "relief": "flat",
                "bd": 0,
                "padx": 16,
                "pady": 8,
                "cursor": "hand2",
                "highlightthickness": 0,
                "borderwidth": 0
            }
        else:
            return {}
    
    @staticmethod
    def get_entry_style():
        """获取输入框样式 - 现代设计"""
        return {
            "font": (Theme.FONT_FAMILY, Theme.FONT_SIZE_NORMAL),
            "bg": Theme.SURFACE,
            "fg": Theme.TEXT_PRIMARY,
            "insertbackground": Theme.PRIMARY,
            "selectbackground": Theme.PRIMARY,
            "selectforeground": Theme.TEXT_PRIMARY,
            "relief": "flat",
            "bd": 0,
            "highlightthickness": 2,
            "highlightbackground": Theme.BORDER_SUBTLE,
            "highlightcolor": Theme.BORDER_FOCUS
        }
    
    @staticmethod
    def get_text_style():
        """获取文本框样式 - 现代设计"""
        return {
            "font": (Theme.FONT_FAMILY, Theme.FONT_SIZE_NORMAL),
            "bg": Theme.SURFACE,
            "fg": Theme.TEXT_PRIMARY,
            "insertbackground": Theme.PRIMARY,
            "selectbackground": Theme.PRIMARY,
            "selectforeground": Theme.TEXT_PRIMARY,
            "relief": "flat",
            "bd": 0,
            "highlightthickness": 2,
            "highlightbackground": Theme.BORDER_SUBTLE,
            "highlightcolor": Theme.BORDER_FOCUS,
            "wrap": "word",
            "padx": 12,
            "pady": 12,
            "spacing1": 2,
            "spacing3": 2
        }
    
    @staticmethod
    def get_label_style(variant="normal"):
        """获取标签样式"""
        if variant == "normal":
            return {
                "font": (Theme.FONT_FAMILY, Theme.FONT_SIZE_NORMAL),
                "bg": Theme.BG_SECONDARY,
                "fg": Theme.TEXT_PRIMARY
            }
        elif variant == "secondary":
            return {
                "font": (Theme.FONT_FAMILY, Theme.FONT_SIZE_NORMAL),
                "bg": Theme.BG_SECONDARY,
                "fg": Theme.TEXT_SECONDARY
            }
        elif variant == "title":
            return {
                "font": (Theme.FONT_FAMILY, Theme.FONT_SIZE_TITLE, "bold"),
                "bg": Theme.BG_SECONDARY,
                "fg": Theme.TEXT_PRIMARY
            }
        elif variant == "header":
            return {
                "font": (Theme.FONT_FAMILY, Theme.FONT_SIZE_HEADER, "bold"),
                "bg": Theme.BG_PRIMARY,
                "fg": Theme.TEXT_PRIMARY
            }
        else:
            return {}
    
    @staticmethod
    def get_frame_style(variant="normal"):
        """获取框架样式"""
        if variant == "normal":
            return {
                "bg": Theme.BG_SECONDARY,
                "relief": "flat",
                "bd": 0
            }
        elif variant == "card":
            return {
                "bg": Theme.SURFACE,
                "relief": "flat",
                "bd": 1,
                "highlightthickness": 1,
                "highlightbackground": Theme.BORDER
            }
        elif variant == "panel":
            return {
                "bg": Theme.BG_TERTIARY,
                "relief": "flat",
                "bd": 0
            }
        else:
            return {}
    
    @staticmethod
    def get_listbox_style():
        """获取列表框样式"""
        return {
            "font": (Theme.FONT_FAMILY, Theme.FONT_SIZE_NORMAL),
            "bg": Theme.BG_TERTIARY,
            "fg": Theme.TEXT_PRIMARY,
            "selectbackground": Theme.PRIMARY,
            "selectforeground": Theme.TEXT_PRIMARY,
            "activestyle": "none",
            "relief": "flat",
            "bd": 0,
            "highlightthickness": 0
        }
    
    @staticmethod
    def get_scrollbar_style():
        """获取滚动条样式"""
        return {
            "bg": Theme.BG_TERTIARY,
            "troughcolor": Theme.BG_SECONDARY,
            "activebackground": Theme.PRIMARY,
            "relief": "flat",
            "bd": 0,
            "width": 12
        }
    
    @staticmethod
    def get_menu_style():
        """获取菜单样式"""
        return {
            "bg": Theme.SURFACE,
            "fg": Theme.TEXT_PRIMARY,
            "activebackground": Theme.PRIMARY,
            "activeforeground": Theme.TEXT_PRIMARY,
            "selectcolor": Theme.PRIMARY,
            "relief": "flat",
            "bd": 0,
            "font": (Theme.FONT_FAMILY, Theme.FONT_SIZE_NORMAL),
            "tearoff": 0
        }
    
    @staticmethod
    def get_notebook_style():
        """获取选项卡样式"""
        return {
            "bg": Theme.BG_SECONDARY,
            "fg": Theme.TEXT_PRIMARY,
            "relief": "flat",
            "bd": 0
        }


class Icons:
    """图标定义（使用Unicode字符）"""
    
    # 文件操作
    FILE = "📄"
    FOLDER = "📁"
    SAVE = "💾"
    OPEN = "📂"
    DELETE = "🗑️"
    
    # 编辑操作
    EDIT = "✏️"
    COPY = "📋"
    CUT = "✂️"
    PASTE = "📌"
    UNDO = "↩️"
    REDO = "↪️"
    
    # 媒体控制
    PLAY = "▶️"
    PAUSE = "⏸️"
    STOP = "⏹️"
    RECORD = "⏺️"
    
    # 导航
    HOME = "🏠"
    BACK = "⬅️"
    FORWARD = "➡️"
    UP = "⬆️"
    DOWN = "⬇️"
    
    # 状态
    SUCCESS = "✅"
    ERROR = "❌"
    WARNING = "⚠️"
    INFO = "ℹ️"
    QUESTION = "❓"
    
    # 功能
    SETTINGS = "⚙️"
    SEARCH = "🔍"
    FILTER = "🔽"
    SORT = "↕️"
    REFRESH = "🔄"
    
    # AI相关
    AI = "🤖"
    MAGIC = "✨"
    BRAIN = "🧠"
    SPARKLES = "✨"
    
    # 创作相关
    WRITE = "✍️"
    IMAGE = "🖼️"
    CAMERA = "📷"
    PALETTE = "🎨"
    BOOK = "📖"
    
    # 项目管理
    PROJECT = "📂"
    TASK = "📋"
    CALENDAR = "📅"
    CLOCK = "🕐"
    
    # 其他
    STAR = "⭐"
    HEART = "❤️"
    FIRE = "🔥"
    LIGHTNING = "⚡"
    CLOUD = "☁️"
    SUN = "☀️"
    MOON = "🌙"

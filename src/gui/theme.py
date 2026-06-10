"""
专业UI主题配置 - 支持深色/浅色主题切换
"""
import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

class ThemeColors:
    """主题颜色基类"""
    pass


class DarkTheme(ThemeColors):
    """深色主题"""
    NAME = "dark"
    
    # 主色调
    PRIMARY = "#4BA3A6"
    PRIMARY_DARK = "#2F7E7F"
    PRIMARY_LIGHT = "#6FC1C2"
    PRIMARY_GLOW = "rgba(75, 163, 166, 0.4)"
    
    # 强调色
    ACCENT = "#E09F3E"
    ACCENT_DARK = "#C47A2B"
    ACCENT_LIGHT = "#F2B65E"
    
    # 状态色
    SUCCESS = "#3BB273"
    WARNING = "#E09F3E"
    ERROR = "#E05858"
    INFO = "#4BA3A6"
    
    # 背景色
    BG_PRIMARY = "#0E1318"
    BG_SECONDARY = "#141B22"
    BG_TERTIARY = "#1B2430"
    BG_HOVER = "#232E3B"
    BG_SELECTED = "#2C3A49"
    BG_CARD = "#131A20"
    
    # 表面色
    SURFACE = "#171F26"
    SURFACE_LIGHT = "#1F2833"
    SURFACE_DARK = "#10161C"
    SURFACE_GLASS = "rgba(23, 31, 38, 0.85)"
    
    # 文本色
    TEXT_PRIMARY = "#E6EDF3"
    TEXT_SECONDARY = "#9AA7B4"
    TEXT_DISABLED = "#5B6B7A"
    TEXT_HINT = "#7E8B97"
    
    # 边框色
    BORDER = "#253241"
    BORDER_LIGHT = "#2E3B4A"
    BORDER_FOCUS = "#4BA3A6"
    BORDER_SUBTLE = "#1C2630"
    
    # 分隔线
    DIVIDER = "#1E2A37"
    DIVIDER_LIGHT = "#243140"
    
    # 字体配置（静态）
    FONT_FAMILY = "Microsoft YaHei UI"
    FONT_FAMILY_MONO = "Consolas"
    
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


class LightTheme(ThemeColors):
    """浅色主题"""
    NAME = "light"
    
    # 主色调
    PRIMARY = "#2F7E7F"
    PRIMARY_DARK = "#246566"
    PRIMARY_LIGHT = "#4BA3A6"
    PRIMARY_GLOW = "rgba(47, 126, 127, 0.25)"
    
    # 强调色
    ACCENT = "#C7762F"
    ACCENT_DARK = "#A85F24"
    ACCENT_LIGHT = "#E09F3E"
    
    # 状态色
    SUCCESS = "#2F855A"
    WARNING = "#C7762F"
    ERROR = "#C53030"
    INFO = "#2F7E7F"
    
    # 背景色
    BG_PRIMARY = "#F8FAFC"
    BG_SECONDARY = "#F1F5F9"
    BG_TERTIARY = "#E2E8F0"
    BG_HOVER = "#CBD5E1"
    BG_SELECTED = "#D9EDEA"
    BG_CARD = "#FFFFFF"
    
    # 表面色
    SURFACE = "#FFFFFF"
    SURFACE_LIGHT = "#F8FAFC"
    SURFACE_DARK = "#E2E8F0"
    SURFACE_GLASS = "rgba(255, 255, 255, 0.9)"
    
    # 文本色
    TEXT_PRIMARY = "#0F172A"
    TEXT_SECONDARY = "#475569"
    TEXT_DISABLED = "#94A3B8"
    TEXT_HINT = "#64748B"
    
    # 边框色
    BORDER = "#CBD5E1"
    BORDER_LIGHT = "#E2E8F0"
    BORDER_FOCUS = "#2F7E7F"
    BORDER_SUBTLE = "#E2E8F0"
    
    # 分隔线
    DIVIDER = "#E2E8F0"
    DIVIDER_LIGHT = "#F1F5F9"

    # 字体配置（与深色主题保持一致）
    FONT_FAMILY = "Microsoft YaHei UI"
    FONT_FAMILY_MONO = "Consolas"

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
    SHADOW_SMALL = "0 2px 4px rgba(0,0,0,0.15)"
    SHADOW_NORMAL = "0 4px 8px rgba(0,0,0,0.2)"
    SHADOW_LARGE = "0 8px 16px rgba(0,0,0,0.25)"

    # 动画时长（毫秒）
    ANIMATION_FAST = 150
    ANIMATION_NORMAL = 300
    ANIMATION_SLOW = 500


class ThemeManager:
    """主题管理器 - 单例模式"""
    _instance = None
    _current_theme = LightTheme
    _callbacks = []
    _config_path = Path("config/theme_config.json")
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._load_saved_theme()
        return cls._instance
    
    def _load_saved_theme(self):
        """加载保存的主题设置"""
        try:
            if self._config_path.exists():
                with open(self._config_path, 'r') as f:
                    config = json.load(f)
                    if config.get('theme') == 'dark':
                        self._current_theme = DarkTheme
                    elif config.get('theme') == 'light':
                        self._current_theme = LightTheme
        except Exception as e:
            logger.debug("load saved theme failed: %s", e)
    
    def _save_theme(self):
        """保存主题设置"""
        try:
            self._config_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self._config_path, 'w') as f:
                json.dump({'theme': self._current_theme.NAME}, f)
        except Exception as e:
            logger.debug("save theme failed: %s", e)
    
    @property
    def current(self) -> ThemeColors:
        return self._current_theme
    
    @property
    def is_dark(self) -> bool:
        return self._current_theme == DarkTheme
    
    def toggle(self):
        """切换主题"""
        if self._current_theme == DarkTheme:
            self._current_theme = LightTheme
        else:
            self._current_theme = DarkTheme
        self._save_theme()
        self._notify_callbacks()
    
    def set_dark(self):
        """设置深色主题"""
        if self._current_theme != DarkTheme:
            self._current_theme = DarkTheme
            self._save_theme()
            self._notify_callbacks()
    
    def set_light(self):
        """设置浅色主题"""
        if self._current_theme != LightTheme:
            self._current_theme = LightTheme
            self._save_theme()
            self._notify_callbacks()
    
    def register_callback(self, callback):
        """注册主题变更回调"""
        self._callbacks.append(callback)
    
    def unregister_callback(self, callback):
        """取消注册回调"""
        if callback in self._callbacks:
            self._callbacks.remove(callback)
    
    def _notify_callbacks(self):
        """通知所有回调"""
        for callback in self._callbacks:
            try:
                callback(self._current_theme)
            except Exception as e:
                logger.debug("theme callback failed: %s", e)


# 全局主题管理器（延迟初始化）
_theme_manager_instance = None

def get_theme_manager():
    """获取主题管理器实例（延迟初始化）"""
    global _theme_manager_instance
    if _theme_manager_instance is None:
        _theme_manager_instance = ThemeManager()
    return _theme_manager_instance

# 创建一个简单的代理对象，避免立即初始化
class _ThemeManagerLazyProxy:
    def __getattr__(self, name):
        return getattr(get_theme_manager(), name)

theme_manager = _ThemeManagerLazyProxy()


class Theme:
    """动态主题类 - 根据当前主题返回对应颜色"""
    
    @staticmethod
    def _get():
        return theme_manager.current
    
    # 主色调
    @property
    def PRIMARY(self): return self._get().PRIMARY
    @property
    def PRIMARY_DARK(self): return self._get().PRIMARY_DARK
    @property
    def PRIMARY_LIGHT(self): return self._get().PRIMARY_LIGHT
    @property
    def PRIMARY_GLOW(self): return self._get().PRIMARY_GLOW
    
    # 强调色
    @property
    def ACCENT(self): return self._get().ACCENT
    @property
    def ACCENT_DARK(self): return self._get().ACCENT_DARK
    @property
    def ACCENT_LIGHT(self): return self._get().ACCENT_LIGHT
    
    # 状态色
    @property
    def SUCCESS(self): return self._get().SUCCESS
    @property
    def WARNING(self): return self._get().WARNING
    @property
    def ERROR(self): return self._get().ERROR
    @property
    def INFO(self): return self._get().INFO
    
    # 背景色
    @property
    def BG_PRIMARY(self): return self._get().BG_PRIMARY
    @property
    def BG_SECONDARY(self): return self._get().BG_SECONDARY
    @property
    def BG_TERTIARY(self): return self._get().BG_TERTIARY
    @property
    def BG_HOVER(self): return self._get().BG_HOVER
    @property
    def BG_SELECTED(self): return self._get().BG_SELECTED
    @property
    def BG_CARD(self): return self._get().BG_CARD
    
    # 表面色
    @property
    def SURFACE(self): return self._get().SURFACE
    @property
    def SURFACE_LIGHT(self): return self._get().SURFACE_LIGHT
    @property
    def SURFACE_DARK(self): return self._get().SURFACE_DARK
    @property
    def SURFACE_GLASS(self): return self._get().SURFACE_GLASS
    
    # 文本色
    @property
    def TEXT_PRIMARY(self): return self._get().TEXT_PRIMARY
    @property
    def TEXT_SECONDARY(self): return self._get().TEXT_SECONDARY
    @property
    def TEXT_DISABLED(self): return self._get().TEXT_DISABLED
    @property
    def TEXT_HINT(self): return self._get().TEXT_HINT
    
    # 边框色
    @property
    def BORDER(self): return self._get().BORDER
    @property
    def BORDER_LIGHT(self): return self._get().BORDER_LIGHT
    @property
    def BORDER_FOCUS(self): return self._get().BORDER_FOCUS
    @property
    def BORDER_SUBTLE(self): return self._get().BORDER_SUBTLE
    
    # 分隔线
    @property
    def DIVIDER(self): return self._get().DIVIDER
    @property
    def DIVIDER_LIGHT(self): return self._get().DIVIDER_LIGHT
    
    # 字体配置（静态）
    FONT_FAMILY = "Microsoft YaHei UI"
    FONT_FAMILY_MONO = "Consolas"
    
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


# 主题代理：始终读取当前主题
class _ThemeProxy:
    def __getattr__(self, name):
        return getattr(theme_manager.current, name)


Theme = _ThemeProxy()


class Styles:
    """组件样式定义"""
    
    # 使用当前主题
    T = Theme
    
    @staticmethod
    def get_button_style(variant="primary"):
        """获取按钮样式 - 现代设计"""
        T = Theme
        if variant == "primary":
            return {
                "font": (T.FONT_FAMILY, T.FONT_SIZE_NORMAL, "600"),
                "bg": T.PRIMARY,
                "fg": T.TEXT_PRIMARY,
                "activebackground": T.PRIMARY_LIGHT,
                "activeforeground": T.TEXT_PRIMARY,
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
                "font": (T.FONT_FAMILY, T.FONT_SIZE_NORMAL, "normal"),
                "bg": T.SURFACE_LIGHT,
                "fg": T.TEXT_PRIMARY,
                "activebackground": T.BG_HOVER,
                "activeforeground": T.TEXT_PRIMARY,
                "relief": "flat",
                "bd": 0,
                "padx": 18,
                "pady": 9,
                "cursor": "hand2",
                "highlightthickness": 1,
                "highlightbackground": T.BORDER,
                "highlightcolor": T.BORDER_FOCUS,
                "borderwidth": 0
            }
        elif variant == "danger":
            return {
                "font": (T.FONT_FAMILY, T.FONT_SIZE_NORMAL, "600"),
                "bg": T.ERROR,
                "fg": T.TEXT_PRIMARY,
                "activebackground": "#DC2626",
                "activeforeground": T.TEXT_PRIMARY,
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
                "font": (T.FONT_FAMILY, T.FONT_SIZE_NORMAL, "600"),
                "bg": T.SUCCESS,
                "fg": T.TEXT_PRIMARY,
                "activebackground": "#059669",
                "activeforeground": T.TEXT_PRIMARY,
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
                "font": (T.FONT_FAMILY, T.FONT_SIZE_NORMAL, "normal"),
                "bg": "transparent",
                "fg": T.TEXT_SECONDARY,
                "activebackground": T.BG_HOVER,
                "activeforeground": T.TEXT_PRIMARY,
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

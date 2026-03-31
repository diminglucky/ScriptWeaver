"""
简化的主题配置 - 避免死锁
"""

class DarkTheme:
    """深色主题"""
    NAME = "dark"
    
    # 主色调
    PRIMARY = "#6366F1"
    PRIMARY_DARK = "#4F46E5"
    PRIMARY_LIGHT = "#818CF8"
    PRIMARY_GLOW = "rgba(99, 102, 241, 0.5)"
    
    # 强调色
    ACCENT = "#06B6D4"
    ACCENT_DARK = "#0891B2"
    ACCENT_LIGHT = "#22D3EE"
    
    # 状态色
    SUCCESS = "#10B981"
    WARNING = "#F59E0B"
    ERROR = "#EF4444"
    INFO = "#3B82F6"
    
    # 背景色
    BG_PRIMARY = "#0A0B0F"
    BG_SECONDARY = "#13141B"
    BG_TERTIARY = "#1C1D26"
    BG_HOVER = "#252631"
    BG_SELECTED = "#2D2E3D"
    BG_CARD = "#16171F"
    
    # 表面色
    SURFACE = "#18191F"
    SURFACE_LIGHT = "#22232B"
    SURFACE_DARK = "#0E0F14"
    SURFACE_GLASS = "rgba(30, 31, 40, 0.8)"
    
    # 文本色
    TEXT_PRIMARY = "#F1F3F9"
    TEXT_SECONDARY = "#9CA3AF"
    TEXT_DISABLED = "#4B5563"
    TEXT_HINT = "#6B7280"
    
    # 边框色
    BORDER = "#282A36"
    BORDER_LIGHT = "#32343E"
    BORDER_FOCUS = "#6366F1"
    BORDER_SUBTLE = "#1F2028"
    
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


# 直接使用 DarkTheme
Theme = DarkTheme


class Styles:
    """组件样式定义"""
    pass


class Icons:
    """图标定义"""
    FILE = "📄"
    FOLDER = "📁"
    SAVE = "💾"
    SUCCESS = "✅"
    ERROR = "❌"
    WARNING = "⚠️"
    SETTINGS = "⚙️"
    SEARCH = "🔍"


# 简化的主题管理器
class SimpleThemeManager:
    def __init__(self):
        self.current = DarkTheme
        self.is_dark = True
    
    def toggle(self):
        pass
    
    def register_callback(self, callback):
        pass


theme_manager = SimpleThemeManager()

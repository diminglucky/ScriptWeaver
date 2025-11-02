"""
人物照片预览管理器 - 从char_photo.py重构出来
负责人物照片的预览和显示逻辑
"""
from typing import Optional
from PIL import Image, ImageTk
import tkinter as tk

from src.core.logging_config import get_logger

logger = get_logger(__name__)


class CharacterPhotoPreview:
    """人物照片预览管理器 - 负责人物照片的预览和显示逻辑"""
    
    @staticmethod
    def update_preview(mixin_instance, img: Image.Image) -> None:
        """
        更新人物照片预览
        
        Args:
            mixin_instance: CharacterPhotoMixin实例
            img: 图片对象
        """
        try:
            canvas_width = mixin_instance.char_canvas.winfo_width()
            canvas_height = mixin_instance.char_canvas.winfo_height()
            
            # 如果Canvas还没有初始化大小，使用默认值
            if canvas_width <= 1:
                canvas_width = 400
            if canvas_height <= 1:
                canvas_height = 400
            
            img_width, img_height = img.size
            
            # 计算缩放比例
            width_ratio = canvas_width / img_width
            height_ratio = canvas_height / img_height
            scale_ratio = min(width_ratio, height_ratio, 1.0)
            
            new_w = int(img_width * scale_ratio)
            new_h = int(img_height * scale_ratio)
            
            # 缩放图片
            resized_img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
            
            # 转换为PhotoImage
            mixin_instance.character_preview_photo = ImageTk.PhotoImage(resized_img)
            
            # 更新Label
            mixin_instance.char_preview.configure(image=mixin_instance.character_preview_photo, text="")
            
            # 更新Canvas的滚动区域
            scroll_width = max(new_w, canvas_width)
            scroll_height = max(new_h, canvas_height)
            mixin_instance.char_canvas.configure(scrollregion=(0, 0, scroll_width, scroll_height))
            
            # 居中显示
            if new_w < canvas_width:
                x_offset = (canvas_width - new_w) // 2
            else:
                x_offset = 0
            
            if new_h < canvas_height:
                y_offset = (canvas_height - new_h) // 2
            else:
                y_offset = 0
            
            mixin_instance.char_canvas.coords(mixin_instance.char_canvas_window, x_offset, y_offset)
            
        except Exception as e:
            logger.error(f"更新预览失败: {e}", exc_info=True)
    
    @staticmethod
    def show_fullsize(mixin_instance, img_path: str) -> None:
        """
        显示完整尺寸图片
        
        Args:
            mixin_instance: CharacterPhotoMixin实例
            img_path: 图片路径
        """
        try:
            from PIL import Image
            
            # 创建新窗口
            fullsize_window = tk.Toplevel(mixin_instance)
            fullsize_window.title(f"完整尺寸预览 - {Path(img_path).name}")
            
            # 加载图片
            img = Image.open(img_path)
            img_width, img_height = img.size
            
            # 限制最大尺寸（适应屏幕）
            max_width = fullsize_window.winfo_screenwidth() * 0.9
            max_height = fullsize_window.winfo_screenheight() * 0.9
            
            if img_width > max_width or img_height > max_height:
                scale_ratio = min(max_width / img_width, max_height / img_height)
                new_width = int(img_width * scale_ratio)
                new_height = int(img_height * scale_ratio)
                img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
            
            # 转换为PhotoImage
            photo = ImageTk.PhotoImage(img)
            
            # 创建Label显示图片
            label = tk.Label(fullsize_window, image=photo)
            label.image = photo  # 保持引用
            label.pack()
            
            # 设置窗口大小
            fullsize_window.geometry(f"{img.width}x{img.height}")
            
        except Exception as e:
            logger.error(f"显示完整尺寸图片失败: {e}", exc_info=True)


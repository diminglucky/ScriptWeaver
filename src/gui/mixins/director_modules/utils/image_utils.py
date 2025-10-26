"""
图片处理工具
"""

from pathlib import Path
from typing import Optional, Tuple
from PIL import Image


class ImageUtils:
    """图片处理工具类"""
    
    @staticmethod
    def load_image(image_path: Path) -> Optional[Image.Image]:
        """加载图片"""
        try:
            return Image.open(image_path)
        except Exception as e:
            print(f"加载图片失败 {image_path}: {e}")
            return None
    
    @staticmethod
    def save_image(image: Image.Image, output_path: Path) -> bool:
        """保存图片"""
        try:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            image.save(output_path)
            return True
        except Exception as e:
            print(f"保存图片失败 {output_path}: {e}")
            return False
    
    @staticmethod
    def resize_image(
        image: Image.Image,
        size: Tuple[int, int],
        keep_aspect_ratio: bool = True
    ) -> Image.Image:
        """调整图片大小"""
        if keep_aspect_ratio:
            image.thumbnail(size, Image.Resampling.LANCZOS)
            return image
        else:
            return image.resize(size, Image.Resampling.LANCZOS)
    
    @staticmethod
    def get_image_size(image_path: Path) -> Optional[Tuple[int, int]]:
        """获取图片尺寸"""
        try:
            with Image.open(image_path) as img:
                return img.size
        except Exception as e:
            print(f"获取图片尺寸失败 {image_path}: {e}")
            return None
    
    @staticmethod
    def is_valid_image(file_path: Path) -> bool:
        """检查是否为有效图片"""
        try:
            with Image.open(file_path) as img:
                img.verify()
            return True
        except:
            return False
    
    @staticmethod
    def create_thumbnail(
        image_path: Path,
        thumbnail_path: Path,
        size: Tuple[int, int] = (256, 256)
    ) -> bool:
        """创建缩略图"""
        try:
            with Image.open(image_path) as img:
                img.thumbnail(size, Image.Resampling.LANCZOS)
                img.save(thumbnail_path)
            return True
        except Exception as e:
            print(f"创建缩略图失败 {image_path}: {e}")
            return False
    
    @staticmethod
    def convert_format(
        image_path: Path,
        output_path: Path,
        format: str = "PNG"
    ) -> bool:
        """转换图片格式"""
        try:
            with Image.open(image_path) as img:
                # 如果是RGBA且要转为JPEG，先转为RGB
                if format.upper() == "JPEG" and img.mode == "RGBA":
                    img = img.convert("RGB")
                img.save(output_path, format=format)
            return True
        except Exception as e:
            print(f"转换图片格式失败 {image_path}: {e}")
            return False
    
    @staticmethod
    def crop_image(
        image: Image.Image,
        box: Tuple[int, int, int, int]
    ) -> Image.Image:
        """
        裁剪图片
        
        Args:
            image: 图片对象
            box: (left, top, right, bottom)
        """
        return image.crop(box)
    
    @staticmethod
    def get_image_info(image_path: Path) -> Optional[dict]:
        """获取图片信息"""
        try:
            with Image.open(image_path) as img:
                return {
                    'format': img.format,
                    'mode': img.mode,
                    'size': img.size,
                    'width': img.width,
                    'height': img.height
                }
        except Exception as e:
            print(f"获取图片信息失败 {image_path}: {e}")
            return None


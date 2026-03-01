"""资源管理工具"""

from __future__ import annotations

from PIL import Image
from pathlib import Path
from typing import Dict, Optional, Tuple
import logging
import weakref
from collections import OrderedDict

logger = logging.getLogger(__name__)

class ImageCache:
    """LRU图片缓存管理器
    
    使用最近最少使用(LRU)策略管理图片缓存，
    自动关闭不再使用的图片以释放内存
    """
    
    def __init__(self, max_size: int = 50):
        """初始化缓存
        
        Args:
            max_size: 最大缓存数量
        """
        self.max_size = max_size
        self._cache: OrderedDict[str, Image.Image] = OrderedDict()
    
    def get(self, path: Path, size: Optional[Tuple[int, int]] = None) -> Optional[Image.Image]:
        """获取缓存的图片
        
        Args:
            path: 图片路径
            size: 可选的缩放尺寸
        
        Returns:
            缓存的图片，如果不存在则返回None
        """
        key = self._make_key(path, size)
        
        if key in self._cache:
            # 移到末尾（最近使用）
            self._cache.move_to_end(key)
            return self._cache[key]
        
        return None
    
    def put(self, path: Path, image: Image.Image, size: Optional[Tuple[int, int]] = None):
        """添加图片到缓存
        
        Args:
            path: 图片路径
            image: 图片对象
            size: 可选的缩放尺寸
        """
        key = self._make_key(path, size)
        
        # 如果已存在，先移除旧的
        if key in self._cache:
            old_img = self._cache.pop(key)
            try:
                old_img.close()
            except Exception as e:
                logger.debug("close old cached image failed: %s", e)
        
        # 如果缓存满了，移除最久未使用的
        while len(self._cache) >= self.max_size:
            oldest_key, oldest_img = self._cache.popitem(last=False)
            try:
                oldest_img.close()
            except Exception as e:
                logger.debug("close evicted cached image failed: %s", e)
        
        # 添加新图片
        self._cache[key] = image
    
    def load(self, path: Path, size: Optional[Tuple[int, int]] = None) -> Image.Image:
        """加载图片（带缓存）
        
        Args:
            path: 图片路径
            size: 可选的缩放尺寸
        
        Returns:
            图片对象
        """
        # 先尝试从缓存获取
        cached = self.get(path, size)
        if cached:
            return cached
        
        # 加载图片
        img = Image.open(path)
        
        # 如果需要缩放
        if size:
            img.thumbnail(size, Image.Resampling.LANCZOS)
        
        # 添加到缓存
        self.put(path, img, size)
        
        return img
    
    def clear(self):
        """清空缓存"""
        for img in self._cache.values():
            try:
                img.close()
            except Exception as e:
                logger.debug("close cached image on clear failed: %s", e)
        self._cache.clear()
    
    def remove(self, path: Path, size: Optional[Tuple[int, int]] = None):
        """移除指定图片
        
        Args:
            path: 图片路径
            size: 可选的缩放尺寸
        """
        key = self._make_key(path, size)
        if key in self._cache:
            img = self._cache.pop(key)
            try:
                img.close()
            except Exception as e:
                logger.debug("close removed cached image failed: %s", e)
    
    def _make_key(self, path: Path, size: Optional[Tuple[int, int]]) -> str:
        """生成缓存键"""
        key = str(path)
        if size:
            key += f"_{size[0]}x{size[1]}"
        return key
    
    def __len__(self) -> int:
        """获取缓存大小"""
        return len(self._cache)
    
    def __del__(self):
        """析构时清理资源"""
        self.clear()


# 全局图片缓存实例
_global_image_cache: Optional[ImageCache] = None


def get_image_cache(max_size: int = 50) -> ImageCache:
    """获取全局图片缓存实例
    
    Args:
        max_size: 最大缓存数量
    
    Returns:
        ImageCache实例
    """
    global _global_image_cache
    if _global_image_cache is None:
        _global_image_cache = ImageCache(max_size)
    return _global_image_cache

"""
文件操作工具 - 统一工具类
"""
from pathlib import Path
from typing import List, Optional
import shutil
import json
from src.core.logging_config import get_logger

logger = get_logger(__name__)


class FileUtils:
    """文件操作工具类"""
    
    @staticmethod
    def ensure_directory(path: Path) -> Path:
        """确保目录存在"""
        path.mkdir(parents=True, exist_ok=True)
        return path
    
    @staticmethod
    def safe_delete_file(file_path: Path) -> bool:
        """安全删除文件"""
        try:
            if file_path.exists() and file_path.is_file():
                file_path.unlink()
                return True
            return False
        except Exception as e:
            logger.error(f"删除文件失败 {file_path}: {e}")
            return False
    
    @staticmethod
    def safe_delete_directory(dir_path: Path, recursive: bool = False) -> bool:
        """安全删除目录"""
        try:
            if dir_path.exists() and dir_path.is_dir():
                if recursive:
                    shutil.rmtree(dir_path)
                else:
                    dir_path.rmdir()
                return True
            return False
        except Exception as e:
            logger.error(f"删除目录失败 {dir_path}: {e}")
            return False
    
    @staticmethod
    def list_files(
        directory: Path,
        extensions: Optional[List[str]] = None,
        recursive: bool = False
    ) -> List[Path]:
        """列出目录中的文件"""
        if not directory.exists():
            return []
        
        files = []
        pattern = "**/*" if recursive else "*"
        
        for item in directory.glob(pattern):
            if item.is_file():
                if extensions is None or item.suffix.lower() in extensions:
                    files.append(item)
        
        return sorted(files)
    
    @staticmethod
    def copy_file(src: Path, dst: Path) -> bool:
        """复制文件"""
        try:
            FileUtils.ensure_directory(dst.parent)
            shutil.copy2(src, dst)
            return True
        except Exception as e:
            logger.error(f"复制文件失败 {src} -> {dst}: {e}")
            return False
    
    @staticmethod
    def move_file(src: Path, dst: Path) -> bool:
        """移动文件"""
        try:
            FileUtils.ensure_directory(dst.parent)
            shutil.move(str(src), str(dst))
            return True
        except Exception as e:
            logger.error(f"移动文件失败 {src} -> {dst}: {e}")
            return False
    
    @staticmethod
    def read_json(file_path: Path) -> Optional[dict]:
        """读取JSON文件"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"读取JSON失败 {file_path}: {e}")
            return None
    
    @staticmethod
    def write_json(file_path: Path, data: dict, indent: int = 2) -> bool:
        """写入JSON文件"""
        try:
            FileUtils.ensure_directory(file_path.parent)
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=indent)
            return True
        except Exception as e:
            logger.error(f"写入JSON失败 {file_path}: {e}")
            return False
    
    @staticmethod
    def get_file_size(file_path: Path) -> int:
        """获取文件大小（字节）"""
        try:
            return file_path.stat().st_size
        except Exception as e:
            logger.error(f"获取文件大小失败 {file_path}: {e}")
            return 0
    
    @staticmethod
    def is_file_locked(file_path: Path) -> bool:
        """检查文件是否被锁定（Windows）"""
        try:
            # Windows特定实现
            import os
            if os.name == 'nt':
                file_path.touch()
                return False
            return False
        except (OSError, PermissionError):
            return True


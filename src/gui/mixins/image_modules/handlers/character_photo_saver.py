"""
人物照片保存器 - 从char_photo.py重构出来
负责人物照片的保存逻辑
"""
import re
import json
from pathlib import Path
from typing import Optional
from PIL import Image
from tkinter import messagebox

from src.core.logging_config import get_logger

logger = get_logger(__name__)


class CharacterPhotoSaver:
    """人物照片保存器 - 负责人物照片的保存逻辑"""
    
    @staticmethod
    def auto_save_photo(
        mixin_instance,
        index: int,
        img: Image.Image,
        character_name: str
    ) -> str:
        """
        自动保存人物照片到当前项目的characters文件夹
        
        Args:
            mixin_instance: CharacterPhotoMixin实例
            index: 人物在列表中的索引
            img: 图片对象
            character_name: 人物名称
            
        Returns:
            保存的文件路径，失败返回空字符串
        """
        try:
            if not mixin_instance.current_project:
                messagebox.showwarning("提示", "请先创建或打开一个项目，人物照片将保存到项目目录中")
                return ""
            
            characters_dir = mixin_instance.current_project.project_dir / "characters"
            characters_dir.mkdir(parents=True, exist_ok=True)
            
            if not characters_dir.exists():
                logger.error(f"文件夹创建失败：{characters_dir}")
                return ""
            
            # 生成文件名（只使用人物名称）
            clean_name = re.sub(r'[^\w\s\u4e00-\u9fff-]', '', character_name)
            filename = f"{clean_name}.png"
            save_path = characters_dir / filename
            
            logger.info(f"准备保存到：{save_path}")
            
            img.save(str(save_path))
            
            if not save_path.exists():
                logger.error(f"文件保存失败：{save_path}")
                return ""
            
            # 更新人物列表中的照片路径（使用相对路径）
            if hasattr(mixin_instance, 'character_list') and index < len(mixin_instance.character_list):
                # 转换为相对于项目目录的路径
                relative_path = save_path.relative_to(mixin_instance.current_project.project_dir)
                mixin_instance.character_list[index]["photo_path"] = str(relative_path).replace("\\", "/")
            
            # 保存人物描述到JSON文件
            CharacterPhotoSaver._save_character_info(mixin_instance, characters_dir)
            
            # 返回相对路径（相对于项目目录）
            relative_path = save_path.relative_to(mixin_instance.current_project.project_dir)
            logger.info(f"照片已保存: {save_path} (相对路径: {relative_path})")
            return str(relative_path).replace("\\", "/")
            
        except Exception as e:
            logger.error(f"保存照片失败: {e}", exc_info=True)
            return ""
    
    @staticmethod
    def auto_save_photo_with_name(
        mixin_instance,
        img: Image.Image,
        character_name: str,
        filename: str
    ) -> str:
        """
        使用指定文件名保存人物照片
        
        Args:
            mixin_instance: CharacterPhotoMixin实例
            img: 图片对象
            character_name: 人物名称
            filename: 文件名（不含扩展名）
            
        Returns:
            保存的文件路径，失败返回空字符串
        """
        try:
            if not mixin_instance.current_project:
                messagebox.showwarning("提示", "请先创建或打开一个项目")
                return ""
            
            characters_dir = mixin_instance.current_project.project_dir / "characters"
            characters_dir.mkdir(parents=True, exist_ok=True)
            
            # 清理文件名
            clean_filename = re.sub(r'[^\w\s\u4e00-\u9fff-]', '', filename)
            save_path = characters_dir / f"{clean_filename}.png"
            
            logger.info(f"准备保存到：{save_path}")
            
            img.save(str(save_path))
            
            if not save_path.exists():
                logger.error(f"文件保存失败：{save_path}")
                return ""
            
            # 保存人物描述到JSON文件
            CharacterPhotoSaver._save_character_info(mixin_instance, characters_dir)
            
            # 返回相对路径（相对于项目目录）
            relative_path = save_path.relative_to(mixin_instance.current_project.project_dir)
            logger.info(f"照片已保存: {save_path} (相对路径: {relative_path})")
            return str(relative_path).replace("\\", "/")
            
        except Exception as e:
            logger.error(f"保存照片失败: {e}", exc_info=True)
            return ""
    
    @staticmethod
    def _save_character_info(mixin_instance, characters_dir: Path) -> None:
        """保存人物信息到JSON文件"""
        try:
            if not hasattr(mixin_instance, 'character_list'):
                return
            
            characters_info_path = characters_dir / "characters_info.json"
            
            # 更新人物信息（使用扁平格式，直接以人物名称为key）
            # 确保photo_path是相对路径
            characters_info = {}
            for char in mixin_instance.character_list:
                char_name = char.get("name", "")
                if char_name:
                    photo_path = char.get("photo_path", "")
                    # 如果photo_path是绝对路径，转换为相对路径
                    if photo_path:
                        try:
                            photo_path_obj = Path(photo_path)
                            if photo_path_obj.is_absolute():
                                # 尝试转换为相对路径
                                project_dir = mixin_instance.current_project.project_dir
                                try:
                                    relative_path = photo_path_obj.relative_to(project_dir)
                                    photo_path = str(relative_path).replace("\\", "/")
                                    logger.debug(f"转换绝对路径为相对路径: {photo_path_obj} -> {photo_path}")
                                except ValueError:
                                    # 如果无法转换为相对路径（不在项目目录下），保持原样但记录警告
                                    logger.warning(f"照片路径不在项目目录下: {photo_path_obj}")
                                    photo_path = str(photo_path_obj).replace("\\", "/")
                        except Exception as e:
                            logger.warning(f"处理照片路径时出错: {e}")
                    
                    characters_info[char_name] = {
                        "description": char.get("description", ""),
                        "photo_path": photo_path
                    }
            
            # 保存到文件（扁平格式，便于加载）
            with open(characters_info_path, 'w', encoding='utf-8') as f:
                json.dump(characters_info, f, ensure_ascii=False, indent=2)
            
            logger.debug(f"人物信息已保存到: {characters_info_path}")
            
        except Exception as e:
            logger.warning(f"保存人物信息失败: {e}")


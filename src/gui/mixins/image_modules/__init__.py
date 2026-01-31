"""图片功能模块 - 组合所有子功能

包含：
- 分镜管理（shot_manager）
- 图片生成（image_generator）
- 人物管理（char_*）
- 提示词操作（prompt_ops）
- 视频工作流（video_ops）
"""

from .ui_main import ImageUIMainMixin
from .ui_create import ImageUICreateTabMixin
from .ui_character import ImageUICharacterTabMixin
from .shot_manager import ShotManagerMixin  
from .image_generator import ImageGeneratorMixin
from .char_extract import CharacterExtractMixin
from .char_photo import CharacterPhotoMixin
from .char_description import CharacterDescriptionMixin
from .char_sheet import CharacterSheetMixin
from .char_utils import CharacterUtilsMixin
from .prompt_ops import PromptOperationsMixin
from .file_ops import FileOperationsMixin
from .preview_ops import PreviewOperationsMixin
from .video_ops import VideoPromptMixin


class ImageMixin(
    ImageUIMainMixin,
    ImageUICreateTabMixin,
    ImageUICharacterTabMixin,
    ShotManagerMixin,
    ImageGeneratorMixin,
    CharacterExtractMixin,
    CharacterPhotoMixin,
    CharacterDescriptionMixin,
    CharacterSheetMixin,
    CharacterUtilsMixin,
    PromptOperationsMixin,
    FileOperationsMixin,
    PreviewOperationsMixin,
    VideoPromptMixin,
):
    """图片功能完整Mixin (组合模式)
    
    功能模块：
    - UI构建：ui_main, ui_create, ui_character
    - 分镜管理：shot_manager（含批量生成）
    - 图片生成：image_generator
    - 人物系统：char_extract, char_photo, char_description, char_sheet, char_utils
    - 提示词：prompt_ops（含AI补全、预览确认）
    - 视频工作流：video_ops（含导出功能）
    - 文件操作：file_ops, preview_ops
    """
    pass


__all__ = ['ImageMixin']


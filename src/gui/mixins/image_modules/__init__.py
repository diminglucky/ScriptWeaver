"""图片功能模块 - 组合所有子功能"""

from .ui_main import ImageUIMainMixin
from .ui_create import ImageUICreateTabMixin
from .ui_character import ImageUICharacterTabMixin
from .ui_setup import ImageUISetupTabMixin
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
    ImageUISetupTabMixin,
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
    
    原image_mixin.py (4008行) 已拆分为15个小文件
    """
    pass


__all__ = ['ImageMixin']


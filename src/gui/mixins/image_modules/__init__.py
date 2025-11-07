"""图片功能模块 - 人物管理（已简化，图片生成功能统一到导演页面）"""

from .ui_main import ImageUIMainMixin
# from .ui_create import ImageUICreateTabMixin  # ❌ 删除：图片创作统一到导演页面
from .ui_character import ImageUICharacterTabMixin
from .ui_setup import ImageUISetupTabMixin
# from .shot_manager import ShotManagerMixin  # ❌ 删除：分镜管理在导演页面
# from .image_generator import ImageGeneratorMixin  # ❌ 删除：图片生成统一到导演页面
from .char_extract import CharacterExtractMixin
from .char_photo import CharacterPhotoMixin  # ✅ 恢复：人物照片在图片管理页面生成
from .char_description import CharacterDescriptionMixin
from .char_detail import CharacterDetailMixin  # ✅ 新增：人物详情编辑（外观、服装等）
from .char_sheet import CharacterSheetMixin
from .char_utils import CharacterUtilsMixin
from .prompt_ops import PromptOperationsMixin  # ✅ 保留：故事页面需要风格选择功能
from .file_ops import FileOperationsMixin
from .sd_config import SDConfigMixin  # ⚙️ SD专用配置功能
# from .preview_ops import PreviewOperationsMixin  # ❌ 删除：预览功能简化
# from .video_ops import VideoPromptMixin  # ❌ 删除：视频提示词在导演页面


class ImageMixin(
    ImageUIMainMixin,
    # ImageUICreateTabMixin,  # ❌ 删除
    ImageUICharacterTabMixin,
    ImageUISetupTabMixin,
    # ShotManagerMixin,  # ❌ 删除
    # ImageGeneratorMixin,  # ❌ 删除
    CharacterExtractMixin,
    CharacterPhotoMixin,  # ✅ 恢复：人物照片生成
    CharacterDescriptionMixin,
    CharacterDetailMixin,  # ✅ 新增：人物详情编辑
    CharacterSheetMixin,
    CharacterUtilsMixin,
    PromptOperationsMixin,  # ✅ 保留：故事页面风格选择
    FileOperationsMixin,
    SDConfigMixin,  # ⚙️ SD专用配置
    # PreviewOperationsMixin,  # ❌ 删除
    # VideoPromptMixin,  # ❌ 删除
):
    """图片功能 - 人物管理和人物形象生成
    
    ✅ 核心功能：
    - 人物信息查看和编辑
    - 人物描述生成
    - 人物提取
    - 👤 人物照片生成（标准+表情+角度）
    - API配置
    - 风格提示词操作（故事页面需要）
    
    📸 人物形象生成：
    - 标准形象（1张）
    - 表情库（7种：开心、难过、愤怒、惊讶、害怕、中性、微笑）
    - 角度库（3种：正面、侧面、背面）
    
    🎬 与导演页面的配合：
    - 本页面：生成所有人物形象
    - 导演页面：使用这些形象生成分镜
    """
    pass


__all__ = ['ImageMixin']


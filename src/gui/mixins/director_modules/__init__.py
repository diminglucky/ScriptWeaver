"""
导演模块 - 故事转视频的完整工作流
"""

from .director_mixin import DirectorMixin
from .script_generator import ScriptGeneratorMixin
from .shot_list_generator import ShotListGeneratorMixin
from .video_prompt_builder import VideoPromptBuilderMixin
from .consistency_manager import ConsistencyManagerMixin
# from .scene_image_generator import SceneImageGeneratorMixin  # ❌ 已删除
from .project_persistence import ProjectPersistenceMixin

__all__ = [
	'DirectorMixin',
	'ScriptGeneratorMixin',
	'ShotListGeneratorMixin',
	'VideoPromptBuilderMixin',
	'ConsistencyManagerMixin',
	# 'SceneImageGeneratorMixin',  # ❌ 已删除，使用 SDConsistencyMixin 替代
	'ProjectPersistenceMixin',
]

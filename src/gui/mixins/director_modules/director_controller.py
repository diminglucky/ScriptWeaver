"""
导演控制器 - 协调各个服务和UI的主控制器
"""

from typing import Optional, Dict, List, Callable
from pathlib import Path
import threading

try:
    # 尝试相对导入（作为包使用时）
    from .models import Shot, Character, DirectorProject
    from .services import (
        PromptBuilderService,
        ImageGeneratorService,
        ShotManagerService,
        CharacterService
    )
    from .config import ConfigManager, APIConfig
    from .utils import ExceptionHandler, safe_method
except ImportError:
    # 绝对导入（独立运行时）
    from models import Shot, Character, DirectorProject
    from services import (
        PromptBuilderService,
        ImageGeneratorService,
        ShotManagerService,
        CharacterService
    )
    from config import ConfigManager, APIConfig
    from utils import ExceptionHandler, safe_method


class DirectorController:
    """
    导演控制器
    
    职责：
    1. 协调各个服务层
    2. 管理项目状态
    3. 处理业务流程
    4. 提供统一的接口给UI层
    """
    
    def __init__(self, config_manager: Optional[ConfigManager] = None):
        # 服务实例
        self.prompt_builder = PromptBuilderService()
        self.image_generator = ImageGeneratorService()
        self.shot_manager = ShotManagerService()
        self.character_service = CharacterService()
        
        # 配置管理
        self.config_manager = config_manager or ConfigManager()
        
        # 当前项目
        self.current_project: Optional[DirectorProject] = None
        
        # 异常处理
        self.logger = ExceptionHandler.get_logger(__name__)
    
    # === 项目管理 ===
    
    @safe_method(default_return=False)
    def create_project(self, project_dir: Path) -> bool:
        """创建新项目"""
        self.current_project = DirectorProject(project_dir=project_dir)
        self.current_project.ensure_directories()
        
        # 清空管理器
        self.shot_manager.clear_shots()
        self.character_service.clear_characters()
        
        self.logger.info(f"创建项目: {project_dir}")
        return True
    
    @safe_method(default_return=False)
    def load_project(self, project_dir: Path) -> bool:
        """加载项目"""
        project = DirectorProject.load(project_dir)
        if not project:
            self.logger.error(f"加载项目失败: {project_dir}")
            return False
        
        self.current_project = project
        
        # 加载到管理器
        self.shot_manager.clear_shots()
        self.shot_manager.add_shots(project.shots)
        
        self.character_service.clear_characters()
        for char in project.characters.values():
            self.character_service.add_character(char)
        
        self.logger.info(f"加载项目: {project_dir}")
        return True
    
    @safe_method(default_return=False)
    def save_project(self) -> bool:
        """保存项目"""
        if not self.current_project:
            self.logger.warning("没有活动项目")
            return False
        
        # 同步数据
        self.current_project.shots = self.shot_manager.get_all_shots()
        self.current_project.characters = self.character_service.get_all_characters()
        
        success = self.current_project.save()
        if success:
            self.logger.info(f"保存项目: {self.current_project.project_dir}")
        return success
    
    # === 分镜管理 ===
    
    @safe_method(default_return=0)
    def add_shots(self, shots: List[Shot]) -> int:
        """添加分镜"""
        self.shot_manager.add_shots(shots)
        return len(shots)
    
    @safe_method(default_return=[])
    def get_all_shots(self) -> List[Shot]:
        """获取所有分镜"""
        return self.shot_manager.get_all_shots()
    
    @safe_method(default_return=None)
    def get_shot(self, shot_number: int) -> Optional[Shot]:
        """获取指定分镜"""
        return self.shot_manager.get_shot(shot_number)
    
    @safe_method(default_return={})
    def get_shots_summary(self) -> Dict:
        """获取分镜摘要"""
        return self.shot_manager.get_shots_summary()
    
    # === 人物管理 ===
    
    @safe_method()
    def add_character(self, character: Character):
        """添加人物"""
        self.character_service.add_character(character)
    
    @safe_method(default_return=None)
    def get_character(self, name: str) -> Optional[Character]:
        """获取人物"""
        return self.character_service.get_character(name)
    
    @safe_method(default_return=[])
    def get_character_names(self) -> List[str]:
        """获取所有人物名称"""
        return self.character_service.get_character_names()
    
    @safe_method(default_return={})
    def get_all_characters(self) -> Dict[str, Character]:
        """获取所有人物"""
        return self.character_service.get_all_characters()
    
    # === 图片生成 ===
    
    def generate_shot_image(
        self,
        shot_number: int,
        variant: int = 1,
        api_config_name: str = "default_sd",
        progress_callback: Optional[Callable] = None
    ) -> Optional[str]:
        """
        生成单个分镜图片
        
        Args:
            shot_number: 分镜编号
            variant: 变体编号
            api_config_name: API配置名称
            progress_callback: 进度回调
        
        Returns:
            生成的图片路径
        """
        try:
            # 获取分镜
            shot = self.shot_manager.get_shot(shot_number)
            if not shot:
                self.logger.error(f"未找到分镜 {shot_number}")
                return None
            
            # 获取API配置
            api_config = self.config_manager.get_api_config(api_config_name)
            if not api_config:
                self.logger.error(f"未找到API配置: {api_config_name}")
                return None
            
            # 确保项目和目录
            if not self.current_project:
                self.logger.error("没有活动项目")
                return None
            
            self.current_project.ensure_directories()
            
            # 生成图片
            image_path = self.image_generator.generate_shot_image(
                shot=shot,
                shot_variant=variant,
                output_dir=self.current_project.shots_dir,
                api_config=api_config.to_dict(),
                characters_data=self.character_service.get_all_characters()
            )
            
            if progress_callback:
                progress_callback(shot_number, variant, image_path)
            
            return image_path
        
        except Exception as e:
            self.logger.error(f"生成分镜图片失败: {e}", exc_info=True)
            return None
    
    def batch_generate_shots(
        self,
        shot_numbers: Optional[List[int]] = None,
        num_variants: int = 3,
        api_config_name: str = "default_sd",
        progress_callback: Optional[Callable] = None
    ) -> Dict[int, List[str]]:
        """
        批量生成分镜图片
        
        Args:
            shot_numbers: 要生成的分镜编号列表，None表示全部
            num_variants: 每个分镜的变体数量
            api_config_name: API配置名称
            progress_callback: 进度回调 (current, total, shot_number, variant)
        
        Returns:
            {shot_number: [image_paths]}
        """
        try:
            # 确定要生成的分镜
            if shot_numbers is None:
                shots = self.shot_manager.get_all_shots()
            else:
                shots = [self.shot_manager.get_shot(n) for n in shot_numbers]
                shots = [s for s in shots if s is not None]
            
            if not shots:
                self.logger.warning("没有要生成的分镜")
                return {}
            
            # 获取API配置
            api_config = self.config_manager.get_api_config(api_config_name)
            if not api_config:
                self.logger.error(f"未找到API配置: {api_config_name}")
                return {}
            
            # 确保项目和目录
            if not self.current_project:
                self.logger.error("没有活动项目")
                return {}
            
            self.current_project.ensure_directories()
            
            # 批量生成
            results = self.image_generator.batch_generate_shots(
                shots=shots,
                output_dir=self.current_project.shots_dir,
                api_config=api_config.to_dict(),
                characters_data=self.character_service.get_all_characters(),
                num_variants=num_variants,
                progress_callback=progress_callback
            )
            
            return results
        
        except Exception as e:
            self.logger.error(f"批量生成失败: {e}", exc_info=True)
            return {}
    
    def generate_shots_async(
        self,
        shot_numbers: Optional[List[int]] = None,
        num_variants: int = 3,
        api_config_name: str = "default_sd",
        progress_callback: Optional[Callable] = None,
        completion_callback: Optional[Callable] = None
    ):
        """
        异步批量生成分镜图片
        
        Args:
            shot_numbers: 要生成的分镜编号列表
            num_variants: 每个分镜的变体数量
            api_config_name: API配置名称
            progress_callback: 进度回调
            completion_callback: 完成回调
        """
        def task():
            results = self.batch_generate_shots(
                shot_numbers=shot_numbers,
                num_variants=num_variants,
                api_config_name=api_config_name,
                progress_callback=progress_callback
            )
            
            if completion_callback:
                completion_callback(results)
        
        thread = threading.Thread(target=task, daemon=True)
        thread.start()
    
    # === 配置管理 ===
    
    @safe_method()
    def add_api_config(self, name: str, config: APIConfig):
        """添加API配置"""
        self.config_manager.add_api_config(name, config)
    
    @safe_method(default_return=None)
    def get_api_config(self, name: str) -> Optional[APIConfig]:
        """获取API配置"""
        return self.config_manager.get_api_config(name)
    
    @safe_method(default_return=[])
    def get_api_config_names(self) -> List[str]:
        """获取所有API配置名称"""
        return list(self.config_manager.api_configs.keys())
    
    # === 提示词构建 ===
    
    @safe_method(default_return=("", ""))
    def build_shot_prompt(
        self,
        shot_number: int,
        api_type: str = "sd"
    ) -> tuple:
        """
        为分镜构建提示词
        
        Returns:
            (positive_prompt, negative_prompt)
        """
        shot = self.shot_manager.get_shot(shot_number)
        if not shot:
            return "", ""
        
        return self.prompt_builder.build_shot_prompt(
            shot=shot,
            api_type=api_type,
            characters_data=self.character_service.get_all_characters()
        )
    
    # === 工具方法 ===
    
    @safe_method(default_return=False)
    def validate_project(self) -> bool:
        """验证当前项目"""
        if not self.current_project:
            return False
        
        # 验证分镜
        shot_errors = self.shot_manager.validate_shots()
        if shot_errors:
            for error in shot_errors:
                self.logger.warning(f"分镜验证: {error}")
        
        # 验证人物
        char_errors = self.character_service.validate_characters()
        if char_errors:
            for error in char_errors:
                self.logger.warning(f"人物验证: {error}")
        
        return len(shot_errors) == 0 and len(char_errors) == 0
    
    @safe_method(default_return=[])
    def get_shot_images(self, shot_number: int) -> List[Path]:
        """获取分镜的所有已生成图片"""
        if not self.current_project:
            return []
        
        shots_dir = self.current_project.shots_dir
        if not shots_dir.exists():
            return []
        
        # 查找该分镜的所有图片
        pattern = f"shot_{shot_number:03d}_*.png"
        images = list(shots_dir.glob(pattern))
        
        return sorted(images)
    
    @safe_method(default_return=0)
    def get_total_shots_count(self) -> int:
        """获取分镜总数"""
        return self.shot_manager.get_shots_count()
    
    # === 一致性配置 ===
    
    def set_consistency_mode(self, mode: str):
        """
        设置人物一致性模式
        
        Args:
            mode: 'strong' | 'medium' | 'weak'
                - strong: 强一致性，紧锁外貌，适合特写/近景
                - medium: 中等一致性，保持外貌，允许动作/表情变化（默认）
                - weak: 弱一致性，允许较大变化，适合风格化或全景
        """
        self.prompt_builder.set_consistency_mode(mode)
        self.logger.info(f"设置人物一致性模式: {mode}")
    
    def get_consistency_mode(self) -> str:
        """获取当前人物一致性模式"""
        return self.prompt_builder.consistency_mode


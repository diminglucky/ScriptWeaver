"""
分镜管理服务 - 负责分镜的创建、修改、查询等操作
"""

from typing import List, Optional, Dict

try:
    from src.gui.mixins.director_modules.models.shot import Shot
except ImportError:
    from ...gui.mixins.director_modules.models.shot import Shot


class ShotManagerService:
    """分镜管理服务"""
    
    def __init__(self):
        self.shots: List[Shot] = []
    
    def add_shot(self, shot: Shot):
        """添加分镜"""
        self.shots.append(shot)
    
    def add_shots(self, shots: List[Shot]):
        """批量添加分镜"""
        self.shots.extend(shots)
    
    def get_shot(self, shot_number: int) -> Optional[Shot]:
        """根据编号获取分镜"""
        for shot in self.shots:
            if shot.shot_number == shot_number:
                return shot
        return None
    
    def get_all_shots(self) -> List[Shot]:
        """获取所有分镜"""
        return self.shots.copy()
    
    def get_shots_count(self) -> int:
        """获取分镜数量"""
        return len(self.shots)
    
    def update_shot(self, shot_number: int, updated_shot: Shot) -> bool:
        """更新分镜"""
        for i, shot in enumerate(self.shots):
            if shot.shot_number == shot_number:
                self.shots[i] = updated_shot
                return True
        return False
    
    def delete_shot(self, shot_number: int) -> bool:
        """删除分镜"""
        for i, shot in enumerate(self.shots):
            if shot.shot_number == shot_number:
                self.shots.pop(i)
                return True
        return False
    
    def clear_shots(self):
        """清空所有分镜"""
        self.shots.clear()
    
    def get_shots_by_character(self, character_name: str) -> List[Shot]:
        """获取包含指定人物的所有分镜"""
        return [shot for shot in self.shots if shot.has_character(character_name)]
    
    def get_shots_by_scene(self, scene_id: str) -> List[Shot]:
        """获取指定场景的所有分镜"""
        return [shot for shot in self.shots if shot.scene_id == scene_id]
    
    def get_unique_characters(self) -> List[str]:
        """获取所有出现的人物名称（去重）"""
        characters = set()
        for shot in self.shots:
            characters.update(shot.characters)
        return sorted(list(characters))
    
    def get_unique_scenes(self) -> List[str]:
        """获取所有场景ID（去重）"""
        scenes = set()
        for shot in self.shots:
            if shot.scene_id:
                scenes.add(shot.scene_id)
        return sorted(list(scenes))
    
    def get_shots_summary(self) -> Dict:
        """获取分镜统计摘要"""
        return {
            'total_shots': len(self.shots),
            'characters': self.get_unique_characters(),
            'scenes': self.get_unique_scenes(),
            'shot_types': self._get_shot_types_distribution()
        }
    
    def _get_shot_types_distribution(self) -> Dict[str, int]:
        """获取镜头类型分布"""
        distribution = {}
        for shot in self.shots:
            shot_type = shot.shot_type or 'Unknown'
            distribution[shot_type] = distribution.get(shot_type, 0) + 1
        return distribution
    
    def validate_shots(self) -> List[str]:
        """验证分镜数据，返回错误信息列表"""
        errors = []
        
        # 检查分镜编号是否连续
        expected_number = 1
        for shot in sorted(self.shots, key=lambda s: s.shot_number):
            if shot.shot_number != expected_number:
                errors.append(f"分镜编号不连续：期望 {expected_number}，实际 {shot.shot_number}")
            expected_number += 1
        
        # 检查必要字段
        for shot in self.shots:
            if not shot.shot_type:
                errors.append(f"分镜 {shot.shot_number} 缺少镜头类型")
            if not shot.visual_description and not shot.scene_description:
                errors.append(f"分镜 {shot.shot_number} 缺少场景描述")
        
        return errors
    
    def reorder_shots(self):
        """重新排序分镜编号"""
        self.shots.sort(key=lambda s: s.shot_number)
        for i, shot in enumerate(self.shots, 1):
            shot.shot_number = i
    
    def parse_shots_from_script(self, script_text: str) -> List[Shot]:
        """
        从剧本文本中解析分镜（使用AI解析）
        """
        # 简单的分镜识别：按场景编号分割
        import re
        scenes = re.split(r'\n场景\s*\d+', script_text)
        shots = []
        
        for idx, scene in enumerate(scenes[1:], 1):  # 跳过第一个空元素
            if scene.strip():
                shot = Shot(
                    shot_number=idx,
                    scene_id=f"Scene_{idx}",
                    visual_description=scene.strip()[:200],  # 前200字符作为描述
                    shot_type="Medium Shot",
                    characters=[],
                    action="",
                    camera=None
                )
                shots.append(shot)
        
        return shots
    
    def export_to_dict_list(self) -> List[Dict]:
        """导出为字典列表"""
        return [shot.to_dict() for shot in self.shots]
    
    def import_from_dict_list(self, data: List[Dict]):
        """从字典列表导入"""
        self.shots = [Shot.from_dict(d) for d in data]


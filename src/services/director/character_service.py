"""
人物服务 - 负责人物数据的管理
"""
from typing import Dict, List, Optional
from pathlib import Path
import json
from src.core.logging_config import get_logger

try:
    from src.gui.mixins.director_modules.models.character import Character
except ImportError:
    from ...gui.mixins.director_modules.models.character import Character

logger = get_logger(__name__)


class CharacterService:
    """人物服务"""
    
    def __init__(self):
        self.characters: Dict[str, Character] = {}
    
    def add_character(self, character: Character):
        """添加人物"""
        self.characters[character.name] = character
    
    def get_character(self, name: str) -> Optional[Character]:
        """获取人物"""
        return self.characters.get(name)
    
    def get_all_characters(self) -> Dict[str, Character]:
        """获取所有人物"""
        return self.characters.copy()
    
    def get_character_names(self) -> List[str]:
        """获取所有人物名称"""
        return list(self.characters.keys())
    
    def update_character(self, character: Character):
        """更新人物"""
        self.characters[character.name] = character
    
    def delete_character(self, name: str) -> bool:
        """删除人物"""
        if name in self.characters:
            del self.characters[name]
            return True
        return False
    
    def clear_characters(self):
        """清空所有人物"""
        self.characters.clear()
    
    def has_character(self, name: str) -> bool:
        """检查人物是否存在"""
        return name in self.characters
    
    def get_characters_with_portraits(self) -> List[Character]:
        """获取有肖像的人物"""
        return [char for char in self.characters.values() if char.has_portrait()]

    def get_first_available_portrait(self, names: List[str]) -> Optional[str]:
        """按人物名称列表顺序返回第一个可用的肖像路径"""
        for n in names or []:
            ch = self.characters.get(n)
            if ch and ch.portrait_image:
                p = Path(ch.portrait_image)
                if p.exists():
                    return str(p)
        return None
    
    def save_characters_to_file(self, file_path: Path) -> bool:
        """保存人物数据到文件"""
        try:
            data = {
                'version': '1.0',
                'characters': {
                    name: char.to_dict()
                    for name, char in self.characters.items()
                }
            }
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            return True
        except Exception as e:
            logger.error(f"保存人物数据失败: {e}")
            return False
    
    def load_characters_from_file(self, file_path: Path) -> bool:
        """从文件加载人物数据"""
        try:
            if not file_path.exists():
                return False
            
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            characters_data = data.get('characters', {})
            self.characters = {
                name: Character.from_dict(char_data)
                for name, char_data in characters_data.items()
            }
            
            return True
        except Exception as e:
            logger.error(f"加载人物数据失败: {e}")
            return False
    
    def export_to_dict(self) -> Dict:
        """导出为字典"""
        return {
            name: char.to_dict()
            for name, char in self.characters.items()
        }
    
    def import_from_dict(self, data: Dict):
        """从字典导入"""
        self.characters = {
            name: Character.from_dict(char_data)
            for name, char_data in data.items()
        }
    
    def validate_characters(self) -> List[str]:
        """验证人物数据，返回错误信息列表"""
        errors = []
        
        for name, char in self.characters.items():
            if not char.name:
                errors.append(f"人物缺少名称")
            
            if not char.gender:
                errors.append(f"人物 {name} 缺少性别信息")
            
            # 可以添加更多验证规则
        
        return errors
    
    def get_character_by_occupation(self, occupation: str) -> List[Character]:
        """根据职业筛选人物"""
        return [
            char for char in self.characters.values()
            if occupation.lower() in char.occupation.lower()
        ]
    
    def search_characters(self, keyword: str) -> List[Character]:
        """搜索人物（按名称、职业、性格）"""
        keyword_lower = keyword.lower()
        results = []
        
        for char in self.characters.values():
            if (keyword_lower in char.name.lower() or
                keyword_lower in char.occupation.lower() or
                keyword_lower in char.personality.lower()):
                results.append(char)
        
        return results

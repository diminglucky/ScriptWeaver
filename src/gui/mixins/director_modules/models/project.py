"""
项目数据模型
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional
from pathlib import Path
import json

from .shot import Shot
from .character import Character


@dataclass
class DirectorProject:
    """导演项目数据模型"""
    project_dir: Path
    story: str = ""
    script: str = ""
    shots: List[Shot] = field(default_factory=list)
    characters: Dict[str, Character] = field(default_factory=dict)
    video_prompts: str = ""
    settings: Dict = field(default_factory=dict)
    
    def __post_init__(self):
        """初始化后处理"""
        if isinstance(self.project_dir, str):
            self.project_dir = Path(self.project_dir)
        
        # 确保 shots 是 Shot 对象列表
        for i, shot in enumerate(self.shots):
            if not isinstance(shot, Shot):
                self.shots[i] = Shot.from_dict(shot if isinstance(shot, dict) else {})
        
        # 确保 characters 中的值是 Character 对象
        for name, char in list(self.characters.items()):
            if not isinstance(char, Character):
                self.characters[name] = Character.from_dict(
                    char if isinstance(char, dict) else {'name': name}
                )
    
    @property
    def path(self) -> str:
        """项目路径字符串"""
        return str(self.project_dir)
    
    @property
    def director_dir(self) -> Path:
        """导演文件夹"""
        return self.project_dir / "director"
    
    @property
    def shots_dir(self) -> Path:
        """分镜图片文件夹"""
        return self.director_dir / "shots"
    
    @property
    def characters_dir(self) -> Path:
        """人物图片文件夹"""
        return self.project_dir / "characters"
    
    def ensure_directories(self):
        """确保所有必要的目录存在"""
        self.director_dir.mkdir(parents=True, exist_ok=True)
        self.shots_dir.mkdir(parents=True, exist_ok=True)
        self.characters_dir.mkdir(parents=True, exist_ok=True)
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            'project_dir': str(self.project_dir),
            'story': self.story,
            'script': self.script,
            'shots': [shot.to_dict() for shot in self.shots],
            'characters': {name: char.to_dict() for name, char in self.characters.items()},
            'video_prompts': self.video_prompts,
            'settings': self.settings
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'DirectorProject':
        """从字典创建对象"""
        shots = [Shot.from_dict(s) for s in data.get('shots', [])]
        
        characters = {}
        for name, char_data in data.get('characters', {}).items():
            characters[name] = Character.from_dict(char_data)
        
        return cls(
            project_dir=Path(data['project_dir']),
            story=data.get('story', ''),
            script=data.get('script', ''),
            shots=shots,
            characters=characters,
            video_prompts=data.get('video_prompts', ''),
            settings=data.get('settings', {})
        )
    
    def save(self) -> bool:
        """保存项目"""
        try:
            self.ensure_directories()
            
            # 保存主项目文件
            project_file = self.director_dir / "project.json"
            with open(project_file, 'w', encoding='utf-8') as f:
                json.dump(self.to_dict(), f, ensure_ascii=False, indent=2)
            
            return True
        except Exception as e:
            print(f"保存项目失败: {e}")
            return False
    
    @classmethod
    def load(cls, project_dir: Path) -> Optional['DirectorProject']:
        """加载项目"""
        try:
            project_file = project_dir / "director" / "project.json"
            if not project_file.exists():
                return None
            
            with open(project_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            return cls.from_dict(data)
        except Exception as e:
            print(f"加载项目失败: {e}")
            return None
    
    def add_shot(self, shot: Shot):
        """添加分镜"""
        self.shots.append(shot)
    
    def get_shot(self, shot_number: int) -> Optional[Shot]:
        """获取指定编号的分镜"""
        for shot in self.shots:
            if shot.shot_number == shot_number:
                return shot
        return None
    
    def add_character(self, character: Character):
        """添加人物"""
        self.characters[character.name] = character
    
    def get_character(self, name: str) -> Optional[Character]:
        """获取人物"""
        return self.characters.get(name)
    
    def get_character_names(self) -> List[str]:
        """获取所有人物名称"""
        return list(self.characters.keys())


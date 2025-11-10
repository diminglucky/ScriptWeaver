"""
分镜数据模型
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class ShotCamera:
    """镜头相机参数"""
    movement: str = ""  # 运动方式
    angle: str = ""     # 角度
    lens: str = ""      # 镜头类型
    
    def to_dict(self) -> Dict:
        return {
            'movement': self.movement,
            'angle': self.angle,
            'lens': self.lens
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'ShotCamera':
        return cls(
            movement=data.get('movement', ''),
            angle=data.get('angle', ''),
            lens=data.get('lens', '')
        )


@dataclass
class ShotCharacterDetail:
    """分镜中人物的详细信息"""
    name: str
    appearance: str = ""
    clothing: str = ""
    expression: str = ""
    posture: str = ""
    action: str = ""
    
    def to_dict(self) -> Dict:
        return {
            'name': self.name,
            'appearance': self.appearance,
            'clothing': self.clothing,
            'expression': self.expression,
            'posture': self.posture,
            'action': self.action
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'ShotCharacterDetail':
        return cls(
            name=data.get('name', ''),
            appearance=data.get('appearance', ''),
            clothing=data.get('clothing', ''),
            expression=data.get('expression', ''),
            posture=data.get('posture', ''),
            action=data.get('action', '')
        )


@dataclass
class Shot:
    """分镜数据模型"""
    shot_number: int
    scene_id: str = ""
    location: str = ""
    time: str = ""
    shot_type: str = ""
    visual_description: str = ""
    scene_description: str = ""
    jimeng_prompt: str = ""  # 图像生成专用提示词
    lighting: str = ""
    atmosphere: str = ""
    characters: List[str] = field(default_factory=list)
    character_details: Dict[str, ShotCharacterDetail] = field(default_factory=dict)
    action: str = ""
    emotion: str = ""
    props: List[str] = field(default_factory=list)
    camera: Optional[ShotCamera] = None
    continuity: str = ""
    duration: str = ""
    transition: str = ""
    
    def __post_init__(self):
        """初始化后处理"""
        if self.camera is None:
            self.camera = ShotCamera()
        
        # 确保 character_details 是 ShotCharacterDetail 对象
        if isinstance(self.character_details, dict):
            for key, value in list(self.character_details.items()):
                if not isinstance(value, ShotCharacterDetail):
                    if isinstance(value, dict):
                        self.character_details[key] = ShotCharacterDetail.from_dict(value)
                    elif isinstance(value, str):
                        self.character_details[key] = ShotCharacterDetail(name=key, appearance=value)
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        character_details_dict = {}
        for name, detail in self.character_details.items():
            if isinstance(detail, ShotCharacterDetail):
                character_details_dict[name] = detail.to_dict()
            elif isinstance(detail, dict):
                character_details_dict[name] = detail
            else:
                character_details_dict[name] = str(detail)
        
        return {
            'shot_number': self.shot_number,
            'scene_id': self.scene_id,
            'location': self.location,
            'time': self.time,
            'shot_type': self.shot_type,
            'visual_description': self.visual_description,
            'scene_description': self.scene_description,
            'jimeng_prompt': self.jimeng_prompt,
            'lighting': self.lighting,
            'atmosphere': self.atmosphere,
            'characters': self.characters,
            'character_details': character_details_dict,
            'action': self.action,
            'emotion': self.emotion,
            'props': self.props if isinstance(self.props, list) else [],
            'camera': self.camera.to_dict() if self.camera else {},
            'continuity': self.continuity,
            'duration': self.duration,
            'transition': self.transition
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'Shot':
        """从字典创建对象"""
        # 处理 character_details
        character_details = {}
        raw_details = data.get('character_details', {})
        if isinstance(raw_details, dict):
            for name, detail in raw_details.items():
                if isinstance(detail, dict):
                    character_details[name] = ShotCharacterDetail.from_dict(detail)
                else:
                    character_details[name] = ShotCharacterDetail(name=name, appearance=str(detail))
        
        # 处理 camera
        camera_data = data.get('camera', {})
        camera = ShotCamera.from_dict(camera_data) if camera_data else ShotCamera()
        
        return cls(
            shot_number=data.get('shot_number', 0),
            scene_id=data.get('scene_id', ''),
            location=data.get('location', ''),
            time=data.get('time', ''),
            shot_type=data.get('shot_type', ''),
            visual_description=data.get('visual_description', ''),
            scene_description=data.get('scene_description', ''),
            jimeng_prompt=data.get('jimeng_prompt', ''),
            lighting=data.get('lighting', ''),
            atmosphere=data.get('atmosphere', ''),
            characters=data.get('characters', []),
            character_details=character_details,
            action=data.get('action', ''),
            emotion=data.get('emotion', ''),
            props=data.get('props', []),
            camera=camera,
            continuity=data.get('continuity', ''),
            duration=data.get('duration', ''),
            transition=data.get('transition', '')
        )
    
    def get_description_summary(self, max_length: int = 100) -> str:
        """获取描述摘要"""
        desc = self.visual_description or self.scene_description or self.action
        if len(desc) > max_length:
            return desc[:max_length] + "..."
        return desc
    
    def has_character(self, character_name: str) -> bool:
        """检查是否包含指定人物"""
        return character_name in self.characters
    
    def get_character_detail(self, character_name: str) -> Optional[ShotCharacterDetail]:
        """获取人物详情"""
        return self.character_details.get(character_name)


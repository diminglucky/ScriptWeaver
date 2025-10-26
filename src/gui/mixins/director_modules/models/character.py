"""
人物数据模型
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class CharacterFace:
    """面部特征"""
    face_shape: str = ""
    skin_tone: str = ""
    eyes: str = ""
    eyebrows: str = ""
    nose: str = ""
    mouth: str = ""
    special_marks: str = ""
    
    def to_dict(self) -> Dict:
        return {
            'face_shape': self.face_shape,
            'skin_tone': self.skin_tone,
            'eyes': self.eyes,
            'eyebrows': self.eyebrows,
            'nose': self.nose,
            'mouth': self.mouth,
            'special_marks': self.special_marks
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'CharacterFace':
        return cls(
            face_shape=data.get('face_shape', ''),
            skin_tone=data.get('skin_tone', ''),
            eyes=data.get('eyes', ''),
            eyebrows=data.get('eyebrows', ''),
            nose=data.get('nose', ''),
            mouth=data.get('mouth', ''),
            special_marks=data.get('special_marks', '')
        )


@dataclass
class CharacterHair:
    """发型特征"""
    color: str = ""
    length: str = ""
    style: str = ""
    bangs: str = ""
    
    def to_dict(self) -> Dict:
        return {
            'color': self.color,
            'length': self.length,
            'style': self.style,
            'bangs': self.bangs
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'CharacterHair':
        return cls(
            color=data.get('color', ''),
            length=data.get('length', ''),
            style=data.get('style', ''),
            bangs=data.get('bangs', '')
        )


@dataclass
class CharacterBody:
    """身材特征"""
    height: str = ""
    body_type: str = ""
    features: str = ""
    
    def to_dict(self) -> Dict:
        return {
            'height': self.height,
            'body_type': self.body_type,
            'features': self.features
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'CharacterBody':
        return cls(
            height=data.get('height', ''),
            body_type=data.get('body_type', ''),
            features=data.get('features', '')
        )


@dataclass
class CharacterAppearance:
    """人物外观"""
    face: CharacterFace = field(default_factory=CharacterFace)
    hair: CharacterHair = field(default_factory=CharacterHair)
    body: CharacterBody = field(default_factory=CharacterBody)
    
    def to_dict(self) -> Dict:
        return {
            'face': self.face.to_dict(),
            'hair': self.hair.to_dict(),
            'body': self.body.to_dict()
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'CharacterAppearance':
        return cls(
            face=CharacterFace.from_dict(data.get('face', {})),
            hair=CharacterHair.from_dict(data.get('hair', {})),
            body=CharacterBody.from_dict(data.get('body', {}))
        )


@dataclass
class CharacterOutfit:
    """服装设定"""
    top: str = ""
    bottom: str = ""
    shoes: str = ""
    accessories: str = ""
    style: str = ""
    color_scheme: str = ""
    
    def to_dict(self) -> Dict:
        return {
            'top': self.top,
            'bottom': self.bottom,
            'shoes': self.shoes,
            'accessories': self.accessories,
            'style': self.style,
            'color_scheme': self.color_scheme
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'CharacterOutfit':
        return cls(
            top=data.get('top', ''),
            bottom=data.get('bottom', ''),
            shoes=data.get('shoes', ''),
            accessories=data.get('accessories', ''),
            style=data.get('style', ''),
            color_scheme=data.get('color_scheme', '')
        )


@dataclass
class Character:
    """人物数据模型"""
    name: str
    age: str = ""
    gender: str = ""
    occupation: str = ""
    personality: str = ""
    background: str = ""
    appearance: CharacterAppearance = field(default_factory=CharacterAppearance)
    outfits: Dict[str, CharacterOutfit] = field(default_factory=dict)
    default_expression: str = "中性"
    expressions: List[str] = field(default_factory=list)
    common_actions: str = ""
    portrait_image: Optional[str] = None
    reference_images: List[str] = field(default_factory=list)
    
    def __post_init__(self):
        """初始化后处理"""
        if not isinstance(self.appearance, CharacterAppearance):
            self.appearance = CharacterAppearance.from_dict(
                self.appearance if isinstance(self.appearance, dict) else {}
            )
        
        # 确保 outfits 中的值是 CharacterOutfit 对象
        for key, outfit in list(self.outfits.items()):
            if not isinstance(outfit, CharacterOutfit):
                self.outfits[key] = CharacterOutfit.from_dict(
                    outfit if isinstance(outfit, dict) else {}
                )
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        outfits_dict = {}
        for scene, outfit in self.outfits.items():
            if isinstance(outfit, CharacterOutfit):
                outfits_dict[scene] = outfit.to_dict()
            elif isinstance(outfit, dict):
                outfits_dict[scene] = outfit
        
        return {
            'name': self.name,
            'age': self.age,
            'gender': self.gender,
            'occupation': self.occupation,
            'personality': self.personality,
            'background': self.background,
            'appearance': self.appearance.to_dict() if isinstance(self.appearance, CharacterAppearance) else self.appearance,
            'outfits': outfits_dict,
            'default_expression': self.default_expression,
            'expressions': self.expressions,
            'common_actions': self.common_actions,
            'portrait_image': self.portrait_image,
            'reference_images': self.reference_images
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'Character':
        """从字典创建对象"""
        # 处理 appearance
        appearance_data = data.get('appearance', {})
        appearance = CharacterAppearance.from_dict(appearance_data) if appearance_data else CharacterAppearance()
        
        # 处理 outfits
        outfits = {}
        raw_outfits = data.get('outfits', {})
        for scene, outfit_data in raw_outfits.items():
            outfits[scene] = CharacterOutfit.from_dict(outfit_data) if outfit_data else CharacterOutfit()
        
        return cls(
            name=data.get('name', ''),
            age=data.get('age', ''),
            gender=data.get('gender', ''),
            occupation=data.get('occupation', ''),
            personality=data.get('personality', ''),
            background=data.get('background', ''),
            appearance=appearance,
            outfits=outfits,
            default_expression=data.get('default_expression', '中性'),
            expressions=data.get('expressions', []),
            common_actions=data.get('common_actions', ''),
            portrait_image=data.get('portrait_image'),
            reference_images=data.get('reference_images', [])
        )
    
    def get_default_outfit(self) -> CharacterOutfit:
        """获取默认服装"""
        return self.outfits.get('default', CharacterOutfit())
    
    def add_outfit(self, scene: str, outfit: CharacterOutfit):
        """添加服装"""
        self.outfits[scene] = outfit
    
    def has_portrait(self) -> bool:
        """是否有肖像图片"""
        return self.portrait_image is not None and self.portrait_image != ""


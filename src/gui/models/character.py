"""
角色数据模型 - 基于AI图片生成最佳实践优化

核心原则（来自2025最佳实践）：
1. 角色DNA模板 - 每次生成使用完全相同的详细描述
2. 三视图策略 - 先正面→侧面→背面，渐进建立一致性
3. 禁止漂移说明 - 明确什么不能变
4. 参考图锚定 - 用已生成图片作为后续参考
"""

from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional
import hashlib


@dataclass
class CharacterProfile:
    """角色设定 - 从故事中分析得到"""
    role: str = ""              # 主角/配角/反派
    gender: str = ""            # 男/女
    age_hint: str = ""          # 年龄提示
    identity: str = ""          # 身份/职业
    personality: List[str] = field(default_factory=list)
    atmosphere: str = ""        # 整体气质
    story_role: str = ""        # 故事中的作用
    appearance_hints: str = ""  # 故事中提到的外貌线索


@dataclass
class VisualFeatures:
    """视觉特征 - 结构化存储，用于构建一致性提示词"""
    # === 核心特征（绝对不变）===
    face_shape: str = ""        # 脸型：方脸/瓜子脸/圆脸/鹅蛋脸
    eye_features: str = ""      # 眼睛：剑眉星目/丹凤眼/杏眼/桃花眼
    nose_features: str = ""     # 鼻子：高挺/小巧/鹰钩
    skin_tone: str = ""         # 肤色：白皙/小麦色/古铜色
    body_type: str = ""         # 体型：高大魁梧/修长挺拔/苗条/健壮
    
    # === 外观特征（可变但需明确）===
    hair_style: str = ""        # 发型：利落短发/长发飘逸/马尾
    hair_color: str = ""        # 发色：黑色/深棕色/金色
    default_outfit: str = ""    # 默认服装
    
    # === 独特标记（提高辨识度的关键）===
    unique_marks: List[str] = field(default_factory=list)  # 痣/疤痕/配饰
    
    # === 禁止漂移说明 ===
    do_not_change: List[str] = field(default_factory=list)  # 明确不能改变的特征


@dataclass
class CharacterDNA:
    """
    角色DNA模板 - 每次生成使用的核心描述
    
    这是保持一致性的关键：将角色描述锁定为一个可复制的模板，
    每次生成都使用完全相同的核心描述，只改变姿势/场景。
    """
    # 角色ID（用于标识同一角色）
    character_id: str = ""
    
    # 锁定的核心描述（每次生成都使用）
    core_prompt: str = ""
    
    # 禁止漂移说明（negative prompt的一部分）
    negative_features: List[str] = field(default_factory=list)
    
    # 参考图路径（anchor图，用于后续生成）
    anchor_image: str = ""      # 主锚定图（通常是正面照）
    side_image: str = ""        # 侧面参考
    back_image: str = ""        # 背面参考
    
    # 生成种子（如果API支持）
    preferred_seed: int = 0
    
    def get_full_prompt(self, pose: str = "", scene: str = "", extra: str = "") -> str:
        """
        获取完整提示词
        
        结构：[角色ID] + 核心描述 + 姿势/场景 + 一致性强调
        """
        parts = []
        
        # 1. 角色标识
        if self.character_id:
            parts.append(f"[{self.character_id}]")
        
        # 2. 核心描述（每次完全一致）
        if self.core_prompt:
            parts.append(self.core_prompt)
        
        # 3. 姿势/场景（可变部分）
        if pose:
            parts.append(pose)
        if scene:
            parts.append(scene)
        if extra:
            parts.append(extra)
        
        # 4. 一致性强调
        parts.extend([
            "same person throughout",
            "consistent facial features",
            "maintain exact appearance",
        ])
        
        return ", ".join(parts)
    
    def get_negative_prompt(self) -> str:
        """获取负面提示词（禁止漂移）"""
        negatives = [
            "changing appearance",
            "different face",
            "inconsistent features",
            "morphing",
            "transformation",
        ]
        
        # 添加自定义禁止项
        negatives.extend(self.negative_features)
        
        return ", ".join(negatives)


@dataclass
class Character:
    """角色完整数据"""
    name: str
    
    # 角色设定
    profile: CharacterProfile = field(default_factory=CharacterProfile)
    
    # 外貌描述（自然语言）
    description: str = ""
    
    # 视觉特征（结构化）
    visual: VisualFeatures = field(default_factory=VisualFeatures)
    
    # 角色DNA（一致性核心）
    dna: CharacterDNA = field(default_factory=CharacterDNA)
    
    # 照片路径
    photo_paths: List[str] = field(default_factory=list)
    primary_photo: str = ""
    
    # 元数据
    character_id: str = ""
    
    def __post_init__(self):
        if not self.character_id:
            self.character_id = self._generate_id()
        # 同步到DNA
        if not self.dna.character_id:
            self.dna.character_id = self.character_id
    
    def _generate_id(self) -> str:
        hash_input = f"{self.name}_{id(self)}"
        return f"CHAR_{hashlib.md5(hash_input.encode()).hexdigest()[:6].upper()}"
    
    def build_dna(self) -> CharacterDNA:
        """
        根据视觉特征构建角色DNA
        
        这是关键方法：将结构化特征转换为可复用的提示词模板
        """
        # 构建核心描述
        core_parts = []
        
        # 基本信息
        if self.profile.gender:
            core_parts.append(self.profile.gender)
        if self.profile.age_hint:
            core_parts.append(self.profile.age_hint)
        
        # 核心面部特征（最重要）
        if self.visual.face_shape:
            core_parts.append(f"{self.visual.face_shape} face")
        if self.visual.eye_features:
            core_parts.append(self.visual.eye_features)
        if self.visual.nose_features:
            core_parts.append(self.visual.nose_features)
        if self.visual.skin_tone:
            core_parts.append(f"{self.visual.skin_tone} skin")
        
        # 体型
        if self.visual.body_type:
            core_parts.append(self.visual.body_type)
        
        # 发型发色
        if self.visual.hair_color:
            core_parts.append(f"{self.visual.hair_color} hair")
        if self.visual.hair_style:
            core_parts.append(self.visual.hair_style)
        
        # 独特标记（关键！提高辨识度）
        for mark in self.visual.unique_marks[:3]:
            core_parts.append(mark)
        
        # 默认服装
        if self.visual.default_outfit:
            core_parts.append(self.visual.default_outfit)
        
        # 更新DNA
        self.dna.character_id = self.character_id
        self.dna.core_prompt = ", ".join(core_parts)
        self.dna.negative_features = self.visual.do_not_change.copy()
        
        # 设置参考图
        if self.primary_photo:
            self.dna.anchor_image = self.primary_photo
        
        return self.dna
    
    def get_consistency_prompt(
        self,
        view: str = "front",
        expression: str = "neutral",
        outfit_override: str = "",
        scene: str = "",
        language: str = "en"
    ) -> Dict[str, str]:
        """
        获取一致性优化的提示词
        
        返回包含 positive 和 negative prompt 的字典
        """
        # 确保DNA已构建
        if not self.dna.core_prompt:
            self.build_dna()
        
        # 视角映射
        view_map = {
            "front": "front view, facing camera, direct gaze",
            "side": "side profile view, 90 degree angle",
            "back": "back view, from behind",
            "three-quarter": "three-quarter view, 45 degree angle",
        }
        
        # 表情映射
        expr_map = {
            "neutral": "neutral expression",
            "happy": "genuine smile, happy expression",
            "sad": "melancholic expression, sad eyes",
            "angry": "intense gaze, angry expression",
            "surprised": "wide eyes, surprised expression",
        }
        
        # 构建正面提示词
        positive_parts = []
        
        # 1. 角色ID + 核心描述
        positive_parts.append(f"[{self.character_id}]")
        positive_parts.append(self.dna.core_prompt)
        
        # 2. 服装（覆盖或默认）
        if outfit_override:
            positive_parts.append(outfit_override)
        
        # 3. 视角
        positive_parts.append(view_map.get(view, view_map["front"]))
        
        # 4. 表情
        positive_parts.append(expr_map.get(expression, expr_map["neutral"]))
        
        # 5. 场景
        if scene:
            positive_parts.append(scene)
        
        # 6. 一致性强调
        positive_parts.extend([
            "same person",
            "consistent appearance",
            "photorealistic",
            "high quality",
            "professional photography",
        ])
        
        # 构建负面提示词
        negative_parts = [
            "changing face",
            "morphing features",
            "inconsistent appearance",
            "different person",
            "deformed",
            "ugly",
            "blurry",
            "low quality",
        ]
        negative_parts.extend(self.dna.negative_features)
        
        return {
            "positive": ", ".join(positive_parts),
            "negative": ", ".join(negative_parts),
        }
    
    def to_dict(self) -> Dict:
        """转换为字典（用于保存）"""
        return {
            "name": self.name,
            "character_id": self.character_id,
            "description": self.description,
            "profile": asdict(self.profile),
            "visual": asdict(self.visual),
            "dna": asdict(self.dna),
            "photo_paths": self.photo_paths,
            "primary_photo": self.primary_photo,
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'Character':
        """从字典创建"""
        char = cls(name=data.get("name", ""))
        char.character_id = data.get("character_id", "")
        char.description = data.get("description", "")
        
        if "profile" in data:
            char.profile = CharacterProfile(**data["profile"])
        if "visual" in data:
            char.visual = VisualFeatures(**data["visual"])
        if "dna" in data:
            char.dna = CharacterDNA(**data["dna"])
        
        char.photo_paths = data.get("photo_paths", [])
        char.primary_photo = data.get("primary_photo", data.get("photo_path", ""))
        
        return char
    
    @classmethod
    def from_legacy(cls, old_data: Dict) -> 'Character':
        """从旧格式创建"""
        char = cls(name=old_data.get("name", ""))
        char.description = old_data.get("description", "")
        char.primary_photo = old_data.get("photo_path", "")
        
        if "character_profile" in old_data:
            p = old_data["character_profile"]
            char.profile = CharacterProfile(
                role=p.get("role", ""),
                gender=p.get("gender", ""),
                age_hint=p.get("age_hint", ""),
                identity=p.get("identity", ""),
                personality=p.get("personality", []),
                atmosphere=p.get("atmosphere", ""),
            )
        
        return char

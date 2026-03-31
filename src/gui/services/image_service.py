"""
图片生成服务 - 基于2025最佳实践优化

核心策略：
1. 三视图生成 - 先正面→侧面→背面，渐进建立一致性
2. 角色DNA模板 - 每次使用完全相同的核心描述
3. 禁止漂移说明 - 负面提示词防止特征漂移
4. 参考图锚定 - 用已生成图片作为后续参考
"""

import base64
from io import BytesIO
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from PIL import Image

from src.clients.image_client import OpenAIImageClient


@dataclass
class ImageConfig:
    provider: str = "openai"
    api_key: str = ""
    secret_key: str = ""
    base_url: str = ""
    model: str = "dall-e-3"


class ConsistencyPromptBuilder:
    """
    一致性提示词构建器
    
    核心原则：
    1. 角色DNA放在最前面
    2. 视角/姿势作为变量
    3. 一致性强调词放在最后
    4. 负面提示词防止漂移
    """
    
    # 视角提示词（渐进式，从正面开始）
    VIEW_PROMPTS = {
        "front": {
            "en": "front view, facing camera directly, symmetrical face, direct eye contact",
            "zh": "正面，面向镜头，对称面部，直视镜头",
        },
        "three-quarter": {
            "en": "three-quarter view, 45 degree angle, slight turn, same person",
            "zh": "斜侧面，45度角，微微转头，同一个人",
        },
        "side": {
            "en": "side profile view, 90 degree angle, profile shot, same person",
            "zh": "侧面，90度角，侧脸，同一个人",
        },
        "back": {
            "en": "back view, from behind, back of head visible, same person",
            "zh": "背面，背对镜头，后脑勺可见，同一个人",
        },
    }
    
    # 表情提示词
    EXPRESSION_PROMPTS = {
        "neutral": {"en": "neutral calm expression", "zh": "中性平静表情"},
        "happy": {"en": "genuine warm smile, happy", "zh": "真诚温暖的微笑，开心"},
        "sad": {"en": "melancholic expression, sad eyes", "zh": "忧郁表情，悲伤的眼神"},
        "angry": {"en": "intense fierce gaze, angry", "zh": "凌厉眼神，愤怒"},
        "surprised": {"en": "wide eyes, surprised expression", "zh": "睁大眼睛，惊讶"},
    }
    
    # 构图提示词
    COMPOSITION_PROMPTS = {
        "portrait": {"en": "portrait, head and shoulders, close-up", "zh": "肖像，头肩，特写"},
        "upper_body": {"en": "upper body shot, waist up", "zh": "上半身，腰部以上"},
        "full_body": {"en": "full body shot, head to toe", "zh": "全身照，从头到脚"},
    }
    
    # 一致性强调词
    CONSISTENCY_BOOST = {
        "en": [
            "same person throughout",
            "consistent facial features",
            "maintain exact appearance",
            "no morphing",
            "photorealistic",
            "high quality",
            "professional photography",
            "studio lighting",
        ],
        "zh": [
            "同一个人",
            "面部特征一致",
            "保持完全相同的外貌",
            "高清",
            "专业摄影",
            "影棚灯光",
        ],
    }
    
    # 负面提示词（防止漂移）
    NEGATIVE_PROMPTS = {
        "en": [
            "changing appearance",
            "different face",
            "morphing features",
            "inconsistent",
            "deformed",
            "ugly",
            "blurry",
            "low quality",
            "bad anatomy",
            "extra limbs",
            "duplicate",
            "watermark",
            "text",
        ],
        "zh": [
            "变形",
            "不同的人",
            "模糊",
            "低质量",
            "畸形",
            "多余肢体",
            "水印",
            "文字",
        ],
    }
    
    @classmethod
    def build(
        cls,
        character_dna: str,
        view: str = "front",
        expression: str = "neutral",
        composition: str = "upper_body",
        outfit: str = "",
        scene: str = "",
        language: str = "en",
        extra_negative: List[str] = None,
    ) -> Dict[str, str]:
        """
        构建一致性优化的提示词
        
        Args:
            character_dna: 角色DNA核心描述
            view: 视角
            expression: 表情
            composition: 构图
            outfit: 服装（覆盖默认）
            scene: 场景
            language: 语言
            extra_negative: 额外的负面提示词
        
        Returns:
            {"positive": "...", "negative": "..."}
        """
        lang = language if language in ["en", "zh"] else "en"
        sep = ", " if lang == "en" else "，"
        
        # === 正面提示词 ===
        positive_parts = []
        
        # 1. 构图（放最前面确定画面范围）
        comp = cls.COMPOSITION_PROMPTS.get(composition, cls.COMPOSITION_PROMPTS["upper_body"])
        positive_parts.append(comp[lang])
        
        # 2. 视角
        view_prompt = cls.VIEW_PROMPTS.get(view, cls.VIEW_PROMPTS["front"])
        positive_parts.append(view_prompt[lang])
        
        # 3. 角色DNA（核心！）
        if character_dna:
            positive_parts.append(character_dna)
        
        # 4. 表情
        expr = cls.EXPRESSION_PROMPTS.get(expression, cls.EXPRESSION_PROMPTS["neutral"])
        positive_parts.append(expr[lang])
        
        # 5. 服装
        if outfit:
            positive_parts.append(outfit)
        
        # 6. 场景
        if scene:
            positive_parts.append(scene)
        else:
            # 默认使用纯色背景（减少干扰）
            positive_parts.append("plain solid color background" if lang == "en" else "纯色背景")
        
        # 7. 一致性强调
        positive_parts.extend(cls.CONSISTENCY_BOOST[lang])
        
        # === 负面提示词 ===
        negative_parts = cls.NEGATIVE_PROMPTS[lang].copy()
        if extra_negative:
            negative_parts.extend(extra_negative)
        
        return {
            "positive": sep.join(positive_parts),
            "negative": sep.join(negative_parts),
        }
    
    @classmethod
    def optimize_for_api(cls, prompt: str, api_type: str, max_length: int = None) -> str:
        """针对不同API优化提示词长度"""
        limits = {"hunyuan": 256, "openai": 1000, "dalle": 1000}
        max_len = max_length or limits.get(api_type, 500)
        
        if len(prompt) <= max_len:
            return prompt
        
        # 智能截断
        truncated = prompt[:max_len]
        for punct in ['。', '，', '.', ',']:
            idx = truncated.rfind(punct)
            if idx > max_len * 0.7:
                return truncated[:idx + 1]
        return truncated


class ThreeViewGenerator:
    """
    三视图生成器
    
    核心策略：渐进式生成，从正面开始，逐步建立一致性
    
    生成顺序：
    1. 正面（锚定图）→ 作为后续的参考
    2. 斜侧面（45度）→ 过渡
    3. 侧面（90度）→ 验证一致性
    4. 背面（可选）
    """
    
    GENERATION_ORDER = [
        ("front", "正面锚定图", "建立角色基准"),
        ("three-quarter", "斜侧面", "45度过渡"),
        ("side", "侧面", "90度验证"),
        ("back", "背面", "完整三视图"),
    ]
    
    @classmethod
    def get_generation_sequence(cls, include_back: bool = True) -> List[Tuple[str, str, str]]:
        """获取生成序列"""
        if include_back:
            return cls.GENERATION_ORDER
        return cls.GENERATION_ORDER[:3]
    
    @classmethod
    def get_recommended_workflow(cls) -> str:
        """获取推荐的生成工作流说明"""
        return """
## 三视图生成最佳实践

### 步骤1：生成正面锚定图
- 使用完整的角色DNA描述
- 选择"正面"视角
- 生成后检查是否满意
- 满意后保存为参考图

### 步骤2：生成斜侧面（45度）
- 保持角色DNA完全不变
- 仅改变视角为"斜侧面"
- 如果与正面图差异大，重新生成

### 步骤3：生成侧面（90度）
- 保持角色DNA完全不变
- 仅改变视角为"侧面"
- 验证面部特征一致性

### 步骤4：生成背面（可选）
- 保持角色DNA完全不变
- 生成背面图

### 关键原则
1. 每次只改变视角，其他完全不变
2. 如果某个角度生成效果不好，从上一步重新开始
3. 不要跳过中间步骤
"""


class ImageService:
    """图片生成服务"""
    
    def __init__(self, config: ImageConfig):
        self.config = config
    
    def generate(
        self, 
        prompt: str, 
        negative_prompt: str = "",
        size: str = "1024x1024",
        seed: int = None,
    ) -> Optional[Image.Image]:
        """生成图片"""
        if self.config.provider == "hunyuan":
            return self._generate_hunyuan(prompt, size)
        else:
            return self._generate_openai(prompt, size)
    
    def _generate_openai(self, prompt: str, size: str) -> Optional[Image.Image]:
        client = OpenAIImageClient(
            api_key=self.config.api_key,
            base_url=self.config.base_url if self.config.base_url else None,
            model=self.config.model
        )
        results = client.generate(prompt=prompt, size=size, n=1)
        return results[0].image if results else None
    
    def _generate_hunyuan(self, prompt: str, size: str) -> Optional[Image.Image]:
        from src.clients.hunyuan_image_client import HunyuanImageClient
        
        size_map = {
            "512x512": "768:768", "768x768": "768:768",
            "1024x1024": "1024:1024", "1024x1792": "1080:1920",
        }
        resolution = size_map.get(size, "1024:1024")
        
        # 混元限制256字符
        if len(prompt) > 256:
            prompt = prompt[:256]
        
        client = HunyuanImageClient(
            secret_id=self.config.api_key,
            secret_key=self.config.secret_key
        )
        result = client.generate(prompt=prompt, resolution=resolution, style="201")
        
        if isinstance(result, dict) and "ResultImage" in result:
            img_data = base64.b64decode(result["ResultImage"])
            with Image.open(BytesIO(img_data)) as tmp_img:
                return tmp_img.copy()
        return getattr(result, 'image', None)
    
    def generate_with_consistency(
        self,
        character_dna: str,
        view: str = "front",
        expression: str = "neutral",
        composition: str = "upper_body",
        outfit: str = "",
        scene: str = "",
        extra_negative: List[str] = None,
        size: str = "1024x1024",
    ) -> Optional[Image.Image]:
        """
        使用一致性优化生成图片
        
        这是推荐的生成方法，自动应用一致性最佳实践
        """
        # 根据API类型选择语言
        language = "zh" if self.config.provider == "hunyuan" else "en"
        
        # 构建提示词
        prompts = ConsistencyPromptBuilder.build(
            character_dna=character_dna,
            view=view,
            expression=expression,
            composition=composition,
            outfit=outfit,
            scene=scene,
            language=language,
            extra_negative=extra_negative,
        )
        
        # 优化提示词长度
        api_type = self.config.provider
        positive = ConsistencyPromptBuilder.optimize_for_api(prompts["positive"], api_type)
        
        print(f"📝 生成提示词 ({view}): {positive[:100]}...")
        
        return self.generate(positive, prompts["negative"], size)


def create_image_service(img_api_presets: Dict, preset_name: str) -> Optional[ImageService]:
    if preset_name not in img_api_presets:
        return None
    p = img_api_presets[preset_name]
    if not p.get("api_key") and not p.get("secret_id"):
        return None
    return ImageService(ImageConfig(
        provider=p.get("provider", "openai"),
        api_key=p.get("api_key", p.get("secret_id", "")),
        secret_key=p.get("secret_key", ""),
        base_url=p.get("base_url", ""),
        model=p.get("model", "dall-e-3"),
    ))

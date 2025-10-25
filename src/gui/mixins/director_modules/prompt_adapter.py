"""
智能提示词适配器 - 根据不同API类型生成最优提示词
支持：Stable Diffusion、OpenAI DALL-E、腾讯混元等
"""

from typing import Dict, Tuple, Optional
import re


class PromptAdapter:
    """提示词适配器 - 针对不同API生成专门优化的提示词"""
    
    # Stable Diffusion 质量标签（用于文生图）
    SD_QUALITY_TAGS_TXT2IMG = [
        "masterpiece",
        "best quality", 
        "ultra detailed",
        "8k",
        "high resolution",
        "photorealistic",
        "cinematic lighting",
        "professional photography",
        "sharp focus",
        "highly detailed",
        "intricate details"
    ]
    
    # Stable Diffusion 质量标签（用于图生图，更轻量）
    SD_QUALITY_TAGS_IMG2IMG = [
        "high quality",
        "detailed",
        "sharp focus",
        "professional"
    ]
    
    # Stable Diffusion 负面提示词（通用）
    SD_NEGATIVE_PROMPT_COMMON = [
        "nsfw",
        "lowres",
        "bad anatomy",
        "bad hands",
        "text",
        "error",
        "missing fingers",
        "extra digit",
        "fewer digits",
        "cropped",
        "worst quality",
        "low quality",
        "jpeg artifacts",
        "signature",
        "watermark",
        "username",
        "blurry",
        "artist name"
    ]
    
    # Stable Diffusion 负面提示词（人物一致性专用）
    SD_NEGATIVE_PROMPT_CONSISTENCY = [
        "multiple people",
        "crowd",
        "different person",
        "changing appearance",
        "inconsistent clothing",
        "inconsistent hair",
        "inconsistent face",
        "different hairstyle",
        "hair color change",
        "different outfit",
        "face inconsistency",
        "character inconsistency",
        "multiple identities",
        "changing features",
        "wrong face",
        "wrong person"
    ]
    
    @classmethod
    def build_prompt_for_api(cls,
                            api_type: str,
                            scene_description: str,
                            characters: list = None,
                            character_details: dict = None,
                            shot_type: str = "",
                            action: str = "",
                            emotion: str = "",
                            is_img2img: bool = False,
                            consistency_mode: bool = False) -> Tuple[str, str]:
        """
        根据API类型构建最优提示词
        
        Args:
            api_type: API类型 ("sd", "openai", "hunyuan")
            scene_description: 场景描述
            characters: 人物列表
            character_details: 人物详细信息 {name: description}
            shot_type: 镜头类型
            action: 动作描述
            emotion: 情绪
            is_img2img: 是否是图生图模式
            consistency_mode: 是否启用人物一致性模式
            
        Returns:
            (positive_prompt, negative_prompt)
        """
        if api_type == "sd":
            return cls._build_sd_prompt(
                scene_description, characters, character_details,
                shot_type, action, emotion, is_img2img, consistency_mode
            )
        elif api_type == "openai":
            return cls._build_openai_prompt(
                scene_description, characters, character_details,
                shot_type, action, emotion
            )
        elif api_type == "hunyuan":
            return cls._build_hunyuan_prompt(
                scene_description, characters, character_details,
                shot_type, action, emotion
            )
        else:
            # 默认使用SD风格
            return cls._build_sd_prompt(
                scene_description, characters, character_details,
                shot_type, action, emotion, is_img2img, consistency_mode
            )
    
    @classmethod
    def _build_sd_prompt(cls,
                        scene_description: str,
                        characters: list,
                        character_details: dict,
                        shot_type: str,
                        action: str,
                        emotion: str,
                        is_img2img: bool,
                        consistency_mode: bool) -> Tuple[str, str]:
        """构建Stable Diffusion专用提示词（逗号分隔的标签式）"""
        
        # === 正向提示词 ===
        parts = []
        
        # 1. 质量标签（放在最前面）
        if is_img2img:
            # 图生图模式：使用更轻量的质量标签
            quality_tags = cls.SD_QUALITY_TAGS_IMG2IMG
        else:
            # 文生图模式：使用完整质量标签
            quality_tags = cls.SD_QUALITY_TAGS_TXT2IMG
        
        # 如果启用一致性模式，添加一致性标签
        if consistency_mode:
            quality_tags = quality_tags + [
                "character consistency",
                "consistent character design",
                "same person",
                "same face"
            ]
        
        parts.extend(quality_tags)
        
        # 2. 人物描述（最高优先级，放在质量标签后）
        if characters and character_details:
            for char in characters:
                if char in character_details:
                    char_desc = character_details[char]
                    # 转换为英文标签（如果是中文需要处理）
                    parts.append(cls._process_character_description(char_desc))
        
        # 3. 场景描述
        if scene_description:
            # 将场景描述转换为标签
            scene_tags = cls._convert_to_tags(scene_description)
            parts.extend(scene_tags)
        
        # 4. 动作和表情
        if action:
            action_tags = cls._convert_action_to_tags(action)
            parts.extend(action_tags)
        
        if emotion:
            emotion_tags = cls._convert_emotion_to_tags(emotion)
            parts.extend(emotion_tags)
        
        # 5. 镜头类型
        if shot_type:
            shot_tags = cls._convert_shot_type_to_tags(shot_type)
            parts.extend(shot_tags)
        
        # 6. 组合最终提示词（使用逗号分隔）
        positive_prompt = ", ".join(parts)
        
        # === 负面提示词 ===
        negative_parts = list(cls.SD_NEGATIVE_PROMPT_COMMON)
        
        # 如果启用一致性模式，添加一致性负面提示
        if consistency_mode:
            negative_parts.extend(cls.SD_NEGATIVE_PROMPT_CONSISTENCY)
        
        negative_prompt = ", ".join(negative_parts)
        
        return positive_prompt, negative_prompt
    
    @classmethod
    def _build_openai_prompt(cls,
                            scene_description: str,
                            characters: list,
                            character_details: dict,
                            shot_type: str,
                            action: str,
                            emotion: str) -> Tuple[str, str]:
        """构建OpenAI DALL-E专用提示词（自然语言描述）"""
        
        # DALL-E偏好完整的自然语言描述
        parts = []
        
        # 1. 整体场景描述
        if scene_description:
            parts.append(scene_description)
        
        # 2. 人物描述
        if characters and character_details:
            for char in characters:
                if char in character_details:
                    parts.append(f"{char}: {character_details[char]}")
        
        # 3. 动作和情绪
        if action:
            parts.append(f"Action: {action}")
        
        if emotion:
            parts.append(f"Mood: {emotion}")
        
        # 4. 镜头和质量要求
        if shot_type:
            parts.append(f"Camera: {shot_type}")
        
        parts.append("High quality professional photography, cinematic lighting, detailed")
        
        # DALL-E使用完整句子
        positive_prompt = ". ".join(parts) + "."
        
        # DALL-E不使用负面提示词
        negative_prompt = ""
        
        return positive_prompt, negative_prompt
    
    @classmethod
    def _build_hunyuan_prompt(cls,
                             scene_description: str,
                             characters: list,
                             character_details: dict,
                             shot_type: str,
                             action: str,
                             emotion: str) -> Tuple[str, str]:
        """构建腾讯混元专用提示词（中文简短描述）"""
        
        # 混元对提示词长度有限制（256字符），需要精简
        parts = []
        
        # 1. 核心场景（中文）
        if scene_description:
            # 取前100字
            parts.append(scene_description[:100])
        
        # 2. 人物（中文，精简）
        if characters and character_details:
            for char in characters:
                if char in character_details:
                    # 取关键特征
                    desc = character_details[char][:50]
                    parts.append(f"{char}:{desc}")
        
        # 3. 动作和情绪（中文）
        if action:
            parts.append(action[:30])
        
        if emotion:
            parts.append(emotion[:20])
        
        # 4. 质量要求（中文）
        parts.append("高质量,专业摄影,电影级")
        
        # 组合（使用中文逗号）
        positive_prompt = "，".join(parts)
        
        # 混元没有负面提示词
        negative_prompt = ""
        
        return positive_prompt, negative_prompt
    
    @classmethod
    def _process_character_description(cls, description: str) -> str:
        """处理人物描述，转换为SD标签格式"""
        # 简单处理：移除多余空格，转换为英文（如果需要）
        desc = description.strip()
        # 这里可以添加更复杂的处理逻辑
        return desc
    
    @classmethod
    def _convert_to_tags(cls, text: str) -> list:
        """将描述文本转换为SD标签列表"""
        # 简单策略：按逗号或句号分割
        tags = []
        for part in re.split(r'[,，。]', text):
            part = part.strip()
            if part:
                tags.append(part)
        return tags
    
    @classmethod
    def _convert_action_to_tags(cls, action: str) -> list:
        """将动作描述转换为SD标签"""
        tags = []
        action_lower = action.lower()
        
        # 常见动作映射
        action_map = {
            "走": ["walking", "movement"],
            "跑": ["running", "fast movement"],
            "站": ["standing", "static pose"],
            "坐": ["sitting", "seated"],
            "笑": ["smiling", "happy expression"],
            "说话": ["talking", "speaking"],
            "看": ["looking", "gazing"],
            "想": ["thinking", "contemplative"]
        }
        
        for key, values in action_map.items():
            if key in action or key in action_lower:
                tags.extend(values)
        
        # 如果没有匹配，返回原文
        if not tags and action:
            tags.append(action)
        
        return tags
    
    @classmethod
    def _convert_emotion_to_tags(cls, emotion: str) -> list:
        """将情绪描述转换为SD标签"""
        tags = []
        emotion_lower = emotion.lower()
        
        # 情绪映射
        emotion_map = {
            "开心": ["happy", "joyful", "cheerful"],
            "难过": ["sad", "melancholy", "sorrowful"],
            "愤怒": ["angry", "furious", "enraged"],
            "惊讶": ["surprised", "shocked", "astonished"],
            "害怕": ["scared", "frightened", "fearful"],
            "平静": ["calm", "peaceful", "serene"],
            "紧张": ["nervous", "tense", "anxious"]
        }
        
        for key, values in emotion_map.items():
            if key in emotion or key in emotion_lower:
                tags.extend(values)
        
        if not tags and emotion:
            tags.append(emotion)
        
        return tags
    
    @classmethod
    def _convert_shot_type_to_tags(cls, shot_type: str) -> list:
        """将镜头类型转换为SD标签"""
        tags = []
        shot_lower = shot_type.lower()
        
        # 镜头类型映射
        shot_map = {
            "特写": ["close-up shot", "close up", "detailed"],
            "中景": ["medium shot", "mid shot"],
            "全景": ["wide shot", "full scene", "establishing shot"],
            "远景": ["long shot", "distant view"],
            "close": ["close-up shot"],
            "medium": ["medium shot"],
            "wide": ["wide shot"],
            "full": ["full shot"]
        }
        
        for key, values in shot_map.items():
            if key in shot_type or key in shot_lower:
                tags.extend(values)
                break
        
        return tags
    
    @classmethod
    def optimize_for_img2img(cls, 
                            prompt: str, 
                            denoising_strength: float = 0.6) -> str:
        """
        为img2img优化提示词
        
        Args:
            prompt: 原始提示词
            denoising_strength: 重绘幅度（0-1）
            
        Returns:
            优化后的提示词
        """
        # 根据重绘幅度调整提示词强度
        if denoising_strength < 0.4:
            # 低重绘：保留更多原图，提示词可以更详细
            return prompt
        elif denoising_strength < 0.7:
            # 中等重绘：平衡模式
            # 移除一些质量标签，避免过度改变
            for tag in ["ultra detailed", "8k", "intricate details"]:
                prompt = prompt.replace(tag + ", ", "")
                prompt = prompt.replace(", " + tag, "")
            return prompt
        else:
            # 高重绘：接近文生图，保留完整提示词
            return prompt
    
    @classmethod
    def add_consistency_weights(cls, prompt: str, character_name: str) -> str:
        """
        为SD提示词添加权重，增强人物一致性
        
        Args:
            prompt: 原始提示词
            character_name: 人物名称
            
        Returns:
            添加权重后的提示词
        """
        # SD支持使用括号增加权重：(keyword:1.2)
        # 为人物相关的词添加权重
        consistency_keywords = [
            "same person",
            "same face",
            "character consistency",
            "consistent"
        ]
        
        for keyword in consistency_keywords:
            if keyword in prompt:
                # 添加1.3倍权重
                prompt = prompt.replace(keyword, f"({keyword}:1.3)")
        
        return prompt


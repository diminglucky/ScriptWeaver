"""
提示词适配器 - 根据不同的图片生成后端适配提示词格式
"""


class PromptAdapter:
    """提示词适配器 - 智能转换提示词格式"""
    
    @staticmethod
    def build_prompt_for_api(
        api_type: str,
        scene_description: str,
        characters: list = None,
        character_details: dict = None,
        shot_type: str = "",
        action: str = "",
        emotion: str = "",
        is_img2img: bool = False,
        consistency_mode: bool = False
    ) -> tuple:
        """
        为不同API构建优化的提示词
        
        Args:
            api_type: API类型 ("sd", "openai", "hunyuan")
            scene_description: 场景描述
            characters: 人物名称列表
            character_details: 人物详细信息字典
            shot_type: 镜头类型
            action: 动作描述
            emotion: 情感描述
            is_img2img: 是否为图生图
            consistency_mode: 是否启用一致性模式
            
        Returns:
            (prompt, negative_prompt) 元组
        """
        if api_type == "sd":
            return PromptAdapter._build_sd_prompt(
                scene_description, characters, character_details,
                shot_type, action, emotion, is_img2img, consistency_mode
            )
        elif api_type in ["openai", "hunyuan"]:
            return PromptAdapter._build_natural_language_prompt(
                scene_description, characters, character_details,
                shot_type, action, emotion
            )
        else:
            # 默认返回场景描述
            return (scene_description, "low quality, bad anatomy")
    
    @staticmethod
    def _build_sd_prompt(
        scene_desc: str,
        characters: list,
        character_details: dict,
        shot_type: str,
        action: str,
        emotion: str,
        is_img2img: bool,
        consistency_mode: bool
    ) -> tuple:
        """构建SD风格的标签式提示词"""
        tags = []
        
        # 1. 人物数量和基础标签
        if characters:
            num_chars = len(characters)
            if num_chars == 1:
                # 单人 - 检测性别
                char_name = characters[0]
                char_info = character_details.get(char_name, {}) if character_details else {}
                desc = char_info.get('description', '') or char_info.get('appearance', '')
                
                if '男' in desc or 'male' in desc.lower() or 'boy' in desc.lower():
                    tags.append("1boy")
                    tags.append("male focus")
                elif '女' in desc or 'female' in desc.lower() or 'girl' in desc.lower():
                    tags.append("1girl")
                    tags.append("female focus")
                else:
                    tags.append("1person")
                
                tags.append("solo")
                
                # 添加人物外貌特征
                tags.extend(PromptAdapter._extract_character_tags(desc))
                
            elif num_chars == 2:
                tags.append("2people")
            else:
                tags.append(f"{num_chars}people")
        
        # 2. 镜头类型
        if shot_type:
            if '特写' in shot_type or 'close' in shot_type.lower():
                tags.extend(["close-up", "portrait", "face focus"])
            elif '中景' in shot_type or 'medium' in shot_type.lower():
                tags.extend(["medium shot", "upper body"])
            elif '全景' in shot_type or 'wide' in shot_type.lower() or 'full' in shot_type.lower():
                tags.extend(["wide shot", "full body"])
        
        # 3. 动作标签
        if action:
            action_tags = PromptAdapter._extract_action_tags(action)
            tags.extend(action_tags)
        
        # 4. 场景和环境
        if scene_desc:
            scene_tags = PromptAdapter._extract_scene_tags(scene_desc)
            tags.extend(scene_tags)
        
        # 5. 情感表情
        if emotion:
            emotion_tags = PromptAdapter._extract_emotion_tags(emotion)
            tags.extend(emotion_tags)
        
        # 6. 质量标签
        tags.extend([
            "masterpiece",
            "best quality",
            "ultra detailed",
            "8k",
            "photorealistic",
            "professional photography"
        ])
        
        # 构建最终提示词
        prompt = ", ".join(tags)
        
        # 负面提示词
        negative_tags = [
            "low quality",
            "bad anatomy",
            "bad hands",
            "bad proportions",
            "blurry",
            "cropped",
            "deformed",
            "disfigured",
            "duplicate",
            "extra arms",
            "extra fingers",
            "extra legs",
            "fused fingers",
            "gross proportions",
            "long neck",
            "malformed limbs",
            "missing arms",
            "missing legs",
            "mutated hands",
            "mutation",
            "poorly drawn hands",
            "poorly drawn face",
            "ugly",
            "worst quality"
        ]
        
        # 如果是单人镜头，强化防止多人
        if characters and len(characters) == 1:
            negative_tags.extend([
                "multiple people",
                "crowd",
                "group",
                "2boys",
                "2girls",
                "3boys",
                "3girls",
                "many people"
            ])
        
        negative_prompt = ", ".join(negative_tags)
        
        return (prompt, negative_prompt)
    
    @staticmethod
    def _extract_character_tags(description: str) -> list:
        """从人物描述中提取标签"""
        tags = []
        desc_lower = description.lower()
        
        # 年龄
        if '18岁' in description or '18 years old' in desc_lower:
            tags.append("18 years old")
        elif '17岁' in description:
            tags.append("teenager")
        
        # 发型
        if '短发' in description or 'short hair' in desc_lower:
            tags.append("short hair")
        elif '长发' in description or 'long hair' in desc_lower:
            tags.append("long hair")
        
        if '马尾' in description or 'ponytail' in desc_lower:
            tags.append("ponytail")
        
        # 眼镜
        if '眼镜' in description or 'glasses' in desc_lower:
            if '黑框' in description or 'black frame' in desc_lower:
                tags.append("black framed glasses")
            else:
                tags.append("glasses")
        
        # 服装
        if '白衬衫' in description or 'white shirt' in desc_lower:
            tags.append("white shirt")
        elif '蓝色连衣裙' in description or 'blue dress' in desc_lower:
            tags.append("blue dress")
        elif '校服' in description or 'school uniform' in desc_lower:
            tags.append("school uniform")
        
        return tags
    
    @staticmethod
    def _extract_action_tags(action: str) -> list:
        """提取动作标签"""
        tags = []
        action_lower = action.lower()
        
        if '坐' in action or 'sitting' in action_lower or 'sit' in action_lower:
            tags.append("sitting")
        if '站' in action or 'standing' in action_lower or 'stand' in action_lower:
            tags.append("standing")
        if '走' in action or 'walking' in action_lower or 'walk' in action_lower:
            tags.append("walking")
        if '跑' in action or 'running' in action_lower:
            tags.append("running")
        if '看书' in action or 'reading' in action_lower:
            tags.append("reading book")
        if '写' in action or 'writing' in action_lower:
            tags.append("writing")
        if '说话' in action or 'talking' in action_lower:
            tags.append("talking")
        
        return tags
    
    @staticmethod
    def _extract_scene_tags(scene_desc: str) -> list:
        """提取场景标签"""
        tags = []
        scene_lower = scene_desc.lower()
        
        # 地点
        if '教室' in scene_desc or 'classroom' in scene_lower:
            tags.extend(["classroom", "indoors"])
        if '走廊' in scene_desc or 'hallway' in scene_lower or 'corridor' in scene_lower:
            tags.extend(["hallway", "indoors"])
        if '操场' in scene_desc or 'playground' in scene_lower:
            tags.extend(["playground", "outdoors"])
        
        # 光线
        if '阳光' in scene_desc or 'sunlight' in scene_lower:
            tags.append("sunlight")
        if '明亮' in scene_desc or 'bright' in scene_lower:
            tags.append("bright lighting")
        if '昏暗' in scene_desc or 'dim' in scene_lower:
            tags.append("dim lighting")
        
        # 物品
        if '书' in scene_desc or 'book' in scene_lower:
            tags.append("books")
        if '桌子' in scene_desc or 'desk' in scene_lower:
            tags.append("desk")
        if '黑板' in scene_desc or 'blackboard' in scene_lower:
            tags.append("blackboard")
        
        return tags
    
    @staticmethod
    def _extract_emotion_tags(emotion: str) -> list:
        """提取情感标签"""
        tags = []
        emotion_lower = emotion.lower()
        
        if '开心' in emotion or '微笑' in emotion or 'smile' in emotion_lower or 'happy' in emotion_lower:
            tags.append("smile")
        if '悲伤' in emotion or '哭' in emotion or 'sad' in emotion_lower or 'crying' in emotion_lower:
            tags.append("sad")
        if '生气' in emotion or '愤怒' in emotion or 'angry' in emotion_lower:
            tags.append("angry")
        if '惊讶' in emotion or 'surprised' in emotion_lower:
            tags.append("surprised")
        if '认真' in emotion or 'serious' in emotion_lower:
            tags.append("serious")
        
        return tags
    
    @staticmethod
    def _build_natural_language_prompt(
        scene_desc: str,
        characters: list,
        character_details: dict,
        shot_type: str,
        action: str,
        emotion: str
    ) -> tuple:
        """构建自然语言提示词（用于OpenAI/Hunyuan）"""
        parts = []
        
        # 人物描述
        if characters and character_details:
            char_descs = []
            for char_name in characters:
                char_info = character_details.get(char_name, {})
                desc = char_info.get('description', '') or char_info.get('appearance', '')
                if desc:
                    char_descs.append(f"{char_name}：{desc}")
            if char_descs:
                parts.append("人物：" + "；".join(char_descs))
        
        # 场景
        if scene_desc:
            parts.append(f"场景：{scene_desc}")
        
        # 动作
        if action:
            parts.append(f"动作：{action}")
        
        # 情感
        if emotion:
            parts.append(f"情感：{emotion}")
        
        # 镜头
        if shot_type:
            parts.append(f"镜头：{shot_type}")
        
        prompt = "。".join(parts) + "。高质量，专业摄影，细节丰富。"
        negative = "低质量，模糊，变形"
        
        return (prompt, negative)
    
    @staticmethod
    def add_consistency_weights(prompt: str, character_name: str) -> str:
        """为提示词添加一致性权重"""
        # SD支持权重语法 (tag:weight)
        # 对关键特征增加权重
        weighted_prompt = prompt.replace("glasses", "(glasses:1.2)")
        weighted_prompt = weighted_prompt.replace("short hair", "(short hair:1.1)")
        weighted_prompt = weighted_prompt.replace("white shirt", "(white shirt:1.1)")
        return weighted_prompt
    
    @staticmethod
    def adapt_for_backend(prompt: str, backend: str = "sd") -> str:
        """
        根据后端类型适配提示词
        
        Args:
            prompt: 原始提示词
            backend: 后端类型 ("sd", "openai", "hunyuan")
        
        Returns:
            适配后的提示词
        """
        if backend == "sd":
            # Stable Diffusion 使用标签式
            return PromptAdapter._to_sd_tags(prompt)
        elif backend in ["openai", "hunyuan"]:
            # OpenAI/Hunyuan 使用自然语言
            return prompt
        else:
            return prompt
    
    @staticmethod
    def _to_sd_tags(prompt: str) -> str:
        """转换为SD标签格式"""
        # 简单实现：提取关键词
        # 实际应该使用更复杂的NLP处理
        return prompt  # 暂时返回原文

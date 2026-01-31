"""
图片生成辅助工具类
"""
import re
from .image_styles import STYLE_KEYWORDS_EN, STYLE_DESC_CN, STYLE_KEYWORDS_SHORT


class ImagePromptHelper:
    """图片提示词辅助工具"""
    
    # === 敏感词列表（借鉴自 DirectorAI 的安全策略）===
    
    # 绝对禁止的词汇（会触发平台拒绝）
    FORBIDDEN_WORDS = {
        # 能量/特效类
        "lightning", "electric", "electric shock", "thunderbolt", "energy", 
        "energy beam", "energy surge", "power surge", "spark", "arc", "voltage",
        # 战斗/冲突类
        "attack", "battle", "fight", "punch", "kick", "hit", "strike", "slam", 
        "crash", "smash", "beat", "combat", "clash", "confront", "struggle",
        # 危险元素
        "fire", "flame", "burn", "explosion", "explode", "blast", "bomb", 
        "smoke", "weapon", "sword", "knife", "gun", "blade", "sharp",
        # 负面情绪
        "fierce", "intense", "aggressive", "violent", "rage", "angry", "furious", 
        "terrified", "horrified", "scream", "shout", "yell", "panic",
        # 身体恐怖
        "glowing eyes", "red eyes", "blood", "wound", "injury", "transform", 
        "mutate", "distort", "twisted",
        # 不安全动作
        "fall", "drop", "trip", "stumble", "chase", "flee", "escape",
        # 中文敏感词
        "血腥", "暴力", "裸体", "色情", "武器", "爆炸", "攻击", "战斗",
        "恐怖", "惊悚", "尖叫", "愤怒", "仇恨"
    }
    
    # 安全替换词映射
    SAFE_REPLACEMENTS = {
        "lightning": "soft light",
        "electric": "warm light",
        "glowing": "bright",
        "energy": "atmosphere",
        "swirl": "flow",
        "powerful": "beautiful",
        "strong": "elegant",
        "fierce": "calm",
        "intense": "warm",
        "dramatic": "peaceful",
        "action": "scene",
        "dynamic": "smooth",
        "gripping": "holding",
        "trembling": "gentle",
        "fight": "interaction",
        "attack": "approach",
        "battle": "encounter",
        "explosion": "bloom",
        "fire": "warmth",
        "angry": "concerned",
        "scream": "speak",
        "血腥": "红色",
        "暴力": "动作",
        "愤怒": "严肃",
        "攻击": "动作",
    }
    
    # 推荐添加的安全词汇
    SAFE_WORDS = [
        "gentle", "soft", "calm", "peaceful", "warm", "bright", "smooth",
        "quiet", "serene", "tranquil", "beautiful", "lovely", "cute", "sweet",
        "heartwarming", "pleasant", "comfortable", "slowly", "softly", "gently",
        "calmly", "smoothly", "gracefully", "elegantly"
    ]
    
    # 旧版兼容
    SENSITIVE_WORDS = list(FORBIDDEN_WORDS)
    
    @staticmethod
    def build_translation_instruction(img_type: str, has_reference_characters: bool = False, is_img2img: bool = False) -> str:
        """
        构建翻译指令
        
        Args:
            img_type: 图片类型
            has_reference_characters: 是否有参考人物
            is_img2img: 是否是图生图
        
        Returns:
            翻译指令文本
        """
        base_inst = """你是一个专业的图片提示词翻译专家。请将中文图片描述翻译为简洁、精准的英文提示词。

要求：
1. 保持原描述的核心内容和细节
2. 使用专业的图片生成术语
3. 简洁明了，去除冗余词汇
4. 保留重要的视觉元素描述
5. 适合AI图片生成使用"""

        # 根据图片类型添加风格说明
        if img_type in STYLE_KEYWORDS_EN:
            style_keywords = STYLE_KEYWORDS_EN[img_type]
            base_inst += f"\n6. 风格关键词：{style_keywords}"
        
        # 如果有参考人物，强调人物一致性
        if has_reference_characters:
            base_inst += """

⚠️ 特别重要：
- 如果描述中包含「人物外貌一致性要求」或「必须严格保持以下外貌特征」，这些是强制约束！
- 人物的外貌特征（面部、发型、服装、体型等）描述必须完整保留并放在提示词开头
- 使用强调性词汇如 "MUST HAVE", "exactly as described", "consistent with" 等
- 人物特征的权重最高，不可被其他元素稀释"""
        
        # 如果是图生图，添加相关说明
        if is_img2img:
            base_inst += """
- 这是基于参考图生成，请保持参考图中人物的关键特征
- 强调 "same person", "consistent appearance", "matching features" 等"""
        
        return base_inst
    
    @staticmethod
    def truncate_text(text: str, max_length: int = 1000, prefer_punct: bool = False) -> str:
        """
        截断过长的文本
        
        Args:
            text: 原始文本
            max_length: 最大长度
            prefer_punct: 是否优先在标点符号处截断
        
        Returns:
            截断后的文本
        """
        if len(text) <= max_length:
            return text
        
        if prefer_punct:
            # 尝试在标点符号处截断
            truncated = text[:max_length]
            # 查找最后一个句号、逗号等
            last_punct = max(
                truncated.rfind('.'),
                truncated.rfind(','),
                truncated.rfind('。'),
                truncated.rfind('，'),
                truncated.rfind('；'),
                truncated.rfind(';')
            )
            if last_punct > max_length * 0.8:  # 如果标点位置不太靠前
                return truncated[:last_punct + 1]
        
        return text[:max_length]
    
    @staticmethod
    def filter_sensitive_words(text: str) -> str:
        """
        过滤敏感词
        
        Args:
            text: 原始文本
        
        Returns:
            过滤后的文本
        """
        filtered_text = text
        for word in ImagePromptHelper.FORBIDDEN_WORDS:
            filtered_text = re.sub(re.escape(word), "", filtered_text, flags=re.IGNORECASE)
        return filtered_text
    
    @staticmethod
    def sanitize_prompt(text: str, aggressive: bool = False) -> str:
        """
        安全清理提示词（借鉴自 DirectorAI）
        
        执行以下操作：
        1. 替换敏感词为安全替代词
        2. 如果是aggressive模式，添加安全前后缀
        3. 确保使用柔和的表达方式
        
        Args:
            text: 原始提示词
            aggressive: 是否使用激进清理模式
        
        Returns:
            安全清理后的提示词
        """
        sanitized = text
        
        # 1. 替换敏感词为安全替代词
        for dangerous, safe in ImagePromptHelper.SAFE_REPLACEMENTS.items():
            sanitized = re.sub(
                re.escape(dangerous), 
                safe, 
                sanitized, 
                flags=re.IGNORECASE
            )
        
        # 2. 移除剩余的禁止词汇
        for word in ImagePromptHelper.FORBIDDEN_WORDS:
            if word.isascii():
                sanitized = re.sub(r'\b' + re.escape(word) + r'\b', '', sanitized, flags=re.IGNORECASE)
            else:
                sanitized = sanitized.replace(word, '')
        
        # 3. 清理多余空格
        sanitized = re.sub(r'\s+', ' ', sanitized).strip()
        sanitized = re.sub(r',\s*,', ',', sanitized)  # 清理连续逗号
        sanitized = re.sub(r'，\s*，', '，', sanitized)
        
        # 4. 如果是激进模式，添加安全前后缀
        if aggressive:
            safe_prefix = "Peaceful scene, safe for work. "
            safe_suffix = ". Calm and positive atmosphere, family friendly"
            
            if not sanitized.lower().startswith("peaceful"):
                sanitized = safe_prefix + sanitized
            if "family friendly" not in sanitized.lower():
                sanitized = sanitized + safe_suffix
        
        return sanitized
    
    @staticmethod
    def sanitize_video_prompt(text: str) -> str:
        """
        清理视频提示词（视频生成对提示词更敏感）
        
        Args:
            text: 原始提示词
        
        Returns:
            安全清理后的提示词
        """
        # 视频提示词需要更激进的清理
        sanitized = ImagePromptHelper.sanitize_prompt(text, aggressive=True)
        
        # 额外的视频特定替换
        video_replacements = {
            "quick": "slow",
            "fast": "gentle",
            "sudden": "gradual",
            "rapid": "smooth",
            "sharp": "soft",
            "abrupt": "gradual",
            "violent": "gentle",
            "jerky": "smooth",
        }
        
        for dangerous, safe in video_replacements.items():
            sanitized = re.sub(
                r'\b' + re.escape(dangerous) + r'\b',
                safe,
                sanitized,
                flags=re.IGNORECASE
            )
        
        return sanitized
    
    @staticmethod
    def add_safety_suffix(text: str) -> str:
        """
        添加安全后缀（确保内容合规）
        
        Args:
            text: 原始文本
        
        Returns:
            添加后缀的文本
        """
        safety_keywords = "safe for work, appropriate content, family friendly"
        if safety_keywords not in text.lower():
            return f"{text}, {safety_keywords}"
        return text
    
    @staticmethod
    def optimize_for_hunyuan(prompt_cn: str, img_type: str) -> str:
        """
        为腾讯混元API优化提示词
        
        腾讯混元有256字符限制，需要精简描述
        
        Args:
            prompt_cn: 中文提示词
            img_type: 图片类型
        
        Returns:
            优化后的提示词
        """
        # 获取风格关键词
        style_keyword = STYLE_KEYWORDS_SHORT.get(img_type, "")
        
        # 如果提示词过长，需要精简
        if len(prompt_cn) > 200:
            # 保留前150字符的核心描述
            prompt_cn = prompt_cn[:150]
            # 在最后一个句号或逗号处截断
            last_punct = max(
                prompt_cn.rfind('。'),
                prompt_cn.rfind('，'),
                prompt_cn.rfind('；')
            )
            if last_punct > 100:
                prompt_cn = prompt_cn[:last_punct + 1]
        
        # 组合风格关键词
        if style_keyword:
            if len(prompt_cn) + len(style_keyword) + 2 <= 250:
                prompt_cn = f"{prompt_cn}，{style_keyword}"
        
        # 最终长度检查
        if len(prompt_cn) > 250:
            prompt_cn = prompt_cn[:250]
        
        return prompt_cn
    
    @staticmethod
    def map_size_for_hunyuan(size: str) -> str:
        """
        映射分辨率到腾讯混元支持的格式
        
        Args:
            size: 标准尺寸格式 (如 "1024x1024")
        
        Returns:
            腾讯混元支持的尺寸
        """
        # 腾讯混元支持的分辨率映射
        size_map = {
            "1024x1024": "1024:1024",
            "1024x768": "1024:768",
            "768x1024": "768:1024",
            "1280x720": "1280:720",
            "720x1280": "720:1280",
            "1920x1080": "1920:1080",
            "1080x1920": "1080:1920",
            "768x768": "768:768"
        }
        
        return size_map.get(size, "1024:1024")


class DescriptionPromptBuilder:
    """图片描述提示词构建器"""
    
    @staticmethod
    def build_from_shot(shot_text: str, scene: str = "", roles: str = "", img_type: str = "写实照片") -> str:
        """
        从分镜头构建图片描述
        
        Args:
            shot_text: 分镜头文本
            scene: 场景描述补充
            roles: 角色特征补充
            img_type: 图片类型
        
        Returns:
            完整的图片描述
        """
        parts = []
        
        # 添加场景描述
        if scene:
            parts.append(f"场景：{scene}")
        
        # 添加分镜内容
        if shot_text:
            parts.append(shot_text)
        
        # 添加角色特征
        if roles:
            parts.append(f"人物：{roles}")
        
        # 添加风格说明
        if img_type in STYLE_DESC_CN:
            style_desc = STYLE_DESC_CN[img_type]
            parts.append(f"风格：{style_desc}")
        
        return "；".join(parts)
    
    @staticmethod
    def add_character_reference(prompt: str, character_descriptions: list[str]) -> str:
        """
        在提示词中添加人物参考描述
        
        Args:
            prompt: 原始提示词
            character_descriptions: 人物描述列表
        
        Returns:
            添加人物参考后的提示词
        """
        if not character_descriptions:
            return prompt
        
        # 构建人物一致性要求前缀
        character_prefix = "⚠️ 人物外貌一致性要求（最高优先级）：\n"
        for desc in character_descriptions:
            character_prefix += f"【必须严格保持以下外貌特征】{desc}\n"
        
        character_prefix += "\n✅ 以上人物特征是强制约束，必须100%符合！\n"
        character_prefix += "画面中的这些人物外貌、服装、发型等所有特征必须与描述完全一致。\n\n"
        character_prefix += "场景描述：\n"
        
        return character_prefix + prompt
    
    @staticmethod
    def enhance_with_details(prompt: str, lighting: str = "", camera_angle: str = "", atmosphere: str = "") -> str:
        """
        增强提示词细节
        
        Args:
            prompt: 原始提示词
            lighting: 光线描述
            camera_angle: 机位角度
            atmosphere: 氛围描述
        
        Returns:
            增强后的提示词
        """
        enhancements = []
        
        if lighting:
            enhancements.append(f"光线：{lighting}")
        if camera_angle:
            enhancements.append(f"机位：{camera_angle}")
        if atmosphere:
            enhancements.append(f"氛围：{atmosphere}")
        
        if enhancements:
            return prompt + "；" + "；".join(enhancements)
        
        return prompt


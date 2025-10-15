"""
图片生成辅助工具类
"""
import re
from .image_styles import STYLE_KEYWORDS_EN, STYLE_DESC_CN, STYLE_KEYWORDS_SHORT


class ImagePromptHelper:
    """图片提示词辅助工具"""
    
    # 敏感词列表（示例）
    SENSITIVE_WORDS = [
        "blood", "gore", "violence", "nude", "naked", "nsfw",
        "血腥", "暴力", "裸体", "色情"
    ]
    
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
        for word in ImagePromptHelper.SENSITIVE_WORDS:
            filtered_text = re.sub(re.escape(word), "", filtered_text, flags=re.IGNORECASE)
        return filtered_text
    
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


"""
提示词适配器 - 根据不同的图片生成后端适配提示词格式
重构后：使用分离的翻译和标签提取模块
"""
from typing import Optional, List, Dict, Tuple

from src.utils.prompt_translator import PromptTranslator
from src.utils.tag_extractor import TagExtractor
from src.core.logging_config import get_logger

logger = get_logger(__name__)


class PromptAdapter:
    """提示词适配器 - 智能转换提示词格式"""
    
    @staticmethod
    def translate_chinese_to_english(
        chinese_text: str,
        characters: Optional[List[str]] = None,
        character_details: Optional[Dict] = None
    ) -> str:
        """使用DeepSeek将中文jimeng_prompt翻译成详细的英文SD提示词"""
        return PromptTranslator.translate_chinese_to_english(
            chinese_text, characters, character_details
        )
    
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
            scene_description: 场景描述（可能是jimeng_prompt中文描述）
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
        # 如果是中文API（混元），直接使用场景描述
        if api_type == "hunyuan":
            # 混元支持中文，直接使用
            return (scene_description, "低质量，模糊，变形")
        
        # OpenAI类API也支持中文（会翻译），直接使用
        if api_type == "openai":
            return (scene_description, "low quality, blurry, deformed")
        
        # SD需要英文标签，进行转换
        if api_type == "sd":
            # 检查是否已经是英文（简单判断）
            if scene_description and len(scene_description) > 0 and ord(scene_description[0]) < 128:
                # 已经是英文，但可能是完整描述而不是标签
                # 检查是否包含逗号分隔的标签格式
                if "," in scene_description and len(scene_description.split(",")) > 3:
                    # 看起来是完整的SD提示词（已优化），直接使用
                    # 但需要补充人物、动作等细节和生成负面提示词
                    # 先提取现有内容作为场景描述
                    negative_prompt = PromptAdapter._build_sd_prompt(
                        "", characters, character_details,
                        shot_type, action, emotion, is_img2img, consistency_mode
                    )[1]  # 只要负面提示词
                    return (scene_description, negative_prompt)
                else:
                    # 是英文但格式简单，使用_build_sd_prompt完整构建
                    return PromptAdapter._build_sd_prompt(
                        scene_description, characters, character_details,
                        shot_type, action, emotion, is_img2img, consistency_mode
                    )
            else:
                # 中文描述，需要转换为SD标签
                logger.debug("将中文分镜头描述转换为SD英文标签...")
                return PromptAdapter._convert_chinese_to_sd_tags(
                    scene_description, characters, character_details
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
                tags.extend(TagExtractor.extract_character_tags(desc))
                
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
            action_tags = TagExtractor.extract_action_tags(action)
            tags.extend(action_tags)
        
        # 4. 场景和环境
        if scene_desc:
            scene_tags = TagExtractor.extract_scene_tags(scene_desc)
            tags.extend(scene_tags)
        
        # 5. 情感表情
        if emotion:
            emotion_tags = TagExtractor.extract_emotion_tags(emotion)
            tags.extend(emotion_tags)
        
        # 6. 质量标签（与_convert_chinese_to_sd_tags保持一致）
        tags.extend([
            "masterpiece",
            "best quality",
            "ultra detailed",
            "8k",
            # ★★★ 强化真实性（权重加强） ★★★
            "(photorealistic:1.4)",
            "(realistic:1.4)",
            "professional photography",
            # 真实性和解剖学标签（加强权重）
            "(correct anatomy:1.4)",
            "(anatomically correct:1.4)",
            "(realistic proportions:1.3)",
            "(proper hand anatomy:1.5)",
            "(realistic hands:1.5)",
            "(five fingers:1.5)",
            "(normal hands:1.4)",
            "(perfect hands:1.3)",
            "(accurate perspective:1.3)",
            "(realistic objects:1.3)",
            "physically plausible",
            "natural pose",
            "realistic body"
        ])
        
        # 构建最终提示词
        prompt = ", ".join(tags)
        
        # 负面提示词（极度增强，添加权重，与_convert_chinese_to_sd_tags保持一致）
        negative_tags = [
            # 基础质量
            "(low quality:1.4)",
            "(worst quality:1.4)",
            "(normal quality:1.2)",
            "jpeg artifacts",
            "blurry",
            "blurry face",
            # ★★★ 解剖学错误（强化权重） ★★★
            "(bad anatomy:1.5)",
            "(wrong anatomy:1.5)",
            "(anatomical nonsense:1.5)",
            "(impossible anatomy:1.5)",
            "(bad proportions:1.4)",
            "(gross proportions:1.4)",
            "deformed body",
            # ★★★ 手部问题（最高优先级防止） ★★★
            "(bad hands:1.6)",
            "(poorly drawn hands:1.6)",
            "(mutated hands:1.6)",
            "(deformed hands:1.6)",
            "(extra fingers:1.7)",
            "(missing fingers:1.7)",
            "(fused fingers:1.7)",
            "(too many fingers:1.7)",
            "(six fingers:1.7)",
            "(four fingers:1.7)",
            "(cropped hands:1.5)",
            "(worst hands:1.6)",
            "(ugly hands:1.5)",
            # 身体部位错误（加强）
            "(extra arms:1.6)",
            "(extra legs:1.6)",
            "(missing limbs:1.6)",
            "(malformed limbs:1.5)",
            "(twisted limbs:1.5)",
            "(long neck:1.4)",
            # 物体变形（强化权重）
            "(distorted objects:1.5)",
            "(warped objects:1.5)",
            "(bent screen:1.6)",
            "(curved screen:1.6)",
            "(deformed objects:1.5)",
            "(wrong perspective:1.5)",
            "(distorted geometry:1.5)",
            "(unrealistic physics:1.4)",
            # 姿势问题
            "(unnatural pose:1.4)",
            "(impossible pose:1.5)",
            "(twisted body:1.5)",
            # 人脸
            "(poorly drawn face:1.4)",
            "(deformed face:1.4)",
            "(disfigured face:1.4)",
            "ugly",
            # 其他
            "cropped",
            "duplicate",
            "(mutation:1.4)",
            "(disfigured:1.4)"
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
    
    @staticmethod
    def _convert_chinese_to_sd_tags(
        chinese_desc: str,
        characters: list = None,
        character_details: dict = None
    ) -> tuple:
        """将中文jimeng_prompt转换为SD英文标签
        
        Args:
            chinese_desc: 中文场景描述（jimeng_prompt）
            characters: 人物名称列表
            character_details: 人物详细信息
            
        Returns:
            (positive_prompt, negative_prompt) 元组
        """
        # 安全检查
        if not chinese_desc:
            return ("masterpiece, best quality, photorealistic", "low quality, blurry")
        
        tags = []
        
        # 1. 人物相关
        if characters and len(characters) > 0:
            # 检测性别
            if '女生' in chinese_desc or '女孩' in chinese_desc or '女性' in chinese_desc:
                tags.extend(["1girl", "solo", "female focus"])
            elif '男生' in chinese_desc or '男孩' in chinese_desc or '男性' in chinese_desc:
                tags.extend(["1boy", "solo", "male focus"])
            else:
                tags.append("1person")
            
            # 提取人物特征
            if '长发' in chinese_desc:
                tags.append("long hair")
            elif '短发' in chinese_desc:
                tags.append("short hair")
            
            if '黑发' in chinese_desc or '黑色头发' in chinese_desc:
                tags.append("black hair")
            elif '棕发' in chinese_desc or '棕色头发' in chinese_desc:
                tags.append("brown hair")
            
            # 服装
            if '睡衣' in chinese_desc:
                tags.append("pajamas")
            if '衬衫' in chinese_desc or '白衬衫' in chinese_desc:
                tags.append("white shirt")
            if '校服' in chinese_desc:
                tags.append("school uniform")
            if '外套' in chinese_desc:
                tags.append("jacket")
        
        # 2. 场景位置
        if '宿舍' in chinese_desc or '卧室' in chinese_desc:
            tags.extend(["bedroom", "dormitory", "indoors"])
        elif '教室' in chinese_desc:
            tags.extend(["classroom", "indoors"])
        elif '走廊' in chinese_desc:
            tags.extend(["hallway", "corridor", "indoors"])
        elif '医院' in chinese_desc:
            tags.extend(["hospital", "indoors"])
        elif '校园' in chinese_desc:
            tags.extend(["campus", "school", "outdoors"])
        
        # 3. 动作姿势
        if '倒在床上' in chinese_desc or '躺在' in chinese_desc:
            tags.append("lying on bed")
        elif '站' in chinese_desc or '站立' in chinese_desc:
            tags.append("standing")
        elif '坐' in chinese_desc:
            tags.append("sitting")
        elif '走' in chinese_desc:
            tags.append("walking")
        
        if '查看手机' in chinese_desc or '看手机' in chinese_desc or '拿着手机' in chinese_desc:
            tags.append("holding phone")
        if '手机屏幕' in chinese_desc:
            tags.append("smartphone")
        
        # 4. 表情情绪
        if '疲惫' in chinese_desc or '疲倦' in chinese_desc:
            tags.append("tired expression")
        if '微笑' in chinese_desc:
            tags.append("smile")
        if '开心' in chinese_desc:
            tags.append("happy")
        if '悲伤' in chinese_desc or '难过' in chinese_desc:
            tags.append("sad")
        if '愤怒' in chinese_desc or '生气' in chinese_desc:
            tags.append("angry")
        if '惊讶' in chinese_desc:
            tags.append("surprised")
        if '害怕' in chinese_desc:
            tags.append("scared")
        
        # 5. 光线和氛围
        if '阳光' in chinese_desc or '明亮' in chinese_desc:
            tags.append("bright lighting")
        elif '昏暗' in chinese_desc or '黑暗' in chinese_desc:
            tags.append("dim lighting")
        elif '夜晚' in chinese_desc:
            tags.append("night")
        
        if '冷色调' in chinese_desc:
            tags.append("cool color temperature")
        elif '暖色调' in chinese_desc:
            tags.append("warm color temperature")
        
        if '手机屏幕光' in chinese_desc or '手机光' in chinese_desc:
            tags.append("phone screen lighting")
        
        # 6. 镜头类型
        if '特写' in chinese_desc or '近景' in chinese_desc:
            tags.append("close-up")
        elif '中景' in chinese_desc:
            tags.append("medium shot")
        elif '全景' in chinese_desc or '远景' in chinese_desc:
            tags.append("wide shot")
        
        if '固定镜头' in chinese_desc:
            tags.append("static shot")
        if '平视' in chinese_desc:
            tags.append("eye level angle")
        elif '俯视' in chinese_desc:
            tags.append("high angle")
        elif '仰视' in chinese_desc:
            tags.append("low angle")
        
        # 7. 氛围情感
        if '孤独' in chinese_desc:
            tags.append("lonely atmosphere")
        if '温馨' in chinese_desc or '温暖' in chinese_desc:
            tags.append("warm atmosphere")
        if '紧张' in chinese_desc:
            tags.append("tense mood")
        if '浪漫' in chinese_desc:
            tags.append("romantic")
        
        # 8. 质量标签（始终添加）
        tags.extend([
            "masterpiece",
            "best quality",
            "ultra detailed",
            "8k",
            # ★★★ 强化真实性（权重加强） ★★★
            "(photorealistic:1.4)",
            "(realistic:1.4)",
            "professional photography",
            "cinematic",
            # 人脸质量
            "detailed face",
            "detailed eyes",
            "(perfect face:1.2)",
            "high resolution face",
            "sharp facial features",
            "clear facial details",
            "detailed skin texture",
            "realistic skin",
            "perfect eyes",
            "detailed pupils",
            "natural face lighting",
            # ★★★ 解剖学正确性（加强权重） ★★★
            "(correct anatomy:1.4)",
            "(anatomically correct:1.4)",
            "(realistic proportions:1.3)",
            "(proper hand anatomy:1.5)",
            "(realistic hands:1.5)",
            "(five fingers:1.5)",
            "(normal hands:1.4)",
            "(perfect hands:1.3)",
            "(correct perspective:1.3)",
            "(realistic objects:1.3)",
            "(straight edges:1.2)",
            "(accurate geometry:1.2)",
            "physically plausible",
            "natural pose",
            "realistic body"
        ])
        
        # ★★★ 核心修复：将jimeng_prompt翻译成英文故事描述 ★★★
        # 策略1: 使用DeepSeek翻译成完整英文故事描述（最优）
        # 策略2: 如果翻译失败，使用关键词提取（备用）
        
        # 尝试翻译完整的中文描述（传入人物信息以保证一致性）
        english_story = PromptTranslator.translate_chinese_to_english(
            chinese_desc, characters, character_details
        )
        
        if english_story:
            # ✅ 翻译成功：使用英文故事描述 + 质量标签
            logger.debug("✅ 使用完整英文故事描述（通过DeepSeek翻译）")
            
            # 提取质量相关的英文标签
            quality_tag_start_idx = 0
            for i, tag in enumerate(tags):
                if tag == "masterpiece":  # 质量标签的开始
                    quality_tag_start_idx = i
                    break
            
            quality_tags = tags[quality_tag_start_idx:] if quality_tag_start_idx > 0 else []
            
            # 组合：英文故事描述 + 质量标签
            if quality_tags:
                positive_prompt = f"{english_story}, {', '.join(quality_tags)}"
            else:
                positive_prompt = english_story
            
            logger.debug(f"英文故事: {english_story[:150]}...")
            logger.debug(f"质量标签数量: {len(quality_tags)}")
        else:
            # ⚠️ 翻译失败：使用关键词提取作为备用方案
            logger.debug("⚠️ 翻译失败，使用关键词提取备用方案")
            
            # 确保至少有基础标签
            if not tags or len(tags) == 0:
                # 如果连标签都没有，至少给一个基础提示词
                tags = ["1person", "photorealistic", "masterpiece", "best quality"]
                logger.warning("关键词提取失败，使用基础标签")
            
            positive_prompt = ", ".join(tags)
            logger.debug(f"提取的标签: {positive_prompt[:150]}...")
        
        # 负面提示词（极度增强，添加权重）
        negative_tags = [
            # 基础质量
            "(low quality:1.4)",
            "(worst quality:1.4)",
            "(normal quality:1.2)",
            "jpeg artifacts",
            "blurry",
            "blurry face",
            "blurry eyes",
            "low resolution",
            # ★★★ 禁止风格（现实照片，不是动漫/奇幻）★★★
            "(anime style:1.7)",
            "(anime art:1.7)",
            "(cartoon:1.6)",
            "(comic:1.6)",
            "(manga:1.6)",
            "(illustration:1.5)",
            "(fantasy:1.7)",
            "(fantasy art:1.7)",
            "(fantasy character:1.7)",
            "(fantasy elements:1.7)",
            "(magical:1.6)",
            "(supernatural:1.6)",
            "(mechanical:1.7)",
            "(mechanical parts:1.7)",
            "(mechanical structure:1.7)",
            "(mechanical arm:1.7)",
            "(mechanical hand:1.7)",
            "(skeleton hand:1.7)",
            "(bone hand:1.7)",
            "(wing:1.7)",
            "(wings:1.7)",
            "(feathered wings:1.7)",
            "(mechanical wings:1.7)",
            "(non-human:1.6)",
            "(monster:1.6)",
            "(robot:1.6)",
            "(cyborg:1.6)",
            "(mutant:1.7)",
            "(abnormal limb:1.7)",
            "(unnatural limb:1.7)",
            "(transformed arm:1.7)",
            "(transformed hand:1.7)",
            # ★★★ 解剖学错误（强化权重） ★★★
            "(bad anatomy:1.5)",
            "(wrong anatomy:1.5)",
            "(anatomical nonsense:1.5)",
            "(impossible anatomy:1.5)",
            "(bad proportions:1.4)",
            "(gross proportions:1.4)",
            "(weird proportions:1.4)",
            "deformed body",
            "distorted body",
            # ★★★ 手部问题（最高优先级防止） ★★★
            "(bad hands:1.6)",
            "(poorly drawn hands:1.6)",
            "(mutated hands:1.6)",
            "(deformed hands:1.6)",
            "(malformed hands:1.6)",
            "(extra fingers:1.7)",
            "(missing fingers:1.7)",
            "(fused fingers:1.7)",
            "(too many fingers:1.7)",
            "(extra digit:1.7)",
            "(fewer digits:1.7)",
            "(six fingers:1.7)",
            "(four fingers:1.7)",
            "(three fingers:1.7)",
            "(cropped hands:1.5)",
            "(worst hands:1.6)",
            "(ugly hands:1.5)",
            "(abnormal hands:1.5)",
            "liquid hands",
            "messy hands",
            "mutilated hands",
            # 身体部位错误（加强）
            "(extra arms:1.6)",
            "(extra legs:1.6)",
            "(missing arms:1.6)",
            "(missing legs:1.6)",
            "(malformed limbs:1.5)",
            "(fused limbs:1.5)",
            "(long neck:1.4)",
            "(extra body parts:1.5)",
            "(twisted limbs:1.5)",
            "(broken limbs:1.5)",
            # 人脸问题（加强）
            "(poorly drawn face:1.4)",
            "(deformed face:1.4)",
            "(disfigured face:1.4)",
            "cropped face",
            "ugly face",
            "(distorted face:1.3)",
            "asymmetric face",
            "(bad eyes:1.3)",
            "crossed eyes",
            # ★★★ 物体变形（强化权重） ★★★
            "(distorted objects:1.5)",
            "(warped objects:1.5)",
            "(bent screen:1.6)",
            "(curved screen:1.6)",
            "(deformed objects:1.5)",
            "(impossible objects:1.5)",
            "(warped perspective:1.5)",
            "(wrong perspective:1.5)",
            "(distorted geometry:1.5)",
            "(bent lines:1.4)",
            "(unrealistic physics:1.4)",
            # 姿势问题
            "(unnatural pose:1.4)",
            "(impossible pose:1.5)",
            "(twisted body:1.5)",
            "(contorted:1.5)",
            # 其他
            "duplicate",
            "(mutation:1.4)",
            "(disfigured:1.4)",
            "(deformed:1.4)",
            "error",
            "ugly",
            "morbid"
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
                "3girls"
            ])
        
        negative_prompt = ", ".join(negative_tags)
        
        logger.debug(f"转换结果: 原文={chinese_desc[:100]}..., 英文={positive_prompt[:200]}...")
        
        return (positive_prompt, negative_prompt)

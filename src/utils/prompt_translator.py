"""
提示词翻译模块 - 从prompt_adapter.py重构出来
负责将中文提示词翻译为英文
"""
from typing import Optional, List, Dict

from src.core.logging_config import get_logger

logger = get_logger(__name__)

# 导入DeepSeek客户端用于翻译jimeng_prompt
try:
    from src.clients.deepseek_client import DeepSeekClient
    DEEPSEEK_AVAILABLE = True
except Exception as e:
    logger.warning(f"DeepSeek客户端不可用，无法翻译中文prompt: {e}")
    DEEPSEEK_AVAILABLE = False


class PromptTranslator:
    """提示词翻译器 - 将中文提示词翻译为英文"""
    
    # 缓存翻译客户端
    _deepseek_client: Optional[DeepSeekClient] = None
    
    @staticmethod
    def _get_deepseek_client() -> Optional[DeepSeekClient]:
        """获取或创建DeepSeek客户端（单例模式）"""
        if not DEEPSEEK_AVAILABLE:
            return None
        
        if PromptTranslator._deepseek_client is None:
            try:
                PromptTranslator._deepseek_client = DeepSeekClient()
            except Exception as e:
                logger.error(f"无法创建DeepSeek客户端: {e}")
                return None
        
        return PromptTranslator._deepseek_client
    
    @staticmethod
    def translate_chinese_to_english(
        chinese_text: str,
        characters: Optional[List[str]] = None,
        character_details: Optional[Dict] = None
    ) -> str:
        """
        使用DeepSeek将中文jimeng_prompt翻译成详细的英文SD提示词
        
        Args:
            chinese_text: 中文场景描述（jimeng_prompt）
            characters: 人物名称列表（用于增强一致性）
            character_details: 人物详细信息（用于增强一致性）
            
        Returns:
            英文提示词，保留所有故事细节
        """
        if not chinese_text or not chinese_text.strip():
            return ""
        
        # 检查是否已经是英文
        if chinese_text and len(chinese_text) > 0 and ord(chinese_text[0]) < 128:
            logger.debug("文本已经是英文，直接返回")
            return chinese_text
        
        client = PromptTranslator._get_deepseek_client()
        if not client:
            logger.warning("DeepSeek不可用，使用关键词提取作为备用方案")
            return ""  # 返回空，将使用关键词提取
        
        try:
            logger.info(f"开始翻译jimeng_prompt为英文故事描述...")
            logger.debug(f"原文: {chinese_text[:100]}...")
            
            # 构建翻译提示词（包含人物信息以保证一致性）
            character_info = PromptTranslator._build_character_info(
                characters, character_details
            )
            
            messages = PromptTranslator._build_translation_messages(
                chinese_text, character_info
            )
            
            # 调用API翻译
            response = client.chat(messages, temperature=0.3, max_tokens=2000)
            
            if response and 'choices' in response and len(response['choices']) > 0:
                english_text = response['choices'][0]['message']['content'].strip()
                
                # 清理响应（移除可能的markdown标记）
                english_text = english_text.replace("```", "").strip()
                if english_text.startswith("english:"):
                    english_text = english_text.replace("english:", "").strip()
                
                logger.info("翻译完成!")
                logger.debug(f"英文: {english_text[:200]}...")
                
                return english_text
            else:
                logger.warning("翻译API返回空响应")
                return ""
                
        except Exception as e:
            logger.error(f"翻译失败: {e}", exc_info=True)
            logger.info("将使用关键词提取作为备用方案")
            return ""
    
    @staticmethod
    def _build_character_info(
        characters: Optional[List[str]],
        character_details: Optional[Dict]
    ) -> str:
        """构建人物信息字符串"""
        character_info = ""
        
        if characters and len(characters) > 0:
            char_name = characters[0]
            character_info = f"\n\n重要：画面中的主要人物是 {char_name}，"
            
            if character_details and char_name in character_details:
                details = character_details[char_name]
                features = []
                if details.get('gender'):
                    features.append(f"性别：{details['gender']}")
                if details.get('age'):
                    features.append(f"年龄：{details['age']}")
                if details.get('appearance'):
                    features.append(f"外貌：{details['appearance']}")
                if details.get('clothing'):
                    features.append(f"服装：{details['clothing']}")
                
                if features:
                    character_info += "，".join(features) + "。请在翻译时确保这些人物特征被完整保留。"
        
        return character_info
    
    @staticmethod
    def _build_translation_messages(chinese_text: str, character_info: str) -> List[Dict]:
        """构建翻译消息"""
        system_message = """你是一个专业的图像生成提示词翻译专家。你的任务是将中文场景描述翻译成详细的英文Stable Diffusion提示词。

要求：
1. 完整保留所有故事细节：时间、地点、人物、动作、表情、服装、光线、氛围、镜头等
2. 使用自然流畅的英文描述，不要只是关键词列表
3. 保持原文的叙事性和画面感
4. 适合作为Stable Diffusion的prompt使用
5. 不要添加额外的解释或评论，只输出翻译后的英文描述
6. 特别注意人物的外貌、服装、发型等特征描述，确保人物一致性

示例：
中文：清晨的教室里，一个16岁的男生坐在窗边，阳光透过窗户洒在他身上。他穿着白色校服，表情疲惫，眼神空洞地看着窗外。
英文：Morning sunlight streams through the window of a classroom, illuminating a 16-year-old boy sitting by the window. He wears a white school uniform, his expression tired and weary, gazing emptily out the window with hollow eyes."""

        user_message = f"""请将以下中文场景描述翻译成详细的英文Stable Diffusion提示词：

{chinese_text}{character_info}

请直接输出翻译后的英文描述，不要添加任何其他内容。"""

        return [
            {"role": "system", "content": system_message},
            {"role": "user", "content": user_message}
        ]


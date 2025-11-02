"""
SD提示词构建器 - 从director_mixin.py重构出来
负责构建用于Stable Diffusion的图像生成提示词
"""
from typing import Dict, List, Optional
import re

from src.core.logging_config import get_logger

logger = get_logger(__name__)


class SDPromptBuilder:
    """SD提示词构建器 - 构建优化的英文提示词，确保人物和场景一致性"""
    
    @staticmethod
    def build_optimized_prompt(shot: Dict, shot_num: int, consistency_data: Optional[Dict] = None) -> str:
        """为SD构建优化的英文提示词，确保人物和场景一致性
        
        Args:
            shot: 分镜字典
            shot_num: 分镜编号
            consistency_data: 一致性数据（可选）
            
        Returns:
            str: 构建的英文提示词
        """
        # === 第一部分：质量和风格标签（最前面，权重最高） ===
        quality_tags = [
            "masterpiece", "best quality", "ultra detailed", "8k", "photorealistic",
            "cinematic lighting", "professional photography", "sharp focus",
            "highly detailed", "intricate details",
            "character consistency", "consistent character design", "same person"
        ]
        
        # === 第二部分：人物一致性描述（核心！） ===
        character_prompts = SDPromptBuilder._build_character_prompts(
            shot, consistency_data
        )
        
        # === 第三部分：场景和环境 ===
        scene_parts = SDPromptBuilder._build_scene_parts(shot)
        
        # === 第四部分：动作和表情 ===
        action_parts = SDPromptBuilder._build_action_parts(shot)
        
        # === 第五部分：镜头类型 ===
        shot_type_en = SDPromptBuilder._build_shot_type(shot)
        
        # === 组合最终提示词 ===
        final_prompt = ", ".join(quality_tags)
        
        # 人物描述放在最前面，权重最高
        if character_prompts:
            final_prompt += ", " + ", ".join(character_prompts)
        
        # 动作和表情
        if action_parts:
            final_prompt += ", " + ", ".join(action_parts)
        
        # 场景环境
        if scene_parts:
            final_prompt += ", " + ", ".join(scene_parts)
        
        # 镜头类型
        if shot_type_en:
            final_prompt += ", " + shot_type_en
        
        # 添加具体的环境描述（更详细）
        final_prompt = SDPromptBuilder._add_location_details(final_prompt, shot)
        
        # 添加故事连贯性描述
        final_prompt = SDPromptBuilder._add_continuity_details(final_prompt, shot)
        
        # 添加情绪氛围
        final_prompt = SDPromptBuilder._add_emotion_details(final_prompt, shot)
        
        logger.debug(f"SD提示词 (分镜{shot_num}): {len(final_prompt)}字符")
        
        return final_prompt
    
    @staticmethod
    def _build_character_prompts(shot: Dict, consistency_data: Optional[Dict] = None) -> List[str]:
        """构建人物提示词"""
        character_prompts = []
        characters = shot.get('characters', [])
        character_details = shot.get('character_details', {})
        
        for char_name in characters:
            char_parts = []
            
            # 从分镜获取详细信息
            if isinstance(character_details, dict) and char_name in character_details:
                detail = character_details[char_name]
                if isinstance(detail, dict):
                    char_parts.extend(SDPromptBuilder._extract_character_details(detail))
            
            # 优先使用一致性设定中的完整信息
            if consistency_data:
                consistency_chars = consistency_data.get('characters', {})
                if char_name in consistency_chars:
                    char_data = consistency_chars[char_name]
                    char_parts.extend(SDPromptBuilder._extract_consistency_details(char_data, char_parts))
            
            if char_parts:
                # 去重并组合
                char_prompt = ", ".join(dict.fromkeys(char_parts))
                character_prompts.append(char_prompt)
        
        return character_prompts
    
    @staticmethod
    def _extract_character_details(detail: Dict) -> List[str]:
        """从分镜详情中提取人物特征"""
        char_parts = []
        char_parts.append("1person")
        
        # 外貌特征
        if detail.get('appearance'):
            appearance = detail['appearance']
            char_parts.extend(SDPromptBuilder._extract_appearance_features(appearance))
        
        # 服装
        if detail.get('clothing'):
            clothing = detail['clothing']
            char_parts.extend(SDPromptBuilder._extract_clothing_features(clothing))
        
        # 表情
        if detail.get('expression'):
            expression = detail['expression']
            char_parts.extend(SDPromptBuilder._extract_expression_features(expression))
        
        # 姿势和动作
        if detail.get('posture'):
            posture = detail['posture']
            char_parts.extend(SDPromptBuilder._extract_posture_features(posture))
        
        return char_parts
    
    @staticmethod
    def _extract_appearance_features(appearance: str) -> List[str]:
        """提取外貌特征"""
        features = []
        
        # 年龄和性别
        if "岁" in appearance:
            age_match = re.search(r'(\d+)岁', appearance)
            if age_match:
                age = int(age_match.group(1))
                if age < 18:
                    features.append("teenage")
                elif age < 30:
                    features.append("young adult")
                elif age < 50:
                    features.append("middle-aged")
                else:
                    features.append("elderly")
        
        if "男" in appearance:
            features.append("male")
        elif "女" in appearance:
            features.append("female")
        
        # 发型
        if "黑发" in appearance or "黑色" in appearance:
            features.append("black hair")
        if "短发" in appearance or "短寸" in appearance:
            features.append("short hair")
        elif "长发" in appearance:
            features.append("long hair")
        
        # 脸型
        if "国字脸" in appearance:
            features.append("square jaw")
        elif "瓜子脸" in appearance:
            features.append("oval face")
        
        # 眼睛
        if "大眼" in appearance:
            features.append("large eyes")
        if "眼镜" in appearance or "黑框眼镜" in appearance:
            features.append("wearing glasses, black frame glasses")
        
        return features
    
    @staticmethod
    def _extract_clothing_features(clothing: str) -> List[str]:
        """提取服装特征"""
        features = []
        
        # 颜色
        color_map = {
            "白色": "white",
            "黑色": "black",
            "蓝色": "blue",
            "红色": "red"
        }
        for chinese, english in color_map.items():
            if chinese in clothing:
                features.append(english)
        
        # 服装类型
        clothing_map = {
            "校服": "school uniform",
            "衬衫": "shirt",
            "T恤": "t-shirt",
            "裤": "pants",
            "背包": "backpack",
            "双肩包": "backpack"
        }
        for chinese, english in clothing_map.items():
            if chinese in clothing:
                features.append(english)
        
        return features
    
    @staticmethod
    def _extract_expression_features(expression: str) -> List[str]:
        """提取表情特征"""
        features = []
        
        expression_map = {
            ("疲惫", "疲倦"): "tired expression, exhausted face",
            ("微笑",): "smiling, gentle smile",
            ("严肃",): "serious expression",
            ("空洞", "迷茫"): "empty eyes, blank stare",
            ("紧闭", "嘴"): "lips pressed together",
            ("皱眉", "眉头"): "frowning, furrowed brows"
        }
        
        for keywords, english in expression_map.items():
            if any(kw in expression for kw in keywords):
                features.append(english)
        
        return features
    
    @staticmethod
    def _extract_posture_features(posture: str) -> List[str]:
        """提取姿势特征"""
        features = []
        
        if "站" in posture:
            features.append("standing")
        elif "坐" in posture:
            features.append("sitting")
        elif "蹲" in posture:
            features.append("crouching")
        
        if "前倾" in posture:
            features.append("leaning forward")
        if "耷拉" in posture or "下垂" in posture:
            features.append("slouched shoulders")
        
        return features
    
    @staticmethod
    def _extract_consistency_details(char_data: Dict, existing_parts: List[str]) -> List[str]:
        """从一致性数据中提取详细信息"""
        char_parts = []
        
        # 如果没有现有部分，添加基本标记
        if not existing_parts:
            char_parts.append("1person")
        
        # 外貌
        appearance = char_data.get('appearance', {})
        face = appearance.get('face', {})
        hair = appearance.get('hair', {})
        body = appearance.get('body', {})
        
        # 性别
        gender = char_data.get('gender', '')
        existing_text = ' '.join(existing_parts)
        if gender and 'male' not in existing_text and 'female' not in existing_text:
            if "男" in gender:
                char_parts.insert(0, "male")
            elif "女" in gender:
                char_parts.insert(0, "female")
        
        # 年龄
        age = char_data.get('age', '')
        if age and 'teenage' not in existing_text:
            if "16" in str(age) or "17" in str(age) or "18" in str(age):
                char_parts.append("teenage, high school student")
            elif "20" in str(age) or "25" in str(age):
                char_parts.append("young adult")
        
        # 发型
        if hair:
            hair_desc = []
            color = hair.get('color', '')
            length = hair.get('length', '')
            style = hair.get('style', '')
            
            if "黑" in color:
                hair_desc.append("black")
            elif "棕" in color:
                hair_desc.append("brown")
            elif "金" in color:
                hair_desc.append("blonde")
            
            if "短" in length:
                hair_desc.append("short")
            elif "长" in length:
                hair_desc.append("long")
            elif "中" in length:
                hair_desc.append("medium")
            
            if "直" in style:
                hair_desc.append("straight")
            elif "卷" in style:
                hair_desc.append("wavy")
            
            if hair_desc:
                hair_desc.append("hair")
                char_parts.append(" ".join(hair_desc))
        
        # 脸部特征
        if face:
            if face.get('skin_tone'):
                skin = face['skin_tone']
                if "白" in skin or "苍白" in skin:
                    char_parts.append("pale skin, fair skin")
                elif "小麦" in skin:
                    char_parts.append("tan skin, healthy complexion")
            
            if face.get('face_shape'):
                face_shape = face['face_shape']
                if "国字" in face_shape:
                    char_parts.append("square face, strong jawline")
                elif "瓜子" in face_shape or "鹅蛋" in face_shape:
                    char_parts.append("oval face, delicate features")
            
            if face.get('eyes'):
                char_parts.append(face['eyes'])
        
        # 体型
        if body.get('body_type'):
            body_type = body['body_type']
            if "苗条" in body_type or "瘦" in body_type:
                char_parts.append("slim build, slender body")
            elif "健壮" in body_type or "强壮" in body_type:
                char_parts.append("athletic build, fit body")
            elif "中等" in body_type:
                char_parts.append("average build")
        
        if body.get('height'):
            height = body['height']
            if "高" in height:
                char_parts.append("tall")
            elif "矮" in height:
                char_parts.append("short")
        
        # 服装（从一致性设定）
        outfits = char_data.get('outfits', {})
        outfit = outfits.get('default', {})
        
        if outfit:
            outfit_parts = []
            if outfit.get('top'):
                top = outfit['top']
                if "白" in top:
                    outfit_parts.append("white")
                if "衬衫" in top:
                    outfit_parts.append("dress shirt")
                elif "T恤" in top:
                    outfit_parts.append("t-shirt")
                elif "校服" in top:
                    outfit_parts.append("school uniform shirt")
            
            if outfit.get('bottom'):
                bottom = outfit['bottom']
                if "裤" in bottom:
                    outfit_parts.append("pants")
                if "牛仔" in bottom:
                    outfit_parts.append("jeans")
                if "校服" in bottom:
                    outfit_parts.append("school uniform pants")
            
            if outfit.get('shoes'):
                shoes = outfit['shoes']
                if "运动鞋" in shoes:
                    outfit_parts.append("sneakers")
                elif "皮鞋" in shoes:
                    outfit_parts.append("dress shoes")
            
            if outfit_parts:
                char_parts.append("wearing " + ", ".join(outfit_parts))
        
        return char_parts
    
    @staticmethod
    def _build_scene_parts(shot: Dict) -> List[str]:
        """构建场景描述"""
        scene_parts = []
        
        # 视觉描述
        visual_desc = shot.get('visual_description', '')
        if visual_desc:
            scene_parts.extend(SDPromptBuilder._extract_visual_elements(visual_desc))
            scene_parts.append("detailed environment")
        
        # 光线
        lighting = shot.get('lighting', '')
        if lighting:
            scene_parts.extend(SDPromptBuilder._extract_lighting_features(lighting))
        
        # 氛围
        atmosphere = shot.get('atmosphere', '')
        if atmosphere:
            scene_parts.extend(SDPromptBuilder._extract_atmosphere_features(atmosphere))
        
        return scene_parts
    
    @staticmethod
    def _extract_visual_elements(visual_desc: str) -> List[str]:
        """提取视觉元素"""
        elements = []
        
        location_map = {
            "教室": "classroom",
            "办公室": "office",
            "阳光": "sunlight, natural lighting",
            "太阳": "sunlight, natural lighting",
            "窗": "window",
            "桌": "desk",
            "清晨": "morning",
            "早晨": "morning",
            "黄昏": "evening, sunset",
            "傍晚": "evening, sunset"
        }
        
        for keyword, english in location_map.items():
            if keyword in visual_desc:
                elements.append(english)
        
        return elements
    
    @staticmethod
    def _extract_lighting_features(lighting: str) -> List[str]:
        """提取光线特征"""
        features = []
        
        lighting_map = {
            "自然光": "natural light",
            "柔和": "soft lighting",
            "高对比": "high contrast",
            "暖色": "warm color temperature",
            "warm": "warm color temperature"
        }
        
        for keyword, english in lighting_map.items():
            if keyword in lighting:
                features.append(english)
        
        return features
    
    @staticmethod
    def _extract_atmosphere_features(atmosphere: str) -> List[str]:
        """提取氛围特征"""
        features = []
        
        atmosphere_map = {
            ("寂静", "安静"): "quiet atmosphere, serene",
            ("紧张",): "tense atmosphere",
            ("温馨",): "warm atmosphere, cozy"
        }
        
        for keywords, english in atmosphere_map.items():
            if any(kw in atmosphere for kw in keywords):
                features.append(english)
        
        return features
    
    @staticmethod
    def _build_action_parts(shot: Dict) -> List[str]:
        """构建动作描述"""
        action_parts = []
        
        action = shot.get('action', '')
        if action:
            action_map = {
                ("推门", "打开"): "opening door",
                ("走", "迈步"): "walking",
                ("站立", "站在"): "standing",
                ("坐",): "sitting",
                ("看", "注视"): "looking",
                ("微笑",): "smiling"
            }
            
            for keywords, english in action_map.items():
                if any(kw in action for kw in keywords):
                    action_parts.append(english)
        
        return action_parts
    
    @staticmethod
    def _build_shot_type(shot: Dict) -> str:
        """构建镜头类型"""
        shot_type = shot.get('shot_type', '')
        
        if "Wide" in shot_type or "全景" in shot_type:
            return "wide shot, full scene"
        elif "Medium" in shot_type or "中景" in shot_type:
            return "medium shot"
        elif "Close" in shot_type or "特写" in shot_type:
            return "close-up shot"
        
        return ""
    
    @staticmethod
    def _add_location_details(prompt: str, shot: Dict) -> str:
        """添加位置详情"""
        location = shot.get('location', '')
        if not location:
            return prompt
        
        location_map = {
            "教室": ", classroom interior, desks and chairs, school setting",
            "办公室": ", office interior, desk, professional environment",
            "走廊": ", hallway, corridor",
            "操场": ", outdoor, playground"
        }
        
        for keyword, addition in location_map.items():
            if keyword in location:
                prompt += addition
                break
        
        if "outdoor" in location.lower():
            prompt += ", outdoor, playground"
        
        return prompt
    
    @staticmethod
    def _add_continuity_details(prompt: str, shot: Dict) -> str:
        """添加连贯性详情"""
        continuity = shot.get('continuity', '')
        scene_id = shot.get('scene_id', '')
        
        if continuity or scene_id:
            prompt += ", story scene, narrative sequence, cinematic storytelling"
        
        return prompt
    
    @staticmethod
    def _add_emotion_details(prompt: str, shot: Dict) -> str:
        """添加情绪详情"""
        emotion = shot.get('emotion', '')
        if not emotion:
            return prompt
        
        emotion_map = {
            ("孤独", "lonely"): ", lonely atmosphere, solitary",
            ("疲惫", "tired"): ", tired expression, exhausted",
            ("紧张",): ", tense mood",
            ("开心", "happy"): ", happy, cheerful"
        }
        
        emotion_lower = emotion.lower()
        for keywords, addition in emotion_map.items():
            if any(kw in emotion or kw in emotion_lower for kw in keywords):
                prompt += addition
        
        return prompt
    
    @staticmethod
    def build_negative_prompt(shot: Dict) -> str:
        """构建SD负面提示词 - 加强人物一致性约束
        
        Args:
            shot: 分镜字典
            
        Returns:
            str: 构建的负面提示词
        """
        negative_tags = [
            # 质量相关
            "low quality", "worst quality", "normal quality", "lowres", "blurry", "fuzzy",
            "bad anatomy", "bad hands", "bad proportions", "bad perspective",
            "ugly", "deformed", "disfigured", "mutation", "mutated",
            
            # 人物一致性相关（加强）
            "multiple people", "crowd", "different person", "changing appearance",
            "inconsistent clothing", "inconsistent hair", "inconsistent face",
            "different hairstyle", "hair color change", "different outfit",
            "face inconsistency", "character inconsistency",
            "multiple identities", "changing features",
            
            # 构图相关
            "cropped", "cut off", "out of frame", "watermark", "signature", "text",
            "username", "logo", "copyright", "border",
            
            # 风格相关
            "cartoon", "anime", "illustration", "painting", "drawing",
            "3d render", "cg", "unrealistic", "artistic style",
            
            # 其他
            "duplicate", "repeating", "extra limbs", "missing limbs",
            "bad lighting", "overexposed", "underexposed",
            "distorted", "weird", "strange"
        ]
        
        # 如果是人物镜头，添加更多限制
        if shot.get('characters'):
            negative_tags.extend([
                "multiple heads", "two faces", "deformed face",
                "asymmetric eyes", "cross-eyed", "wrong anatomy",
                "extra fingers", "missing fingers", "fused fingers",
                "different face", "face change"
            ])
        
        return ", ".join(negative_tags)


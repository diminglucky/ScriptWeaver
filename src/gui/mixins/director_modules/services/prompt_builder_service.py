"""
提示词构建服务 - 负责为不同API生成优化的提示词
"""

from typing import Dict, List, Optional, Tuple

try:
    from ..models.shot import Shot
    from ..models.character import Character
except ImportError:
    from models.shot import Shot
    from models.character import Character


class PromptBuilderService:
    """提示词构建服务"""
    
    def __init__(self):
        self.character_seed_map = {}  # 人物种子映射
        self.consistency_mode = "medium"  # 一致性模式: strong, medium, weak
    
    def build_shot_prompt(
        self,
        shot: Shot,
        api_type: str,
        characters_data: Dict[str, Character] = None
    ) -> Tuple[str, str]:
        """
        为分镜构建提示词
        
        Args:
            shot: 分镜对象
            api_type: API类型 ('sd', 'openai', 'hunyuan')
            characters_data: 人物数据字典
        
        Returns:
            (正向提示词, 负向提示词)
        """
        if api_type == "sd":
            return self._build_sd_prompt(shot, characters_data)
        elif api_type == "openai":
            return self._build_openai_prompt(shot, characters_data)
        elif api_type == "hunyuan":
            return self._build_hunyuan_prompt(shot, characters_data)
        else:
            return self._build_generic_prompt(shot, characters_data)
    
    def _build_sd_prompt(
        self,
        shot: Shot,
        characters_data: Optional[Dict[str, Character]] = None
    ) -> Tuple[str, str]:
        """构建Stable Diffusion提示词（标签风格）"""
        
        # === 质量标签 ===
        quality_tags = [
            "masterpiece", "best quality", "ultra detailed", "8k",
            "photorealistic", "cinematic lighting", "professional photography",
            "sharp focus", "highly detailed", "intricate details",
            "character consistency", "consistent character design", "same person"
        ]
        
        # === 人物描述 ===
        character_tags = []
        for char_name in shot.characters:
            char_tags = self._build_character_tags_for_sd(
                char_name,
                shot.get_character_detail(char_name),
                characters_data.get(char_name) if characters_data else None
            )
            if char_tags:
                character_tags.extend(char_tags)
        
        # === 场景描述 ===
        scene_tags = self._build_scene_tags_for_sd(shot)
        
        # === 动作和表情 ===
        action_tags = self._build_action_tags_for_sd(shot)
        
        # === 镜头类型 ===
        shot_type_tags = self._build_shot_type_tags_for_sd(shot)
        
        # === 组合提示词 ===
        positive_prompt = ", ".join(
            quality_tags +
            character_tags +
            action_tags +
            scene_tags +
            shot_type_tags
        )
        
        # === 负向提示词 ===
        negative_prompt = self._build_sd_negative_prompt(shot)
        
        return positive_prompt, negative_prompt
    
    def _build_character_tags_for_sd(
        self,
        char_name: str,
        detail: Optional[object],
        character: Optional[Character]
    ) -> List[str]:
        """为SD构建人物标签"""
        tags = ["1person"]
        
        # 从character对象获取详细信息
        if character:
            # 性别和年龄
            if character.gender:
                tags.append("male" if character.gender == "男" else "female")
            if character.age:
                tags.append(self._parse_age_to_english(character.age))
            
            # 外观特征
            appearance = character.appearance
            if appearance:
                # 发型
                hair = appearance.hair
                if hair:
                    hair_tags = []
                    if hair.color:
                        hair_tags.append(self._translate_color(hair.color))
                    if hair.length:
                        hair_tags.append(self._translate_hair_length(hair.length))
                    if hair.style:
                        hair_tags.append(self._translate_hair_style(hair.style))
                    if hair_tags:
                        hair_tags.append("hair")
                        tags.append(" ".join(hair_tags))
                
                # 面部特征
                face = appearance.face
                if face:
                    if face.skin_tone:
                        tags.append(self._translate_skin_tone(face.skin_tone))
                    if face.eyes:
                        tags.append(face.eyes)
                    if face.face_shape:
                        tags.append(self._translate_face_shape(face.face_shape))
                
                # 体型
                body = appearance.body
                if body:
                    if body.body_type:
                        tags.append(self._translate_body_type(body.body_type))
            
            # 服装
            outfit = character.get_default_outfit()
            if outfit:
                outfit_tags = []
                if outfit.top:
                    outfit_tags.append(outfit.top)
                if outfit.bottom:
                    outfit_tags.append(outfit.bottom)
                if outfit_tags:
                    tags.append("wearing " + ", ".join(outfit_tags))
        
        # 从分镜detail获取特定信息
        if detail and hasattr(detail, 'expression') and detail.expression:
            tags.append(self._translate_expression(detail.expression))
        
        return tags
    
    def _build_scene_tags_for_sd(self, shot: Shot) -> List[str]:
        """构建场景标签"""
        tags = []
        
        # 环境
        visual_desc = shot.visual_description
        if "教室" in visual_desc:
            tags.extend(["classroom", "school interior"])
        if "办公室" in visual_desc:
            tags.extend(["office", "professional environment"])
        if "阳光" in visual_desc or "太阳" in visual_desc:
            tags.extend(["sunlight", "natural lighting"])
        if "窗" in visual_desc:
            tags.append("window")
        
        # 光线
        if shot.lighting:
            if "自然光" in shot.lighting:
                tags.append("natural light")
            if "柔和" in shot.lighting:
                tags.append("soft lighting")
        
        # 氛围
        if shot.atmosphere:
            if "寂静" in shot.atmosphere or "安静" in shot.atmosphere:
                tags.extend(["quiet atmosphere", "serene"])
            if "紧张" in shot.atmosphere:
                tags.append("tense atmosphere")
        
        return tags
    
    def _build_action_tags_for_sd(self, shot: Shot) -> List[str]:
        """构建动作标签"""
        tags = []
        
        action = shot.action
        if "走" in action or "迈步" in action:
            tags.append("walking")
        if "站" in action:
            tags.append("standing")
        if "坐" in action:
            tags.append("sitting")
        if "看" in action or "注视" in action:
            tags.append("looking")
        
        return tags
    
    def _build_shot_type_tags_for_sd(self, shot: Shot) -> List[str]:
        """构建镜头类型标签"""
        shot_type = shot.shot_type
        
        if "Wide" in shot_type or "全景" in shot_type:
            return ["wide shot", "full scene"]
        elif "Medium" in shot_type or "中景" in shot_type:
            return ["medium shot"]
        elif "Close" in shot_type or "特写" in shot_type:
            return ["close-up shot"]
        
        return []
    
    def _build_sd_negative_prompt(self, shot: Shot) -> str:
        """构建SD负向提示词"""
        negative_tags = [
            # 质量相关
            "low quality", "worst quality", "normal quality", "lowres",
            "blurry", "fuzzy", "out of focus",
            "bad anatomy", "bad hands", "bad proportions",
            "ugly", "deformed", "disfigured", "mutation",
            
            # 人物一致性相关
            "multiple people", "crowd", "different person",
            "changing appearance", "inconsistent clothing",
            "inconsistent hair", "inconsistent face",
            "character inconsistency",
            
            # 构图相关
            "cropped", "cut off", "out of frame",
            "watermark", "signature", "text", "username",
            
            # 风格相关
            "cartoon", "anime", "illustration", "painting",
            "unrealistic", "artistic style"
        ]
        
        # 如果有人物，添加更多限制
        if shot.characters:
            negative_tags.extend([
                "multiple heads", "two faces", "deformed face",
                "extra fingers", "missing fingers", "different face"
            ])
        
        return ", ".join(negative_tags)
    
    def _build_openai_prompt(
        self,
        shot: Shot,
        characters_data: Optional[Dict[str, Character]] = None
    ) -> Tuple[str, str]:
        """构建OpenAI提示词（自然语言风格）"""
        parts = []
        
        # 场景描述
        if shot.visual_description:
            parts.append(shot.visual_description)
        
        # 人物描述
        char_descriptions = []
        for char_name in shot.characters:
            char_desc = self._build_character_description_natural(
                char_name,
                shot.get_character_detail(char_name),
                characters_data.get(char_name) if characters_data else None
            )
            if char_desc:
                char_descriptions.append(char_desc)
        
        if char_descriptions:
            parts.append("人物：" + "，".join(char_descriptions))
        
        # 动作
        if shot.action:
            parts.append(f"动作：{shot.action}")
        
        # 氛围
        if shot.atmosphere:
            parts.append(f"氛围：{shot.atmosphere}")
        
        # 镜头类型
        if shot.shot_type:
            parts.append(f"镜头：{shot.shot_type}")
        
        prompt = "，".join(parts)
        
        return prompt, ""  # OpenAI不需要负向提示词
    
    def _build_hunyuan_prompt(
        self,
        shot: Shot,
        characters_data: Optional[Dict[str, Character]] = None
    ) -> Tuple[str, str]:
        """构建腾讯混元提示词（中文自然语言）"""
        # 混元偏好详细的中文描述
        return self._build_openai_prompt(shot, characters_data)
    
    def _build_generic_prompt(
        self,
        shot: Shot,
        characters_data: Optional[Dict[str, Character]] = None
    ) -> Tuple[str, str]:
        """构建通用提示词"""
        return self._build_openai_prompt(shot, characters_data)
    
    def _build_character_description_natural(
        self,
        char_name: str,
        detail: Optional[object],
        character: Optional[Character]
    ) -> str:
        """构建人物的自然语言描述"""
        parts = [char_name]
        
        if character:
            # 基本信息
            if character.age and character.gender:
                parts.append(f"{character.age}{character.gender}")
            
            # 外观
            appearance = character.appearance
            if appearance:
                hair = appearance.hair
                if hair and hair.color and hair.style:
                    parts.append(f"{hair.color}{hair.style}")
            
            # 服装
            outfit = character.get_default_outfit()
            if outfit and outfit.top:
                parts.append(f"穿着{outfit.top}")
        
        # 分镜中的特定信息
        if detail and hasattr(detail, 'expression') and detail.expression:
            parts.append(f"表情{detail.expression}")
        
        return "，".join(parts)
    
    # === 翻译辅助方法 ===
    
    def _parse_age_to_english(self, age: str) -> str:
        """解析年龄为英文"""
        try:
            age_num = int(''.join(filter(str.isdigit, age)))
            if age_num < 18:
                return "teenage"
            elif age_num < 30:
                return "young adult"
            elif age_num < 50:
                return "middle-aged"
            else:
                return "elderly"
        except:
            return "adult"
    
    def _translate_color(self, color: str) -> str:
        """翻译颜色"""
        color_map = {
            "黑色": "black",
            "棕色": "brown",
            "金色": "blonde",
            "红色": "red",
            "白色": "white"
        }
        return color_map.get(color, color)
    
    def _translate_hair_length(self, length: str) -> str:
        """翻译发长"""
        length_map = {
            "短发": "short",
            "中长发": "medium length",
            "长发": "long"
        }
        return length_map.get(length, length)
    
    def _translate_hair_style(self, style: str) -> str:
        """翻译发型"""
        style_map = {
            "直发": "straight",
            "卷发": "curly",
            "波浪": "wavy"
        }
        return style_map.get(style, style)
    
    def _translate_skin_tone(self, skin_tone: str) -> str:
        """翻译肤色"""
        skin_map = {
            "白皙": "fair skin",
            "自然": "natural skin",
            "小麦色": "tan skin",
            "健康": "healthy complexion"
        }
        return skin_map.get(skin_tone, "natural skin")
    
    def _translate_face_shape(self, face_shape: str) -> str:
        """翻译脸型"""
        face_map = {
            "国字脸": "square face",
            "瓜子脸": "oval face",
            "圆脸": "round face",
            "鹅蛋脸": "oval face"
        }
        return face_map.get(face_shape, face_shape)
    
    def _translate_body_type(self, body_type: str) -> str:
        """翻译体型"""
        body_map = {
            "苗条": "slim build",
            "健壮": "athletic build",
            "匀称": "average build",
            "丰满": "curvy"
        }
        return body_map.get(body_type, body_type)
    
    def _translate_expression(self, expression: str) -> str:
        """翻译表情"""
        expr_map = {
            "微笑": "smiling",
            "严肃": "serious expression",
            "疲惫": "tired expression",
            "开心": "happy",
            "悲伤": "sad",
            "愤怒": "angry"
        }
        return expr_map.get(expression, expression)
    
    def generate_character_seed(self, character_name: str) -> int:
        """为人物生成固定种子"""
        if character_name not in self.character_seed_map:
            # 🔥 修复：使用md5而不是hash，确保一致性和跨平台稳定性
            import hashlib
            seed = int(hashlib.md5(character_name.encode('utf-8')).hexdigest()[:8], 16) % 1000000
            self.character_seed_map[character_name] = seed
        return self.character_seed_map[character_name]
    
    def set_consistency_mode(self, mode: str):
        """
        设置人物一致性模式
        
        Args:
            mode: 'strong' | 'medium' | 'weak'
        """
        if mode in ["strong", "medium", "weak"]:
            self.consistency_mode = mode
    
    def get_denoising_strength(self, shot: Shot) -> float:
        """
        根据镜头类型和一致性模式返回合适的去噪强度
        
        Args:
            shot: 分镜对象
        
        Returns:
            去噪强度值 (0.0-1.0)
        """
        # 基础值（按一致性模式）
        base_strength = {
            "strong": 0.45,   # 强一致：紧锁外貌，几乎不变
            "medium": 0.55,   # 中等一致：保持外貌，允许动作/表情变化（默认）
            "weak": 0.68      # 弱一致：允许较大变化，适合风格化或夸张表现
        }.get(self.consistency_mode, 0.55)
        
        # 根据镜头类型微调
        shot_type_lower = shot.shot_type.lower() if shot.shot_type else ""
        
        # 特写/大特写：降低去噪（锁脸更紧）
        if any(kw in shot_type_lower for kw in ["特写", "close", "ecu", "cu", "extreme close"]):
            return max(0.40, base_strength - 0.08)
        
        # 近景/中近景：标准值
        elif any(kw in shot_type_lower for kw in ["近景", "中近", "medium close", "mcu", "ms"]):
            return base_strength
        
        # 中景：略微提高（允许更多变化）
        elif any(kw in shot_type_lower for kw in ["中景", "medium shot", "mid"]):
            return min(0.75, base_strength + 0.05)
        
        # 全景/远景：提高去噪（人物细节不重要，环境为主）
        elif any(kw in shot_type_lower for kw in ["全景", "远景", "long shot", "wide", "ls", "vls"]):
            return min(0.78, base_strength + 0.12)
        
        # 默认返回基础值
        return base_strength


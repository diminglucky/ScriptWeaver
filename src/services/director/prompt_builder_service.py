"""
提示词构建服务 - 负责为不同API生成优化的提示词
"""

from typing import Dict, List, Optional, Tuple

try:
    from src.gui.mixins.director_modules.models.shot import Shot
    from src.gui.mixins.director_modules.models.character import Character
except ImportError:
    from ...gui.mixins.director_modules.models.shot import Shot
    from ...gui.mixins.director_modules.models.character import Character


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
        
        # === 质量标签（优化：更精准的真实感描述）===
        quality_tags = [
            # 核心质量标签（必须）
            "masterpiece", "best quality", "ultra detailed",
            # 真实感标签（关键）
            "photorealistic", "realistic", "RAW photo", "real photo",
            # 相机和光照（提升真实感）
            "professional DSLR photography", "natural lighting", "cinematic lighting",
            # 细节标签
            "sharp focus", "highly detailed", "detailed face", "detailed skin texture",
            # 人物一致性（重要）
            "consistent character", "same person", "character consistency"
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
        
        # === 场景描述（完整描述，优先使用）===
        scene_description_full = self._build_scene_description_for_sd(shot)
        
        # === 场景标签（补充信息）===
        scene_tags = self._build_scene_tags_for_sd(shot)
        
        # === 动作和表情 ===
        action_tags = self._build_action_tags_for_sd(shot)
        
        # === 镜头类型 ===
        shot_type_tags = self._build_shot_type_tags_for_sd(shot)
        
        # === 组合提示词 ===
        # SD提示词格式：完整场景描述 + 质量标签 + 人物标签 + 动作标签 + 场景标签 + 镜头标签
        prompt_parts = []
        
        # 1. 完整场景描述（如果有，放在最前面，用自然语言）
        if scene_description_full:
            prompt_parts.append(scene_description_full)
        
        # 2. 质量标签（必须）
        if quality_tags:
            prompt_parts.append(", ".join(quality_tags))
        
        # 3. 人物标签
        if character_tags:
            prompt_parts.append(", ".join(character_tags))
        
        # 4. 动作标签
        if action_tags:
            prompt_parts.append(", ".join(action_tags))
        
        # 5. 场景补充标签（如果场景描述中没有包含）
        if scene_tags:
            prompt_parts.append(", ".join(scene_tags))
        
        # 6. 镜头类型标签
        if shot_type_tags:
            prompt_parts.append(", ".join(shot_type_tags))
        
        # 组合所有部分，用逗号分隔（SD标准格式）
        positive_prompt = ", ".join(prompt_parts)
        
        # === 负向提示词 ===
        negative_prompt = self._build_sd_negative_prompt(shot)
        
        return positive_prompt, negative_prompt
    
    def _build_character_tags_for_sd(
        self,
        char_name: str,
        detail: Optional[object],
        character: Optional[Character]
    ) -> List[str]:
        """为SD构建人物标签（优化：更精确的人物描述）"""
        tags = []
        
        # === 人物数量（必须明确）===
        tags.append("1person")
        tags.append("solo")  # 强调单人
        
        # === 优先从分镜detail获取详细信息（因为它包含了当前分镜的具体描述）===
        if detail:
            # 如果detail是字典类型（从shot.character_details来的）
            if isinstance(detail, dict):
                # 外貌
                if 'appearance' in detail and detail['appearance']:
                    appearance_keywords = self._extract_keywords_from_chinese(detail['appearance'])
                    tags.extend(appearance_keywords)
                
                # 发型
                if 'hair' in detail and detail['hair']:
                    hair_keywords = self._extract_keywords_from_chinese(detail['hair'])
                    tags.extend(hair_keywords)
                
                # 服装
                if 'clothing' in detail and detail['clothing']:
                    clothing_keywords = self._extract_keywords_from_chinese(detail['clothing'])
                    tags.extend(clothing_keywords)
                
                # 表情
                if 'expression' in detail and detail['expression']:
                    expression_keywords = self._extract_keywords_from_chinese(detail['expression'])
                    tags.extend(expression_keywords)
                
                # 姿势
                if 'posture' in detail and detail['posture']:
                    posture_keywords = self._extract_keywords_from_chinese(detail['posture'])
                    tags.extend(posture_keywords)
                
                # 动作
                if 'action' in detail and detail['action']:
                    action_keywords = self._extract_keywords_from_chinese(detail['action'])
                    tags.extend(action_keywords)
            
            # 如果detail是对象类型（ShotCharacterDetail）
            elif hasattr(detail, 'appearance'):
                if detail.appearance:
                    appearance_keywords = self._extract_keywords_from_chinese(detail.appearance)
                    tags.extend(appearance_keywords)
                
                if hasattr(detail, 'clothing') and detail.clothing:
                    clothing_keywords = self._extract_keywords_from_chinese(detail.clothing)
                    tags.extend(clothing_keywords)
                
                if hasattr(detail, 'expression') and detail.expression:
                    expression_keywords = self._extract_keywords_from_chinese(detail.expression)
                    tags.extend(expression_keywords)
                
                if hasattr(detail, 'posture') and detail.posture:
                    posture_keywords = self._extract_keywords_from_chinese(detail.posture)
                    tags.extend(posture_keywords)
                
                if hasattr(detail, 'action') and detail.action:
                    action_keywords = self._extract_keywords_from_chinese(detail.action)
                    tags.extend(action_keywords)
        
        # === 从character对象获取补充信息（如果有）===
        if character:
            # === 性别和年龄（基础信息）===
            if character.gender:
                gender_tag = "1man" if character.gender == "男" else "1woman"
                if gender_tag not in tags:
                    tags.append(gender_tag)
            if character.age:
                age_tag = self._parse_age_to_english(character.age)
                if age_tag not in tags:
                    tags.append(age_tag)
            
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
        
        # 去重
        tags = list(dict.fromkeys(tags))
        
        return tags
    
    def _build_scene_description_for_sd(self, shot: Shot) -> str:
        """构建完整的场景描述（用于SD提示词）"""
        # === 优先使用 jimeng_prompt（专门为图像生成优化的描述）===
        scene_description = ""
        if hasattr(shot, 'jimeng_prompt') and shot.jimeng_prompt:
            scene_description = shot.jimeng_prompt.strip()
        elif shot.visual_description:
            scene_description = shot.visual_description.strip()
        elif shot.scene_description:
            scene_description = shot.scene_description.strip()
        
        if not scene_description:
            return ""
        
        # === 检查是否包含中文字符 ===
        has_chinese = any('\u4e00' <= char <= '\u9fff' for char in scene_description)
        
        if has_chinese:
            # 中文描述，需要翻译
            try:
                from src.utils.prompt_translator import PromptTranslator
                translated = PromptTranslator.translate_chinese_to_english(
                    scene_description,
                    characters=shot.characters if shot.characters else None,
                    character_details=shot.character_details if hasattr(shot, 'character_details') else None
                )
                if translated:
                    return translated.strip()
            except Exception as e:
                # 翻译失败，使用关键词提取作为备用方案
                print(f"⚠️ 场景描述翻译失败，使用关键词提取: {e}")
            
            # 翻译失败或未配置翻译API，使用关键词提取
            keywords = self._extract_keywords_from_chinese(scene_description)
            if keywords:
                return ", ".join(keywords)
            
            # 如果关键词提取也失败，至少返回一些基本信息
            return "detailed scene"
        else:
            # 已经是英文，直接使用
            return scene_description.strip()
        
        return ""
    
    def _build_scene_tags_for_sd(self, shot: Shot) -> List[str]:
        """构建场景标签（补充信息）"""
        tags = []
        
        # === 补充信息：位置、时间 ===
        if shot.location:
            # 先尝试直接翻译
            location_en = self._translate_location(shot.location)
            if location_en != shot.location:  # 如果翻译成功（不等于原文）
                if location_en not in tags:
                    tags.append(location_en)
            else:
                # 翻译失败，使用关键词提取
                location_keywords = self._extract_keywords_from_chinese(shot.location)
                for kw in location_keywords:
                    if kw not in tags:
                        tags.append(kw)
        
        if shot.time:
            time_en = self._translate_time(shot.time)
            if time_en != shot.time:  # 如果翻译成功
                if time_en not in tags:
                    tags.append(time_en)
            else:
                # 翻译失败，使用关键词提取
                time_keywords = self._extract_keywords_from_chinese(shot.time)
                for kw in time_keywords:
                    if kw not in tags:
                        tags.append(kw)
        
        # === 光线（如果场景描述中没有包含）===
        if shot.lighting:
            lighting_tags = self._translate_lighting(shot.lighting)
            if lighting_tags:
                for tag in lighting_tags:
                    if tag not in tags:
                        tags.append(tag)
            else:
                # 使用关键词提取
                lighting_keywords = self._extract_keywords_from_chinese(shot.lighting)
                for kw in lighting_keywords:
                    if kw not in tags:
                        tags.append(kw)
        
        # === 氛围（如果场景描述中没有包含）===
        if shot.atmosphere:
            atmosphere_tags = self._translate_atmosphere(shot.atmosphere)
            if atmosphere_tags:
                for tag in atmosphere_tags:
                    if tag not in tags:
                        tags.append(tag)
            else:
                # 使用关键词提取
                atmosphere_keywords = self._extract_keywords_from_chinese(shot.atmosphere)
                for kw in atmosphere_keywords:
                    if kw not in tags:
                        tags.append(kw)
        
        return tags
    
    def _extract_keywords_from_chinese(self, text: str) -> List[str]:
        """从中文文本中提取关键词并翻译（增强版）"""
        keywords = []
        
        # === 地点关键词 ===
        location_map = {
            "教室": "classroom", "学校": "school", "办公室": "office",
            "走廊": "hallway", "操场": "playground", "图书馆": "library",
            "宿舍": "dormitory", "食堂": "cafeteria", "实验室": "laboratory",
            "卧室": "bedroom", "客厅": "living room", "厨房": "kitchen",
            "浴室": "bathroom", "阳台": "balcony", "楼梯": "staircase",
            "街道": "street", "公园": "park", "咖啡馆": "cafe",
            "餐厅": "restaurant", "商店": "shop", "超市": "supermarket",
            "医院": "hospital", "车站": "station", "机场": "airport"
        }
        for cn, en in location_map.items():
            if cn in text:
                keywords.append(en)
        
        # === 室内/室外 ===
        if "室内" in text or "房间" in text or "屋内" in text:
            keywords.append("indoor")
        if "室外" in text or "户外" in text:
            keywords.append("outdoor")
        
        # === 家具和物品 ===
        furniture_map = {
            "床": "bed", "桌": "desk", "椅": "chair", "沙发": "sofa",
            "书架": "bookshelf", "柜": "cabinet", "窗": "window",
            "门": "door", "墙": "wall", "地板": "floor",
            "天花板": "ceiling", "灯": "lamp", "电视": "TV",
            "电脑": "computer", "手机": "phone", "书": "book"
        }
        for cn, en in furniture_map.items():
            if cn in text:
                keywords.append(en)
        
        # === 时间关键词 ===
        time_map = {
            "清晨": "early morning", "早晨": "morning", "中午": "noon",
            "下午": "afternoon", "傍晚": "evening", "夜晚": "night",
            "深夜": "late night", "黄昏": "dusk", "黎明": "dawn"
        }
        for cn, en in time_map.items():
            if cn in text:
                keywords.append(en)
        
        # === 光线关键词 ===
        lighting_map = {
            "阳光": "sunlight", "太阳": "sunlight", "月光": "moonlight",
            "明亮": "bright lighting", "昏暗": "dim lighting",
            "柔和": "soft lighting", "刺眼": "harsh lighting",
            "自然光": "natural lighting", "灯光": "artificial lighting",
            "冷光": "cold lighting", "暖光": "warm lighting",
            "逆光": "backlight", "侧光": "side lighting"
        }
        for cn, en in lighting_map.items():
            if cn in text:
                keywords.append(en)
        
        # === 颜色关键词 ===
        color_map = {
            "红色": "red", "蓝色": "blue", "绿色": "green",
            "黄色": "yellow", "白色": "white", "黑色": "black",
            "灰色": "gray", "粉色": "pink", "紫色": "purple",
            "橙色": "orange", "棕色": "brown", "金色": "golden"
        }
        for cn, en in color_map.items():
            if cn in text:
                keywords.append(en)
        
        # === 人物动作 ===
        action_map = {
            "站": "standing", "坐": "sitting", "躺": "lying",
            "走": "walking", "跑": "running", "跳": "jumping",
            "看": "looking", "注视": "gazing", "盯": "staring",
            "微笑": "smiling", "哭": "crying", "笑": "laughing",
            "思考": "thinking", "睡": "sleeping", "吃": "eating",
            "喝": "drinking", "读": "reading", "写": "writing",
            "打电话": "on phone", "玩手机": "using phone"
        }
        for cn, en in action_map.items():
            if cn in text:
                keywords.append(en)
        
        # === 表情和情绪 ===
        emotion_map = {
            "疲惫": "tired", "疲倦": "exhausted", "困": "sleepy",
            "开心": "happy", "快乐": "joyful", "兴奋": "excited",
            "悲伤": "sad", "难过": "sorrowful", "哭泣": "crying",
            "生气": "angry", "愤怒": "furious", "烦躁": "irritated",
            "紧张": "nervous", "焦虑": "anxious", "担心": "worried",
            "平静": "calm", "放松": "relaxed", "安静": "peaceful",
            "惊讶": "surprised", "震惊": "shocked", "困惑": "confused",
            "失望": "disappointed", "无奈": "helpless", "绝望": "desperate"
        }
        for cn, en in emotion_map.items():
            if cn in text:
                keywords.append(en)
        
        # === 服装 ===
        clothing_map = {
            "校服": "school uniform", "睡衣": "pajamas", "T恤": "t-shirt",
            "衬衫": "shirt", "裤": "pants", "裙": "skirt",
            "外套": "jacket", "大衣": "coat", "毛衣": "sweater",
            "连衣裙": "dress", "西装": "suit", "运动服": "sportswear"
        }
        for cn, en in clothing_map.items():
            if cn in text:
                keywords.append(en)
        
        # === 天气和氛围 ===
        atmosphere_map = {
            "晴": "sunny", "阴": "cloudy", "雨": "rainy",
            "雪": "snowy", "雾": "foggy", "风": "windy",
            "温馨": "cozy", "冷清": "desolate", "热闹": "lively",
            "安静": "quiet", "嘈杂": "noisy", "寂静": "silent"
        }
        for cn, en in atmosphere_map.items():
            if cn in text:
                keywords.append(en)
        
        # === 人物特征 ===
        feature_map = {
            "长发": "long hair", "短发": "short hair", "黑发": "black hair",
            "金发": "blonde hair", "棕发": "brown hair", "白发": "white hair",
            "眼镜": "wearing glasses", "帽子": "wearing hat",
            "背包": "backpack", "包": "bag", "手表": "watch"
        }
        for cn, en in feature_map.items():
            if cn in text:
                keywords.append(en)
        
        # 去重
        keywords = list(dict.fromkeys(keywords))
        
        return keywords
    
    def _translate_location(self, location: str) -> str:
        """翻译地点"""
        location_map = {
            "教室": "classroom",
            "办公室": "office",
            "走廊": "hallway",
            "操场": "playground",
            "图书馆": "library",
            "宿舍": "dormitory"
        }
        return location_map.get(location, location)
    
    def _translate_time(self, time: str) -> str:
        """翻译时间"""
        time_map = {
            "清晨": "early morning",
            "早晨": "morning",
            "中午": "noon",
            "下午": "afternoon",
            "傍晚": "evening",
            "夜晚": "night"
        }
        return time_map.get(time, time)
    
    def _translate_lighting(self, lighting: str) -> List[str]:
        """翻译光线描述"""
        tags = []
        if "自然光" in lighting or "自然" in lighting:
            tags.append("natural lighting")
        if "阳光" in lighting or "太阳" in lighting:
            tags.append("sunlight")
        if "柔和" in lighting:
            tags.append("soft lighting")
        if "明亮" in lighting:
            tags.append("bright lighting")
        if "昏暗" in lighting:
            tags.append("dim lighting")
        return tags
    
    def _translate_atmosphere(self, atmosphere: str) -> List[str]:
        """翻译氛围描述"""
        tags = []
        if "寂静" in atmosphere or "安静" in atmosphere:
            tags.extend(["quiet atmosphere", "serene"])
        if "紧张" in atmosphere:
            tags.append("tense atmosphere")
        if "温馨" in atmosphere:
            tags.append("warm atmosphere")
        if "悲伤" in atmosphere:
            tags.append("melancholic atmosphere")
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
        """构建SD负向提示词（优化：更强力排除不需要的风格）"""
        negative_tags = [
            # === 质量相关（必须排除）===
            "low quality", "worst quality", "normal quality", "lowres", "low resolution",
            "blurry", "fuzzy", "out of focus", "soft focus", "bokeh blur",
            "jpeg artifacts", "compression artifacts", "noise", "grainy",
            
            # === 解剖结构问题（重要）===
            "bad anatomy", "bad proportions", "anatomically incorrect",
            "bad hands", "bad fingers", "extra fingers", "missing fingers", "fused fingers",
            "bad feet", "bad legs", "bad arms",
            "deformed", "disfigured", "mutation", "mutated",
            "ugly", "gross", "disgusting",
            
            # === 人物一致性（关键）===
            "multiple people", "two people", "three people", "crowd", "group",
            "different person", "different character", "another person",
            "changing appearance", "inconsistent appearance",
            "inconsistent clothing", "different clothes",
            "inconsistent hair", "different hair", "changing hair",
            "inconsistent face", "different face", "changing face",
            "character inconsistency", "person inconsistency",
            
            # === 构图问题 ===
            "cropped", "cut off", "out of frame", "truncated",
            "watermark", "signature", "text", "username", "logo", "watermarked",
            "border", "frame", "split screen", "collage",
            
            # === 强力排除非真实风格（最重要）===
            # 卡通/动漫风格
            "cartoon", "anime", "manga", "comic", "animated",
            "illustration", "drawing", "sketch", "painting", "artwork",
            "cel shading", "toon shading", "stylized",
            # 3D渲染风格
            "3d render", "3d rendering", "3d", "rendered", "cg", "computer graphics",
            "CGI", "digital art", "game art", "video game", "game engine",
            "unreal engine", "unity", "blender render",
            # 材质问题
            "plastic", "plastic skin", "doll", "toy", "mannequin", "wax figure",
            "artificial", "fake", "synthetic", "unrealistic",
            # 其他艺术风格
            "oil painting", "watercolor", "pencil drawing", "charcoal",
            "abstract", "surreal", "fantasy art"
        ]
        
        # 如果有人物，添加更多人物相关限制
        if shot.characters:
            negative_tags.extend([
                "multiple heads", "two heads", "two faces", "multiple faces",
                "deformed face", "distorted face", "asymmetric face",
                "extra limbs", "missing limbs",
                "different facial features", "changing facial features"
            ])
        
        return ", ".join(negative_tags)
    
    def _build_openai_prompt(
        self,
        shot: Shot,
        characters_data: Optional[Dict[str, Character]] = None
    ) -> Tuple[str, str]:
        """构建OpenAI/DALL-E 3提示词（针对照片真实感优化，使用英文）"""
        
        # ==================== 第一部分：照片风格声明（必须在最前面）==================== #
        photo_style = "A photorealistic photograph"
        
        # 镜头类型
        shot_type_desc = ""
        if shot.shot_type:
            shot_type_map = {
                "特写镜头": "close-up shot",
                "特写": "close-up shot",
                "Close-up": "close-up shot",
                "中景镜头": "medium shot", 
                "中景": "medium shot",
                "Medium Shot": "medium shot",
                "全景镜头": "wide shot",
                "全景": "wide shot",
                "Wide Shot": "wide shot",
                "远景镜头": "long shot",
                "远景": "long shot",
                "大全景": "extreme wide shot"
            }
            shot_type_en = shot_type_map.get(shot.shot_type, "medium shot")
            photo_style = f"A photorealistic {shot_type_en}"
            shot_type_desc = ", professional photography"
        
        # ==================== 第二部分：场景描述（使用关键词提取）==================== #
        scene_keywords = []
        
        # 从 jimeng_prompt 或 visual_description 提取关键词
        scene_text = ""
        if hasattr(shot, 'jimeng_prompt') and shot.jimeng_prompt:
            scene_text = shot.jimeng_prompt
        elif shot.visual_description:
            scene_text = shot.visual_description
        
        if scene_text:
            # 使用关键词提取（与SD相同的逻辑）
            scene_keywords = self._extract_keywords_from_chinese(scene_text)
        
        # 补充位置和时间信息
        if shot.location:
            location_keywords = self._extract_keywords_from_chinese(shot.location)
            scene_keywords.extend(location_keywords)
        
        # ==================== 第三部分：人物描述 ==================== #
        character_keywords = []
        if shot.characters:
            for char_name in shot.characters:
                detail = shot.get_character_detail(char_name)
                if detail:
                    # 从人物详情提取关键词
                    if isinstance(detail, dict):
                        for field in ['appearance', 'hair', 'clothing', 'expression', 'posture', 'action']:
                            if field in detail and detail[field]:
                                char_keywords = self._extract_keywords_from_chinese(detail[field])
                                character_keywords.extend(char_keywords)
                    elif hasattr(detail, 'appearance'):
                        if detail.appearance:
                            character_keywords.extend(self._extract_keywords_from_chinese(detail.appearance))
                        if hasattr(detail, 'clothing') and detail.clothing:
                            character_keywords.extend(self._extract_keywords_from_chinese(detail.clothing))
                        if hasattr(detail, 'expression') and detail.expression:
                            character_keywords.extend(self._extract_keywords_from_chinese(detail.expression))
        
        # ==================== 第四部分：光线和氛围 ==================== #
        atmosphere_keywords = []
        
        if shot.lighting:
            lighting_keywords = self._extract_keywords_from_chinese(shot.lighting)
            atmosphere_keywords.extend(lighting_keywords)
        
        if shot.atmosphere:
            atmos_keywords = self._extract_keywords_from_chinese(shot.atmosphere)
            atmosphere_keywords.extend(atmos_keywords)
        
        # ==================== 第五部分：动作 ==================== #
        action_keywords = []
        if shot.action:
            action_keywords = self._extract_keywords_from_chinese(shot.action)
        
        # ==================== 组合最终提示词（全英文）==================== #
        prompt_parts = [photo_style + shot_type_desc]
        
        # 去重所有关键词
        all_keywords = []
        all_keywords.extend(scene_keywords)
        all_keywords.extend(character_keywords)
        all_keywords.extend(action_keywords)
        all_keywords.extend(atmosphere_keywords)
        
        # 去重
        unique_keywords = list(dict.fromkeys(all_keywords))
        
        if unique_keywords:
            # 构建自然语言描述
            keywords_str = ", ".join(unique_keywords[:30])  # 限制关键词数量，避免太长
            prompt_parts.append(f"of {keywords_str}")
        
        # 添加质量强调
        quality_emphasis = "professional DSLR photography, natural lighting, realistic details, photojournalistic style"
        prompt_parts.append(quality_emphasis)
        
        final_prompt = ", ".join(prompt_parts)
        
        # 清理格式
        final_prompt = final_prompt.replace("，，", "，").replace("。，", "，").replace("。。", "。")
        
        return final_prompt, ""  # OpenAI不需要负向提示词
    
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


"""
人物生成提示词构建器
借鉴漫画项目的角色设定表生成经验
"""

from .consistency_optimizer import ConsistencyOptimizer


class CharacterPromptBuilder:
    """专业的人物生成提示词构建器"""
    
    # 视角类型定义
    VIEW_ANGLES = {
        "front": {
            "zh": ["正面", "面向镜头", "正脸", "双眼看向镜头"],
            "en": ["front view", "facing camera", "looking at camera", "direct eye contact"]
        },
        "side": {
            "zh": ["侧面", "90度侧面", "侧脸", "侧身"],
            "en": ["side view", "90 degree profile", "side profile", "lateral view"]
        },
        "back": {
            "zh": ["背面", "背对镜头", "背影", "从背后看"],
            "en": ["back view", "facing away", "rear view", "from behind"]
        },
        "three-quarter": {
            "zh": ["斜侧面", "四分之三视角", "微侧脸", "45度角"],
            "en": ["three-quarter view", "45 degree angle", "slightly turned", "angled view"]
        }
    }
    
    # 表情类型定义
    EXPRESSIONS = {
        "neutral": {
            "zh": ["中性表情", "平静", "面无表情"],
            "en": ["neutral expression", "calm", "blank face"]
        },
        "happy": {
            "zh": ["开心", "微笑", "愉悦", "笑容"],
            "en": ["happy", "smiling", "joyful", "cheerful"]
        },
        "sad": {
            "zh": ["悲伤", "难过", "沮丧", "忧愁"],
            "en": ["sad", "sorrowful", "downcast", "melancholy"]
        },
        "angry": {
            "zh": ["愤怒", "生气", "怒目", "愤恨"],
            "en": ["angry", "furious", "mad", "enraged"]
        },
        "surprised": {
            "zh": ["惊讶", "吃惊", "震惊", "瞪大眼"],
            "en": ["surprised", "shocked", "astonished", "wide-eyed"]
        },
        "fear": {
            "zh": ["恐惧", "害怕", "惊恐", "畏惧"],
            "en": ["fearful", "scared", "frightened", "terrified"]
        }
    }
    
    # 服装/造型变体定义
    OUTFIT_VARIANTS = {
        "formal": {
            "zh": ["正装", "西装", "礼服", "正式服装", "领带", "皮鞋", "优雅"],
            "en": ["formal wear", "suit", "formal dress", "tie", "dress shoes", "elegant"]
        },
        "casual": {
            "zh": ["休闲装", "T恤", "牛仔裤", "运动鞋", "轻松", "日常"],
            "en": ["casual wear", "t-shirt", "jeans", "sneakers", "relaxed", "everyday"]
        },
        "sport": {
            "zh": ["运动装", "运动服", "运动鞋", "健身装", "活力", "运动风"],
            "en": ["sportswear", "athletic clothing", "sports shoes", "gym wear", "energetic"]
        },
        "traditional": {
            "zh": ["古装", "传统服饰", "汉服", "旗袍", "长袍", "古典"],
            "en": ["traditional clothing", "hanfu", "cheongsam", "classical dress", "traditional"]
        },
        "artistic": {
            "zh": ["艺术风", "文艺装", "波西米亚", "独特", "个性", "创意"],
            "en": ["artistic style", "bohemian", "unique", "creative", "distinctive"]
        },
        "professional": {
            "zh": ["职业装", "职业套装", "衬衫", "西裤", "专业", "干练"],
            "en": ["business attire", "professional outfit", "shirt", "dress pants", "competent"]
        }
    }
    
    # 构图类型定义
    COMPOSITION_TYPES = {
        "full_body": {
            "zh": {
                "basic": ["全身照", "从头到脚", "完整身体", "站立姿态"],
                "emphasis": ["双腿双脚可见", "鞋子可见", "完整服装", "绝对不是半身照", "必须包含腿和脚"],
                "background": ["纯色背景", "简洁背景", "无干扰背景"]
            },
            "en": {
                "basic": ["full body shot", "head to feet", "complete figure", "standing pose"],
                "emphasis": ["legs and feet visible", "shoes visible", "complete outfit", "absolutely not half body", "must include legs and feet"],
                "background": ["plain background", "simple background", "clean background"]
            }
        },
        "upper_body": {
            "zh": {
                "basic": ["上半身", "半身照", "肩膀以上"],
                "emphasis": ["清晰五官", "面部特征明显"],
                "background": ["纯色背景", "简洁背景"]
            },
            "en": {
                "basic": ["upper body", "half body shot", "from shoulders up"],
                "emphasis": ["clear facial features", "distinct face"],
                "background": ["plain background", "simple background"]
            }
        },
        "portrait": {
            "zh": {
                "basic": ["肖像", "头像", "脸部特写", "面部"],
                "emphasis": ["五官清晰", "面部细节"],
                "background": ["纯色背景"]
            },
            "en": {
                "basic": ["portrait", "headshot", "face closeup", "facial"],
                "emphasis": ["clear facial features", "facial details"],
                "background": ["plain background"]
            }
        }
    }
    
    @staticmethod
    def build_character_photo_prompt(
        description: str,
        style: str = "写实照片",
        view_angle: str = "front",
        expression: str = "neutral",
        composition: str = "full_body",
        extra_details: str = "",
        language: str = "zh",
        default_nationality: str = "chinese",
        variant: str = "",
        variant_mode: str = "none",
        consistency_level: str = "medium",
        batch_type: str = "none"
    ) -> str:
        """
        构建单张人物照片的提示词
        
        Args:
            description: 人物描述
            style: 图片风格
            view_angle: 视角 (front/side/back/three-quarter)
            expression: 表情 (neutral/happy/sad/angry/surprised/fear)
            composition: 构图类型 (full_body/upper_body/portrait)
            extra_details: 额外细节
            language: 语言 (zh/en)
            default_nationality: 默认国籍 (chinese/none)
            variant: 服装变体（预设类型或自定义描述）
            variant_mode: 变体模式 (none/preset/custom)
            consistency_level: 一致性级别 (none/low/medium/high)
            batch_type: 批量类型 (none/angle/expression/variant)
        
        Returns:
            完整的提示词
        """
        # 应用一致性优化
        if consistency_level != "none":
            description = ConsistencyOptimizer.build_consistency_prompt(
                description=description,
                language=language,
                emphasis_level=consistency_level
            )
            
            # 如果是批量生成，添加批量优化
            if batch_type != "none":
                description = ConsistencyOptimizer.optimize_for_batch_generation(
                    description=description,
                    batch_type=batch_type,
                    language=language
                )
        
        prompt_parts = []
        
        # 1. 构图要求（最高优先级）
        comp_dict = CharacterPromptBuilder.COMPOSITION_TYPES.get(composition, CharacterPromptBuilder.COMPOSITION_TYPES["full_body"])
        comp_data = comp_dict.get(language, comp_dict["zh"])
        
        # 基础构图
        prompt_parts.extend(comp_data["basic"])
        
        # 强调重点
        if composition == "full_body":
            prompt_parts.extend(comp_data["emphasis"])
        
        # 2. 视角要求
        view_dict = CharacterPromptBuilder.VIEW_ANGLES.get(view_angle, CharacterPromptBuilder.VIEW_ANGLES["front"])
        prompt_parts.extend(view_dict.get(language, view_dict["zh"])[:2])  # 取前2个视角描述
        
        # 3. 表情要求
        expr_dict = CharacterPromptBuilder.EXPRESSIONS.get(expression, CharacterPromptBuilder.EXPRESSIONS["neutral"])
        prompt_parts.extend(expr_dict.get(language, expr_dict["zh"])[:2])  # 取前2个表情描述
        
        # 4. 国籍/种族特征（如果需要）
        if default_nationality == "chinese" and language == "zh":
            if not any(keyword in description for keyword in ["外国", "欧美", "美国", "英国", "法国", "德国", "日本", "韩国", "俄罗斯", "非洲", "印度", "阿拉伯", "American", "European", "Western", "Japanese", "Korean"]):
                prompt_parts.extend(["中国人", "东亚面孔"])
        elif default_nationality == "chinese" and language == "en":
            if not any(keyword in description for keyword in ["American", "European", "Western", "Japanese", "Korean", "Russian", "African", "Indian", "Arab"]):
                prompt_parts.extend(["Chinese person", "East Asian features"])
        
        # 5. 人物描述（核心）
        desc_limit = 150 if language == "zh" else 200
        if len(description) > desc_limit:
            prompt_parts.append(description[:desc_limit])
        else:
            prompt_parts.append(description)
        
        # 6. 服装/造型变体
        if variant_mode == "preset" and variant:
            # 使用预设变体
            variant_dict = CharacterPromptBuilder.OUTFIT_VARIANTS.get(variant, {})
            if variant_dict:
                variant_words = variant_dict.get(language, variant_dict.get("zh", []))
                prompt_parts.extend(variant_words[:3])  # 取前3个变体描述词
        elif variant_mode == "custom" and variant:
            # 使用自定义变体描述
            if not variant.startswith("例如"):
                variant_limit = 60
                if len(variant) > variant_limit:
                    prompt_parts.append(variant[:variant_limit])
                else:
                    prompt_parts.append(variant)
        
        # 7. 额外细节
        if extra_details:
            extra_limit = 80
            if len(extra_details) > extra_limit:
                prompt_parts.append(extra_details[:extra_limit])
            else:
                prompt_parts.append(extra_details)
        
        # 8. 背景要求
        prompt_parts.extend(comp_data["background"])
        
        # 9. 画质要求
        if language == "zh":
            prompt_parts.extend(["高清", "细节清晰", "专业摄影"])
        else:
            prompt_parts.extend(["high quality", "detailed", "professional photography"])
        
        # 组合提示词
        separator = "，" if language == "zh" else ", "
        return separator.join(prompt_parts)
    
    @staticmethod
    def build_character_sheet_prompt(
        description: str,
        style: str = "写实照片",
        language: str = "zh"
    ) -> dict:
        """
        构建角色设定表的多视角提示词
        
        Args:
            description: 人物描述
            style: 图片风格
            language: 语言
        
        Returns:
            包含多个视角和表情的提示词字典
        """
        prompts = {}
        
        # 1. 三视图
        for angle_key, angle_name in [("front", "正面"), ("side", "侧面"), ("back", "背面")]:
            prompts[f"view_{angle_key}"] = {
                "name_zh": f"{angle_name}视图",
                "name_en": f"{angle_key.title()} View",
                "prompt": CharacterPromptBuilder.build_character_photo_prompt(
                    description=description,
                    style=style,
                    view_angle=angle_key,
                    expression="neutral",
                    composition="full_body",
                    language=language
                ),
                "type": "view"
            }
        
        # 2. 表情图
        for expr_key, expr_name_zh in [
            ("neutral", "中性"),
            ("happy", "开心"),
            ("sad", "悲伤"),
            ("angry", "愤怒"),
            ("surprised", "惊讶")
        ]:
            expr_dict = CharacterPromptBuilder.EXPRESSIONS[expr_key]
            expr_name_en = expr_dict["en"][0]
            
            prompts[f"expr_{expr_key}"] = {
                "name_zh": f"{expr_name_zh}表情",
                "name_en": f"{expr_name_en.title()} Expression",
                "prompt": CharacterPromptBuilder.build_character_photo_prompt(
                    description=description,
                    style=style,
                    view_angle="front",  # 表情图用正面
                    expression=expr_key,
                    composition="portrait",  # 表情图用肖像构图
                    language=language
                ),
                "type": "expression"
            }
        
        return prompts

    @staticmethod
    def extract_appearance_only(text: str) -> str:
        """Keep appearance-focused fragments and remove scene/action noise."""
        raw = (text or "").strip()
        if not raw:
            return ""

        # Split by common Chinese/English punctuation and line breaks.
        parts = []
        for chunk in raw.replace("\r", "\n").split("\n"):
            for seg in chunk.replace("。", ",").replace("；", ",").replace(";", ",").split(","):
                seg = seg.strip()
                if seg:
                    parts.append(seg)

        appearance_keywords = (
            "外貌", "长相", "五官", "脸", "面部", "眼", "眉", "鼻", "唇", "肤", "发", "发型", "发色",
            "身高", "体型", "体态", "服装", "穿着", "衣", "鞋", "配饰", "疤", "痣", "纹身",
            "appearance", "face", "facial", "eye", "nose", "lip", "hair", "skin", "height",
            "body", "outfit", "clothing", "wearing", "accessory", "scar", "tattoo",
        )
        noise_keywords = (
            "背景", "场景", "镜头", "构图", "光线", "动作", "情节", "故事", "对白", "心理",
            "background", "scene", "camera", "shot", "lighting", "action", "story", "dialogue",
        )

        kept = []
        for seg in parts:
            lower_seg = seg.lower()
            if any(k in seg for k in noise_keywords) or any(k in lower_seg for k in noise_keywords):
                continue
            if any(k in seg for k in appearance_keywords) or any(k in lower_seg for k in appearance_keywords):
                kept.append(seg)

        # Fallback: if heuristic filtered too much, keep original condensed text.
        if not kept:
            kept = parts[:8] if parts else [raw]

        return "，".join(kept)[:800]

    @staticmethod
    def sanitize_for_image_safety(prompt: str, language: str = "en") -> str:
        """Reduce prompt policy risk while keeping core appearance details."""
        text = (prompt or "").strip()
        if not text:
            return ""

        replacements = {
            "未成年": "成年人",
            "儿童": "成年人",
            "小孩": "成年人",
            "nude": "fully clothed",
            "nudity": "fully clothed",
            "sexy": "elegant",
            "gore": "",
            "blood": "",
            "corpse": "",
        }
        for src, dst in replacements.items():
            text = text.replace(src, dst)

        # Collapse repeated separators/spaces.
        while "，，" in text:
            text = text.replace("，，", "，")
        text = " ".join(text.split())
        return text.strip("，, ")

    @staticmethod
    def build_retry_prompt(
        description: str,
        style: str = "ID photo",
        view_angle: str = "front",
        expression: str = "neutral",
        composition: str = "upper_body",
        language: str = "en",
    ) -> str:
        """Build a safer fallback prompt for retry after policy rejection."""
        base_desc = CharacterPromptBuilder.extract_appearance_only(description)
        prompt = CharacterPromptBuilder.build_character_photo_prompt(
            description=base_desc,
            style=style,
            view_angle=view_angle,
            expression=expression,
            composition=composition,
            language=language,
            extra_details="",
            default_nationality="chinese",
            variant="",
            variant_mode="none",
            consistency_level="medium",
            batch_type="none",
        )
        prompt = CharacterPromptBuilder.sanitize_for_image_safety(prompt, language=language)
        api_type = "hunyuan" if language == "zh" else "openai"
        return CharacterPromptBuilder.optimize_for_api(prompt, api_type)
    
    @staticmethod
    def optimize_for_api(prompt: str, api_type: str, max_length: int = None) -> str:
        """
        针对不同API优化提示词
        
        Args:
            prompt: 原始提示词
            api_type: API类型 (hunyuan/openai/dalle)
            max_length: 最大长度限制
        
        Returns:
            优化后的提示词
        """
        if api_type == "hunyuan":
            # 腾讯混元限制256字符
            max_len = max_length or 256
            if len(prompt) > max_len:
                # 保留核心部分：构图+描述前段
                parts = prompt.split("，")
                core_parts = []
                current_length = 0
                
                for part in parts:
                    if current_length + len(part) + 1 <= max_len:
                        core_parts.append(part)
                        current_length += len(part) + 1
                    else:
                        break
                
                return "，".join(core_parts)
            return prompt
        
        elif api_type in ["openai", "dalle"]:
            # OpenAI DALL-E 3 支持更长的提示词，但建议1000字符内
            max_len = max_length or 1000
            if len(prompt) > max_len:
                return prompt[:max_len]
            return prompt
        
        else:
            # 其他API，通用处理
            max_len = max_length or 500
            if len(prompt) > max_len:
                return prompt[:max_len]
            return prompt


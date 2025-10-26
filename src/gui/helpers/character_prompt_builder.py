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
        batch_type: str = "none",
        api_type: str = "openai"
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
            api_type: API类型 (sd/openai/hunyuan) - 决定提示词风格
        
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
        
        # ===== 根据API类型选择提示词风格 =====
        if api_type == "sd":
            # Stable Diffusion: 标签式提示词（逗号分隔关键词）
            return CharacterPromptBuilder._build_sd_style_prompt(
                description=description,
                view_angle=view_angle,
                expression=expression,
                composition=composition,
                extra_details=extra_details,
                default_nationality=default_nationality,
                variant=variant,
                variant_mode=variant_mode,
                language=language
            )
        else:
            # OpenAI/Hunyuan/其他API: 自然语言提示词（完整句子）
            return CharacterPromptBuilder._build_natural_language_prompt(
                description=description,
                view_angle=view_angle,
                expression=expression,
                composition=composition,
                extra_details=extra_details,
                default_nationality=default_nationality,
                variant=variant,
                variant_mode=variant_mode,
                language=language
            )
    
    @staticmethod
    def _build_sd_style_prompt(
        description: str,
        view_angle: str,
        expression: str,
        composition: str,
        extra_details: str,
        default_nationality: str,
        variant: str,
        variant_mode: str,
        language: str
    ) -> str:
        """
        构建SD风格的标签式提示词
        SD要求：全英文、简洁关键词、逗号分隔
        """
        tags = []
        
        # === 1. 质量标签（最前面）===
        tags.extend(["masterpiece", "best quality", "ultra detailed", "8k"])
        
        # === 2. 人数和性别（必须明确）===
        # 检测性别（更全面的关键词）
        is_male = any(kw in description for kw in [
            "男", "male", "man", "boy", "先生", "他", "男性", "男孩", "男人",
            "男生", "小伙", "帅哥", "大叔", "老伯", "爷爷"
        ])
        is_female = any(kw in description for kw in [
            "女", "female", "woman", "girl", "lady", "她", "女性", "女孩", "女人",
            "女生", "姑娘", "美女", "阿姨", "奶奶", "少女"
        ])
        
        # 检测年龄（更细致的分类）
        is_child = any(kw in description for kw in [
            "小孩", "child", "kid", "儿童", "小学生", "幼儿", "孩童",
            "5岁", "6岁", "7岁", "8岁", "9岁", "10岁", "11岁", "12岁"
        ])
        is_teen = any(kw in description for kw in [
            "青少年", "teenager", "teen", "高中生", "初中生", "少年",
            "13岁", "14岁", "15岁", "16岁", "17岁", "18岁", "19岁"
        ])
        is_young = any(kw in description for kw in [
            "年轻", "young", "青年", "20", "25", "30", "大学生", "职场新人"
        ])
        is_middle = any(kw in description for kw in [
            "中年", "middle-aged", "40", "50", "不惑", "中年人"
        ])
        is_old = any(kw in description for kw in [
            "老", "elderly", "老人", "60", "70", "80", "花甲", "古稀", "耄耋"
        ])
        
        # 组合性别+年龄标签（更精确）
        if is_male:
            if is_child:
                tags.extend(["1boy", "young boy", "male child"])
            elif is_teen:
                tags.extend(["1boy", "teenage boy", "male teenager"])
            elif is_young:
                tags.extend(["1man", "young man", "adult male"])
            elif is_middle:
                tags.extend(["1man", "middle-aged man", "mature male"])
            elif is_old:
                tags.extend(["1man", "elderly man", "old man"])
            else:
                tags.extend(["1man", "adult male"])  # 默认成年男性
        elif is_female:
            if is_child:
                tags.extend(["1girl", "young girl", "female child"])
            elif is_teen:
                tags.extend(["1girl", "teenage girl", "female teenager"])
            elif is_young:
                tags.extend(["1woman", "young woman", "adult female"])
            elif is_middle:
                tags.extend(["1woman", "middle-aged woman", "mature female"])
            elif is_old:
                tags.extend(["1woman", "elderly woman", "old woman"])
            else:
                tags.extend(["1woman", "adult female"])  # 默认成年女性
        else:
            # 无法判断性别，从名字推测
            if any(kw in description for kw in ["王", "李", "张", "刘", "陈", "杨", "黄", "赵", "周", "吴"]):
                tags.extend(["1person", "Chinese person"])
            else:
                tags.append("1person")
        
        tags.append("solo")  # 单人（强调）
        
        # === 3. 种族特征 ===
        if default_nationality == "chinese":
            if not any(kw in description for kw in ["欧美", "美国", "American", "European", "Western"]):
                tags.extend(["Chinese", "East Asian", "asian"])
        
        # === 4. 发型（从描述中提取，更全面）===
        hair_keywords = {
            # 颜色
            "黑发": "black hair", "黑色头发": "black hair",
            "棕发": "brown hair", "棕色头发": "brown hair",
            "金发": "blonde hair", "金色头发": "blonde hair", "黄发": "blonde hair",
            "红发": "red hair", "红色头发": "red hair",
            "白发": "white hair", "白色头发": "white hair", "银发": "silver hair",
            "灰发": "gray hair", "蓝发": "blue hair", "紫发": "purple hair",
            # 长度
            "短发": "short hair", "中长发": "medium hair", "中长": "medium hair",
            "长发": "long hair", "齐肩": "shoulder-length hair",
            "及腰": "waist-length hair", "超长": "very long hair",
            # 质感和样式
            "直发": "straight hair", "卷发": "curly hair", "波浪": "wavy hair",
            "自然卷": "naturally curly", "微卷": "slightly wavy",
            # 发型
            "马尾": "ponytail", "高马尾": "high ponytail",
            "双马尾": "twin tails", "麻花辫": "braided hair", "编发": "braided",
            "丸子头": "bun", "发髻": "bun", "齐刘海": "blunt bangs",
            "斜刘海": "side-swept bangs", "中分": "center parting",
            "侧分": "side parting", "碎发": "messy hair", "蓬松": "voluminous hair"
        }
        hair_found = False
        for cn_key, en_tag in hair_keywords.items():
            if cn_key in description:
                if en_tag not in tags:
                    tags.append(en_tag)
                    hair_found = True
        
        # 如果没有明确发型，添加默认
        if not hair_found:
            if is_male:
                tags.extend(["black hair", "short hair"])
            else:
                tags.extend(["black hair", "long hair"])
        
        # === 5. 服装（从描述中提取，更详细）===
        clothing_keywords = {
            # 上装
            "衬衫": "shirt", "白衬衫": "white shirt",
            "T恤": "t-shirt", "短袖": "short sleeves",
            "长袖": "long sleeves", "毛衣": "sweater",
            "卫衣": "hoodie", "外套": "jacket",
            "西装": "suit", "西装外套": "suit jacket",
            "夹克": "jacket", "风衣": "trench coat",
            # 下装
            "裤子": "pants", "长裤": "long pants",
            "牛仔裤": "jeans", "西裤": "dress pants",
            "短裤": "shorts", "裙子": "skirt",
            "连衣裙": "dress", "短裙": "mini skirt",
            "长裙": "long skirt", "百褶裙": "pleated skirt",
            # 整套
            "制服": "uniform", "校服": "school uniform",
            "运动服": "sportswear", "正装": "formal wear",
            "休闲装": "casual wear", "职业装": "business attire",
            # 颜色
            "黑色": "black", "白色": "white", "灰色": "gray",
            "红色": "red", "蓝色": "blue", "绿色": "green",
            "黄色": "yellow", "紫色": "purple", "粉色": "pink",
            "棕色": "brown", "米色": "beige",
            # 材质和风格
            "皮革": "leather", "牛仔": "denim", "棉质": "cotton",
            "运动风": "sporty", "休闲风": "casual", "正式": "formal"
        }
        clothing_found = False
        for cn_key, en_tag in clothing_keywords.items():
            if cn_key in description:
                if en_tag not in tags:
                    tags.append(en_tag)
                    clothing_found = True
        
        # 如果没有明确服装，添加基础服装
        if not clothing_found:
            if is_male:
                tags.extend(["casual wear", "shirt", "pants"])
        else:
                tags.extend(["casual wear", "dress"])
        
        # === 6. 构图标签 ===
        if composition == "full_body":
            tags.extend(["full body", "standing", "full shot"])
        elif composition == "upper_body":
            tags.extend(["upper body", "portrait", "half body"])
        elif composition == "portrait":
            tags.extend(["portrait", "face focus", "close-up"])
        
        # === 7. 视角标签 ===
        view_map = {
            "front": "front view",
            "side": "side view",
            "back": "back view",
            "three-quarter": "three-quarter view"
        }
        if view_angle in view_map:
            tags.append(view_map[view_angle])
        
        # === 8. 表情标签 ===
        expr_map = {
            "neutral": "neutral expression",
            "happy": "smiling",
            "sad": "sad",
            "angry": "angry",
            "surprised": "surprised",
            "fear": "scared"
        }
        if expression in expr_map:
            tags.append(expr_map[expression])
        
        # === 9. 服装变体（如果有）===
        if variant_mode == "preset" and variant:
            variant_dict = CharacterPromptBuilder.OUTFIT_VARIANTS.get(variant, {})
            if variant_dict:
                variant_tags = variant_dict.get("en", [])[:3]
                tags.extend(variant_tags)
        
        # === 10. 面部特征和体型===
        body_keywords = {
            # 体型
            "瘦": "slim", "苗条": "slender", "纤细": "slim",
            "壮": "muscular", "健壮": "athletic", "强壮": "strong",
            "胖": "chubby", "微胖": "slightly chubby", "丰满": "full-figured",
            "高": "tall", "矮": "short", "中等身材": "average build",
            # 面部特征
            "圆脸": "round face", "方脸": "square face", "瓜子脸": "oval face",
            "鹅蛋脸": "oval face", "长脸": "long face",
            "大眼睛": "large eyes", "小眼睛": "small eyes",
            "双眼皮": "double eyelids", "单眼皮": "monolid",
            "高鼻梁": "high nose bridge", "塌鼻梁": "flat nose",
            "厚嘴唇": "full lips", "薄嘴唇": "thin lips",
            "浓眉": "thick eyebrows", "细眉": "thin eyebrows",
            # 皮肤
            "白皙": "fair skin", "古铜": "tan skin", "黝黑": "dark skin",
            "皮肤白": "fair skin", "皮肤黑": "dark skin",
            # 气质
            "帅气": "handsome", "英俊": "handsome", "俊朗": "handsome",
            "漂亮": "beautiful", "美丽": "beautiful", "清秀": "delicate features",
            "可爱": "cute", "甜美": "sweet", "温柔": "gentle",
            "冷峻": "stern", "严肃": "serious", "憨厚": "honest-looking"
        }
        for cn_key, en_tag in body_keywords.items():
            if cn_key in description and en_tag not in tags:
                tags.append(en_tag)
        
        # === 11. 背景 ===
        tags.extend(["simple background", "white background", "plain background"])
        
        # === 12. 光线和质量 ===
        tags.extend([
            "professional photography",
            "studio lighting",
            "sharp focus",
            "highly detailed",
            "photorealistic",
            "high resolution"
        ])
        
        # === 13. 正向强调（确保人物质量）===
        tags.extend([
            "looking at viewer",
            "centered composition",
            "clear face",
            "detailed face",
            "perfect anatomy",
            "realistic proportions"
        ])
        
        # 去重并返回
        seen = set()
        unique_tags = []
        for tag in tags:
            if tag.lower() not in seen:
                seen.add(tag.lower())
                unique_tags.append(tag)
        
        return ", ".join(unique_tags)
    
    @staticmethod
    def _build_natural_language_prompt(
        description: str,
        view_angle: str,
        expression: str,
        composition: str,
        extra_details: str,
        default_nationality: str,
        variant: str,
        variant_mode: str,
        language: str
    ) -> str:
        """构建自然语言风格的提示词（用于OpenAI/Hunyuan等API）"""
        
        # 获取视角、表情、构图的自然语言描述
        view_dict = CharacterPromptBuilder.VIEW_ANGLES.get(view_angle, CharacterPromptBuilder.VIEW_ANGLES["front"])
        view_text = view_dict.get(language, view_dict["zh"])[0]
        
        expr_dict = CharacterPromptBuilder.EXPRESSIONS.get(expression, CharacterPromptBuilder.EXPRESSIONS["neutral"])
        expr_text = expr_dict.get(language, expr_dict["zh"])[0]
        
        comp_dict = CharacterPromptBuilder.COMPOSITION_TYPES.get(composition, CharacterPromptBuilder.COMPOSITION_TYPES["full_body"])
        comp_data = comp_dict.get(language, comp_dict["zh"])
        comp_text = comp_data["basic"][0]
        
        # 构建自然语言句子
        if language == "zh":
            # 中文自然语言
            parts = [f"一张{comp_text}"]
            
            # 添加国籍
            if default_nationality == "chinese":
                if not any(kw in description for kw in ["外国", "欧美", "美国", "英国"]):
                    parts.append("中国人")
            
            # 添加人物描述
            parts.append(description[:150])
            
            # 添加表情
            if expression != "neutral":
                parts.append(f"{expr_text}")
            
            # 添加视角
            parts.append(f"{view_text}")
            
            # 添加服装变体
            if variant_mode == "preset" and variant:
                variant_dict = CharacterPromptBuilder.OUTFIT_VARIANTS.get(variant, {})
                if variant_dict:
                    variant_text = variant_dict.get(language, variant_dict.get("zh", []))[0]
                    parts.append(f"穿着{variant_text}")
            elif variant_mode == "custom" and variant:
                parts.append(variant[:60])
            
            # 添加额外细节
            if extra_details:
                parts.append(extra_details[:80])
            
            # 添加质量要求
            parts.append("高清专业摄影，细节清晰，纯色背景")
            
            return "，".join(parts)
        
        else:
            # 英文自然语言
            parts = [f"A {comp_text} photo of"]
            
            # 添加表情（在描述前）
            if expression != "neutral":
                parts.append(f"a {expr_text}")
            else:
                parts.append("a")
            
            # 添加国籍
            if default_nationality == "chinese":
                if not any(kw in description for kw in ["American", "European", "Western"]):
                    parts.append("Chinese")
            
            # 添加人物描述主体
            parts.append(description[:200])
            
            # 添加服装变体
            if variant_mode == "preset" and variant:
                variant_dict = CharacterPromptBuilder.OUTFIT_VARIANTS.get(variant, {})
                if variant_dict:
                    variant_text = variant_dict.get(language, variant_dict.get("en", []))[0]
                    parts.append(f"wearing {variant_text}")
            elif variant_mode == "custom" and variant:
                parts.append(variant[:60])
            
            # 添加视角
            parts.append(f"{view_text}")
            
            # 添加额外细节
            if extra_details:
                parts.append(extra_details[:80])
            
            # 添加质量要求
            parts.append("high quality professional photography, detailed, plain background")
            
            return " ".join(parts)
    
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
    def get_negative_prompt_for_character(api_type: str = "sd") -> str:
        """
        获取人物生成的负面提示词
        
        Args:
            api_type: API类型（主要用于SD）
        
        Returns:
            负面提示词字符串
        """
        if api_type == "sd":
            # SD需要详细的负面提示词
            negative_tags = [
                # 质量问题
                "low quality", "worst quality", "normal quality", "lowres",
                "blurry", "fuzzy", "out of focus", "jpeg artifacts",
                "compression artifacts", "watermark", "signature", "username",
                # 解剖学问题
                "bad anatomy", "bad hands", "bad fingers", "bad proportions",
                "deformed", "disfigured", "malformed", "mutated",
                "extra limbs", "extra fingers", "missing limbs", "missing fingers",
                "fused fingers", "too many fingers", "long neck", "long body",
                # 面部问题
                "ugly face", "deformed face", "bad face", "mutated face",
                "bad eyes", "crossed eyes", "uneven eyes",
                "bad teeth", "extra heads", "two heads",
                # 多人物问题（重要！）
                "multiple people", "multiple persons", "crowd", "group",
                "two people", "three people", "many people",
                "multiple boys", "multiple girls", "extra person",
                # 其他问题
                "duplicate", "cloned", "copied",
                "text", "error", "cropped", "cut off",
                "gross", "disgusting"
            ]
            return ", ".join(negative_tags)
        else:
            # 其他API通常不需要或不支持负面提示词
            return ""
    
    @staticmethod
    def optimize_for_api(prompt: str, api_type: str, max_length: int = None) -> str:
        """
        针对不同API优化提示词
        
        Args:
            prompt: 原始提示词
            api_type: API类型 (hunyuan/openai/dalle/sd)
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
        
        elif api_type == "sd":
            # Stable Diffusion优化：使用逗号分隔的关键词格式
            max_len = max_length or 500
            
            # 如果提示词中没有逗号，添加质量关键词
            if "," not in prompt:
                # 转换中文标点为英文逗号
                prompt = prompt.replace("，", ", ").replace("；", ", ")
            
            # 确保包含质量关键词
            quality_keywords = ["high quality", "detailed", "sharp", "professional"]
            has_quality = any(kw in prompt.lower() for kw in quality_keywords)
            
            if not has_quality:
                prompt = prompt.rstrip() + ", high quality, detailed, sharp, professional"
            
            # 如果过长则截断
            if len(prompt) > max_len:
                # 在最后一个逗号处截断
                truncated = prompt[:max_len]
                last_comma = truncated.rfind(',')
                if last_comma > max_len - 100:
                    prompt = truncated[:last_comma].rstrip()
                else:
                    prompt = truncated
            
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


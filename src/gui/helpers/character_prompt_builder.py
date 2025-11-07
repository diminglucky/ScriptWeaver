"""
人物生成提示词构建器
借鉴漫画项目的角色设定表生成经验
"""

import re
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
                "background": ["无背景", "透明背景", "纯色背景"]
            },
            "en": {
                "basic": ["full body shot", "head to feet", "complete figure", "standing pose"],
                "emphasis": ["legs and feet visible", "shoes visible", "complete outfit", "absolutely not half body", "must include legs and feet"],
                "background": ["no background", "transparent background", "plain background"]
            }
        },
        "upper_body": {
            "zh": {
                "basic": ["上半身", "半身照", "肩膀以上"],
                "emphasis": ["清晰五官", "面部特征明显"],
                "background": ["无背景", "透明背景", "纯色背景"]
            },
            "en": {
                "basic": ["upper body", "half body shot", "from shoulders up"],
                "emphasis": ["clear facial features", "distinct face"],
                "background": ["no background", "transparent background", "plain background"]
            }
        },
        "portrait": {
            "zh": {
                "basic": ["肖像", "头像", "脸部特写", "面部"],
                "emphasis": ["五官清晰", "面部细节"],
                "background": ["无背景", "透明背景", "纯色背景"]
            },
            "en": {
                "basic": ["portrait", "headshot", "face closeup", "facial"],
                "emphasis": ["clear facial features", "facial details"],
                "background": ["no background", "transparent background", "plain background"]
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
        # 验证描述有效性
        if not description or len(description.strip()) < 10:
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"人物描述太短或为空（长度：{len(description)}），使用默认描述")
            description = "一个人物"  # 默认描述，避免提示词为空
        
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
                style=style,
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
        style: str,
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
        
        # === 0. 单人约束（最优先，最高权重）===
        single_person_tags = [
            "(solo:2.0)", "(1person:2.0)", "(only one person:2.0)",  # 高权重强调单人
            "solo", "1person", "only one person", "single person",  # 多次强调
            "one person only", "one character only", "no other people"  # 额外强调
        ]
        
        # === 1. 风格和质量标签（根据style参数设置）===
        # 根据style参数添加写实风格约束，防止抽象化
        if "写实" in style or "realistic" in style.lower() or "照片" in style or "photo" in style.lower():
            # 写实照片风格：强调真实、照片质量
            quality_tags = [
                "photorealistic", "(photorealistic:1.5)",  # 照片写实，高权重
                "realistic", "(realistic:1.3)",  # 写实风格
                "professional photography", "professional photo",  # 专业摄影
                "high quality photo", "high resolution photo",  # 高质量照片
                "sharp focus", "detailed", "8k", "best quality",  # 清晰度和质量
                "realistic proportions", "anatomically correct",  # 真实比例和解剖学正确
                "natural lighting", "natural skin texture",  # 自然光线和皮肤纹理
                "realistic hair", "realistic clothing",  # 真实的头发和服装
                "no illustration", "no artwork", "no painting",  # 禁止插画和艺术作品
                "no stylized", "no abstract", "no artistic style"  # 禁止风格化和抽象化
            ]
        else:
            # 默认写实风格（即使没有明确指定）
            quality_tags = [
                "photorealistic", "(photorealistic:1.4)",  # 照片写实
                "realistic", "(realistic:1.2)",  # 写实风格
                "professional photography",  # 专业摄影
                "best quality", "high resolution", "detailed",  # 基本质量要求
                "no illustration", "no artwork", "no abstract"  # 禁止抽象化
            ]
        
        # 先添加质量标签
        tags.extend(quality_tags)
        
        # === 2. 人数和性别（必须明确，优先级顺序很重要）===
        # 检测性别（全面的关键词，覆盖各种表达方式）
        is_male = any(kw in description for kw in [
            # 儿童/青少年
            "男孩", "boy", "男生", "小子", "少年", "小伙子",
            # 成年男性
            "男", "male", "man", "men", "先生", "他", "男性", "男人", "男士",
            "小伙", "帅哥", "男子", "汉子", "青年男子", "成年男子",
            # 中年/老年男性
            "大叔", "老伯", "爷爷", "大爷", "老汉", "中年男人", "老年男人",
            "父亲", "爸爸", "爹", "公公", "祖父", "外祖父",
            # 职业/称谓（男性特征明显）
            "男老师", "男师傅", "男老板", "男经理", "男主任", "男领导"
        ])
        is_female = any(kw in description for kw in [
            # 儿童/青少年
            "女孩", "girl", "女生", "姑娘", "少女", "小女孩", "小姑娘",
            # 成年女性
            "女", "female", "woman", "women", "lady", "她", "女性", "女人", "女士",
            "美女", "女子", "青年女性", "成年女性", "年轻女性",
            # 中年/老年女性
            "阿姨", "奶奶", "大妈", "大娘", "中年女性", "老年女性", "老年女人",
            "母亲", "妈妈", "娘", "婆婆", "祖母", "外祖母",
            # 职业/称谓（女性特征明显）
            "女老师", "老板娘", "女经理", "女主任", "女领导", "女师傅"
        ])
        
        # 检测年龄（更细致的分类，支持具体年龄描述）
        # 中文数字转换字典（扩展支持更多数字）
        chinese_numbers = {
            "一": 1, "二": 2, "三": 3, "四": 4, "五": 5,
            "六": 6, "七": 7, "八": 8, "九": 9, "十": 10,
            "十一": 11, "十二": 12, "十三": 13, "十四": 14, "十五": 15,
            "十六": 16, "十七": 17, "十八": 18, "十九": 19, "二十": 20,
            "廿": 20, "廿一": 21, "廿二": 22, "廿三": 23, "廿四": 24, "廿五": 25,
            "廿六": 26, "廿七": 27, "廿八": 28, "廿九": 29,
            "三十": 30, "三十一": 31, "三十二": 32, "三十三": 33, "三十四": 34,
            "三十五": 35, "三十六": 36, "三十七": 37, "三十八": 38, "三十九": 39,
            "四十": 40, "四十一": 41, "四十二": 42, "四十三": 43, "四十四": 44,
            "四十五": 45, "四十六": 46, "四十七": 47, "四十八": 48, "四十九": 49,
            "五十": 50, "六十": 60, "七十": 70, "八十": 80, "九十": 90
        }
        
        # 提取具体年龄数字（支持阿拉伯数字和中文数字）
        age_number = None
        
        # 先尝试匹配阿拉伯数字（优先匹配具体数字，支持更多格式）
        age_patterns = [
            r'约[^\d]*(\d+)[岁多]',  # "约30岁"、"约30多岁"
            r'(\d+)[岁多]',  # "30岁"、"30多岁"
            r'(\d+)[左右]',  # "30左右"、"30岁左右"
            r'大约(\d+)',    # "大约30"
            r'(\d+)来岁',    # "30来岁"
            r'(\d+)[岁]\s*左右',  # "30岁 左右"
            r'(\d+)[岁]上下',  # "30岁上下"
            r'年龄[^\d]*(\d+)',  # "年龄30"、"年龄约30"
            r'(\d+)岁[^\d]*年纪',  # "30岁年纪"
        ]
        for pattern in age_patterns:
            match = re.search(pattern, description)
            if match:
                age_number = int(match.group(1))
                break
        
        # 如果没找到阿拉伯数字，尝试中文数字（按长度从长到短匹配，避免误匹配）
        if age_number is None:
            # 先匹配长数字（如"三十一"），再匹配短数字（如"三十"）
            sorted_cn_nums = sorted(chinese_numbers.items(), key=lambda x: len(x[0]), reverse=True)
            for cn_num, num_val in sorted_cn_nums:
                # 匹配"约三十岁"、"三十岁左右"等格式
                if ("约" + cn_num + "岁" in description or 
                    cn_num + "岁左右" in description or 
                    cn_num + "多岁" in description or
                    cn_num + "岁" in description):
                    age_number = num_val
                    break
        
        is_child = False
        is_teen = False
        is_young = False
        is_middle = False
        is_old = False
        
        if age_number:
            # 根据具体年龄数字判断（更精确的范围，30岁属于年轻）
            if age_number < 13:
                is_child = True
            elif age_number < 18:
                is_teen = True
            elif age_number < 35:  # 30岁属于年轻范围
                is_young = True
            elif age_number < 55:  # 中年范围调整
                is_middle = True
            else:
                is_old = True
        else:
            # 使用关键词检测（作为后备，扩展更多关键词）
            is_child = any(kw in description for kw in [
                "小孩", "child", "kid", "儿童", "小学生", "幼儿", "孩童",
                "5岁", "6岁", "7岁", "8岁", "9岁", "10岁", "11岁", "12岁",
                "幼年", "童年", "儿童时期"
            ])
            is_teen = any(kw in description for kw in [
                "青少年", "teenager", "teen", "高中生", "初中生", "少年", "少年期",
                "13岁", "14岁", "15岁", "16岁", "17岁", "18岁", "19岁",
                "青春期", "中学生"
            ])
            is_young = any(kw in description for kw in [
                "年轻", "young", "青年", "20", "25", "30", "31", "32", "33", "34",
                "三十", "大学生", "职场新人", "年轻人", "青年男女",
                "二十多岁", "三十多岁", "二十岁", "三十岁", "约三十岁", "约20", "约30",
                "二十出头", "三十出头", "青年时期", "成年初期"
            ])
            is_middle = any(kw in description for kw in [
                "中年", "middle-aged", "40", "41", "42", "43", "44", "45", "46", "47", "48", "49", "50",
                "不惑", "中年人", "中年男女", "中年时期", "四十多岁", "五十多岁"
            ])
            is_old = any(kw in description for kw in [
                "老", "elderly", "老人", "60", "70", "80", "90",
                "花甲", "古稀", "耄耋", "老年", "老年人", "老者", "长者",
                "六十多岁", "七十多岁", "八十多岁"
            ])
        
        # 组合性别+年龄标签（更精确，支持具体年龄，SD需要特别强调）
        # SD模型对性别和年龄标签的权重很高，需要放在最前面并重复强调
        gender_age_tags = []
        
        # 在性别标签前再次强调单人
        if is_male:
            if is_child:
                # 儿童男孩：强调年龄和性别
                gender_age_tags = ["1boy", "boy", "male child", "child", "young boy"]
                if age_number:
                    gender_age_tags.append(f"{age_number} years old")
                    gender_age_tags.append(f"{age_number} year old boy")
            elif is_teen:
                gender_age_tags = ["1boy", "teenage boy", "male teenager", "teenager", "teen boy"]
                if age_number:
                    gender_age_tags.append(f"{age_number} years old")
            elif is_young:
                # 年轻男性：30岁及以下都是年轻男性
                if age_number:
                    # 如果有具体年龄，使用具体年龄标签，强调成年男性
                    gender_age_tags = ["1man", f"{age_number} years old", "adult male", "man"]
                    # 30岁以下添加"young man"标签，30-34岁保持"adult male"
                    if age_number < 30:
                        gender_age_tags.insert(2, "young man")
                else:
                    # 没有具体年龄，使用通用年轻男性标签
                    gender_age_tags = ["1man", "young man", "adult male", "man"]
            elif is_middle:
                gender_age_tags = ["1man", "middle-aged man", "mature male", "man"]
            elif is_old:
                gender_age_tags = ["1man", "elderly man", "old man", "man"]
            else:
                gender_age_tags = ["1man", "adult male", "man"]  # 默认成年男性
                
            # SD特殊强调：重复性别标签防止误判，同时再次强调单人
            tags.extend(gender_age_tags)
            tags.extend(["male", "not female"])
            # 再次强调单人约束（防止生成多人）
            tags.extend(["(solo:1.8)", "(1person:1.8)", "only one person"])
            
        elif is_female:
            if is_child:
                # 儿童女孩：强调年龄和性别
                gender_age_tags = ["1girl", "girl", "female child", "child", "young girl"]
                if age_number:
                    gender_age_tags.append(f"{age_number} years old")
                    gender_age_tags.append(f"{age_number} year old girl")
            elif is_teen:
                gender_age_tags = ["1girl", "teenage girl", "female teenager", "teenager", "teen girl"]
                if age_number:
                    gender_age_tags.append(f"{age_number} years old")
            elif is_young:
                # 年轻女性：30岁及以下都是年轻女性
                if age_number:
                    # 如果有具体年龄，使用具体年龄标签，强调成年女性
                    gender_age_tags = ["1woman", f"{age_number} years old", "adult female", "woman"]
                    # 30岁以下添加"young woman"标签，30-34岁保持"adult female"
                    if age_number < 30:
                        gender_age_tags.insert(2, "young woman")
                else:
                    # 没有具体年龄，使用通用年轻女性标签
                    gender_age_tags = ["1woman", "young woman", "adult female", "woman"]
            elif is_middle:
                gender_age_tags = ["1woman", "middle-aged woman", "mature female", "woman"]
            elif is_old:
                gender_age_tags = ["1woman", "elderly woman", "old woman", "woman"]
            else:
                gender_age_tags = ["1woman", "adult female", "woman"]  # 默认成年女性
                
            # SD特殊强调：重复性别标签防止误判，同时再次强调单人
            tags.extend(gender_age_tags)
            tags.extend(["female", "not male"])
            # 再次强调单人约束（防止生成多人）
            tags.extend(["(solo:1.8)", "(1person:1.8)", "only one person"])
            
        else:
            # 无法判断性别，从名字推测
            if any(kw in description for kw in ["王", "李", "张", "刘", "陈", "杨", "黄", "赵", "周", "吴"]):
                tags.extend(["1person", "Chinese person", "(solo:1.8)", "(1person:1.8)", "only one person"])
            else:
                tags.extend(["1person", "(solo:1.8)", "(1person:1.8)", "only one person"])
        
        # 单人约束已在最前面添加，并在性别标签后再次强调，确保不会被覆盖
        
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
        
        # === 5. 服装（从描述中提取，更详细，支持朴素、家居服等）===
        clothing_keywords = {
            # 上装
            "衬衫": "shirt", "白衬衫": "white shirt",
            "T恤": "t-shirt", "短袖": "short sleeves",
            "长袖": "long sleeves", "毛衣": "sweater",
            "卫衣": "hoodie", "外套": "jacket",
            "西装": "suit", "西装外套": "suit jacket",
            "夹克": "jacket", "风衣": "trench coat",
            "针织衫": "knitwear", "开衫": "cardigan",
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
            # 家居服相关
            "家居服": "loungewear", "睡衣": "pajamas", "家居": "home wear",
            "舒适": "comfortable", "宽松": "loose fitting",
            # 颜色
            "黑色": "black", "白色": "white", "灰色": "gray", "深色": "dark",
            "红色": "red", "蓝色": "blue", "绿色": "green",
            "黄色": "yellow", "紫色": "purple", "粉色": "pink",
            "棕色": "brown", "米色": "beige", "浅色": "light",
            # 材质和风格
            "皮革": "leather", "牛仔": "denim", "棉质": "cotton",
            "运动风": "sporty", "休闲风": "casual", "正式": "formal",
            # 朴素风格
            "朴素": "plain", "简单": "simple", "简约": "minimal",
            "无装饰": "no accessories", "无配饰": "no accessories"
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
        
        # === 6. 构图标签（所有构图都默认站立）===
        if composition == "full_body":
            # 全身照：强调站立姿势
            tags.extend([
                "full body", 
                "standing straight", "standing figure", "full shot",
                "vertical stance", "erect posture"
            ])
        elif composition == "upper_body":
            # 半身照：也要站立（上半身直立）
            tags.extend([
                "upper body", 
                "portrait", 
                "half body",
                "standing", "upright", "erect"
            ])
        elif composition == "portrait":
            # 肖像照：也要直立（头部和肩部直立）
            tags.extend([
                "portrait", 
                "face focus", 
                "close-up",
                "upright", "erect", "vertical"
            ])
        
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
        
        # === 9. 服装变体（如果有，需要覆盖原有服装描述）===
        # 注意：如果用户设置了服装变体，应该优先使用变体，而不是原始描述中的服装
        if variant_mode == "preset" and variant:
            variant_dict = CharacterPromptBuilder.OUTFIT_VARIANTS.get(variant, {})
            if variant_dict:
                variant_tags = variant_dict.get("en", [])
                # 移除之前添加的服装标签（避免冲突）
                clothing_tags_to_remove = ["casual wear", "shirt", "pants", "dress", "formal wear"]
                tags = [tag for tag in tags if tag not in clothing_tags_to_remove]
                # 添加变体标签（放在前面以增加权重）
                tags = variant_tags[:5] + tags  # 取前5个变体标签，放在前面
        elif variant_mode == "custom" and variant:
            # 自定义变体：直接添加到提示词前面
            custom_tags = variant.split(",") if "," in variant else [variant]
            # 移除通用服装标签
            clothing_tags_to_remove = ["casual wear", "shirt", "pants", "dress", "formal wear"]
            tags = [tag for tag in tags if tag not in clothing_tags_to_remove]
            # 添加自定义标签
            tags = [tag.strip() for tag in custom_tags[:5]] + tags
        
        # === 10. 面部特征、体型和精神状态（扩展关键词，覆盖更多特征）===
        body_keywords = {
            # 体型（扩展）
            "瘦": "slim", "苗条": "slender", "纤细": "slim", "细瘦": "thin",
            "瘦弱": "thin and weak", "瘦高": "tall and thin", "瘦小": "small and thin",
            "偏瘦": "slightly thin", "偏瘦弱": "slightly thin and weak",
            "壮": "muscular", "健壮": "athletic", "强壮": "strong", "魁梧": "burly",
            "胖": "chubby", "微胖": "slightly chubby", "丰满": "full-figured", "肥胖": "obese",
            "高": "tall", "矮": "short", "中等身材": "average build", "中等": "medium height",
            "中等身高": "medium height", "中等身材": "average build",
            "高大": "tall", "矮小": "short and small", "匀称": "well-proportioned",
            # 面部特征（扩展，更详细）
            "圆脸": "round face", "方脸": "square face", "瓜子脸": "oval face",
            "鹅蛋脸": "oval face", "长脸": "long face", "尖脸": "pointed face",
            "颧骨": "high cheekbones", "颧骨稍高": "slightly high cheekbones", "颧骨高": "high cheekbones",
            "大眼睛": "large eyes", "大眼": "large eyes", "小眼睛": "small eyes", "细长眼睛": "slender eyes",
            "双眼皮": "double eyelids", "单眼皮": "monolid", "内双": "inner double eyelids",
            "高鼻梁": "high nose bridge", "塌鼻梁": "flat nose", "挺鼻": "straight nose",
            "厚嘴唇": "full lips", "薄嘴唇": "thin lips", "小嘴": "small mouth",
            "嘴唇": "lips", "嘴唇干燥": "dry lips", "略显干燥": "slightly dry",
            "浓眉": "thick eyebrows", "细眉": "thin eyebrows", "淡眉": "light eyebrows",
            "双下巴": "double chin", "尖下巴": "pointed chin", "圆下巴": "round chin",
            # 皮肤（扩展）
            "白皙": "fair skin", "古铜": "tan skin", "黝黑": "dark skin",
            "皮肤白": "fair skin", "皮肤黑": "dark skin", "肤色深": "dark skin",
            "苍白": "pale skin", "面无血色": "pale", "脸色苍白": "pale complexion",
            "红润": "rosy complexion", "健康肤色": "healthy skin",
            "偏白": "fair skin", "偏白但": "fair but", "略显暗淡": "slightly dull",
            # 精神状态特征（扩展，更详细）
            "憔悴": "haggard", "疲惫": "tired", "疲倦": "weary",
            "焦虑": "anxious", "紧张": "tense", "不安": "uneasy",
            "疲惫不堪": "exhausted", "精神不振": "listless",
            "黑眼圈": "dark circles under eyes", "眼袋": "eye bags", "眼袋明显": "obvious eye bags",
            "黑眼圈深重": "deep dark circles", "深重": "deep",
            "脸色差": "poor complexion", "疲惫的面容": "tired appearance",
            "无精打采": "listless", "憔悴不堪": "haggard", "虚弱": "weak",
            "面容憔悴": "haggard face", "憔悴的面容": "haggard appearance",
            "眼神疲惫": "tired eyes", "眼神": "eyes", "发颤": "trembling", "经常发颤": "often trembling",
            "手指发颤": "trembling fingers", "微微发颤": "slightly trembling",
            "透露疲惫": "revealing fatigue", "疲惫和紧张": "fatigue and tension",
            # 气质（扩展）
            "帅气": "handsome", "英俊": "handsome", "俊朗": "handsome",
            "漂亮": "beautiful", "美丽": "beautiful", "清秀": "delicate features",
            "可爱": "cute", "甜美": "sweet", "温柔": "gentle",
            "冷峻": "stern", "严肃": "serious", "憨厚": "honest-looking",
            "文静": "gentle", "活泼": "lively", "开朗": "cheerful",
            "忧郁": "melancholy", "阴郁": "gloomy", "淡漠": "indifferent"
        }
        # 提取精神状态特征（单独处理，确保优先级）
        mental_state_tags = []
        for cn_key, en_tag in body_keywords.items():
            if cn_key in description:
                if en_tag not in tags:
                    # 精神状态特征需要特别强调
                    if cn_key in ["憔悴", "疲惫", "疲倦", "焦虑", "紧张", "不安", 
                                 "疲惫不堪", "精神不振", "黑眼圈", "眼袋", "眼袋明显",
                                 "黑眼圈深重", "脸色差", "疲惫的面容", "苍白", "面无血色", "脸色苍白",
                                 "面容憔悴", "眼神疲惫", "发颤", "经常发颤", "手指发颤", "微微发颤",
                                 "透露疲惫", "疲惫和紧张", "略显暗淡"]:
                        mental_state_tags.append(en_tag)
                    else:
                        tags.append(en_tag)
        
        # 精神状态特征已提取，稍后在最终重组时处理（确保单人约束始终在最前面）
        
        # === 11. 背景 ===
        tags.extend(["transparent background", "no background", "solid color background", "pure white background"])  # 无背景或纯色背景
        
        # === 12. 光线（简化）===
        tags.extend([
            "natural light",  # 简化为 natural light
            "clear"  # 清晰即可
        ])
        
        # === 13. 正向强调（确保人物质量和姿势）===
        # 如果有精神状态特征，确保表情和状态匹配
        if mental_state_tags:
            # 疲惫、憔悴的人物不应有开心的表情（除非明确指定）
            if expression == "neutral":
                tags.extend([
                    "tired expression", "weary look", "exhausted appearance"
                ])
        
        # === 13. 基础姿势（大幅简化）===
        tags.extend([
            "looking at viewer",  # 看向观众
            "standing",  # 站立
            "simple pose"  # 简单姿势
        ])
        
        # === 最终重组：按照SD最佳实践顺序排列 ===
        # SD提示词最佳顺序：质量标签 -> 主体（单人+性别年龄）-> 特征描述 -> 环境/背景 -> 技术参数
        
        # 1. 提取各个类别的标签
        quality_tags_in_tags = [tag for tag in tags if tag in quality_tags]
        
        # 2. 提取主体相关标签（单人约束 + 性别年龄标签）
        subject_tags = []
        # 从tags中提取性别年龄相关标签
        gender_age_keywords = ["1boy", "1girl", "1man", "1woman", "boy", "girl", "man", "woman", 
                               "male", "female", "years old", "child", "teenager", "adult"]
        for tag in tags:
            if any(kw in tag.lower() for kw in gender_age_keywords) or tag in single_person_tags:
                if tag not in subject_tags:
                    subject_tags.append(tag)
        
        # 3. 提取特征描述标签（发型、服装、体型、面部特征等）
        feature_tags = []
        feature_keywords = ["hair", "clothing", "outfit", "face", "skin", "eyes", "body", "tall", 
                           "short", "slim", "thin", "wear", "shirt", "dress", "jacket", "black", "white"]
        for tag in tags:
            if any(kw in tag.lower() for kw in feature_keywords) or tag in mental_state_tags:
                if tag not in subject_tags and tag not in feature_tags:
                    feature_tags.append(tag)
        
        # 4. 提取环境/背景标签
        background_tags = [tag for tag in tags if "background" in tag.lower() or "transparent" in tag.lower()]
        
        # 5. 提取技术参数标签（视角、表情、姿势、光线等）
        technical_tags = []
        technical_keywords = ["view", "expression", "pose", "standing", "light", "looking"]
        for tag in tags:
            if any(kw in tag.lower() for kw in technical_keywords):
                if tag not in subject_tags and tag not in feature_tags and tag not in background_tags:
                    technical_tags.append(tag)
        
        # 6. 其他未分类的标签
        other_tags = []
        all_categorized = set(quality_tags_in_tags + subject_tags + feature_tags + background_tags + technical_tags)
        for tag in tags:
            if tag not in all_categorized:
                other_tags.append(tag)
        
        # === 按照最佳实践顺序重组：质量 -> 主体 -> 特征 -> 背景 -> 技术 -> 其他 ===
        final_tags = (
            quality_tags_in_tags +      # 质量标签（最重要，最前面）
            subject_tags +              # 主体（单人+性别年龄）
            feature_tags +              # 特征描述（发型、服装、体型、面部特征）
            background_tags +           # 背景
            technical_tags +            # 技术参数（视角、表情、姿势）
            other_tags                  # 其他
        )
        
        # 去重并返回（保持顺序）
        seen = set()
        unique_tags = []
        for tag in final_tags:
            tag_lower = tag.lower()
            # 处理带权重的标签去重
            tag_base = tag.split(':')[0].strip('()[]') if ':' in tag else tag
            if tag_base.lower() not in seen:
                seen.add(tag_base.lower())
                unique_tags.append(tag)
        
        # 确保提示词长度合理（SD建议75个单词以内，这里按字符数控制）
        prompt = ", ".join(unique_tags)
        if len(prompt) > 500:  # 如果超过500字符，进行智能截断
            # 优先保留质量标签、主体标签和特征标签
            essential_tags = quality_tags_in_tags + subject_tags + feature_tags[:20]
            prompt = ", ".join(essential_tags)
        
        return prompt
    
    @staticmethod
    def _extract_core_description(description: str, max_length: int = 100) -> str:
        """
        智能提取核心视觉特征描述
        优先保留：年龄、性别、发型、服装、体型等关键视觉特征
        
        Args:
            description: 完整描述
            max_length: 最大字符数
            
        Returns:
            提取后的核心描述
        """
        if len(description) <= max_length:
            return description
        
        # 定义关键特征优先级（按视觉重要性排序）
        priority_keywords = [
            # 第一优先级：年龄性别（最关键）
            (r'[^。，]*(?:约|大约)?(\d+|十|二十|三十|四十|五十)(?:岁|多岁)[^。，]*', 10),
            (r'[^。，]*(?:男孩|女孩|男性|女性|男人|女人|男生|女生)[^。，]*', 10),
            
            # 第二优先级：发型发色
            (r'[^。，]*(?:短发|长发|卷发|直发|马尾|黑发|棕发|金发|白发|银发)[^。，]*', 8),
            
            # 第三优先级：服装
            (r'[^。，]*(?:西装|衬衫|T恤|连衣裙|外套|卫衣|运动服|校服|休闲装)[^。，]*', 7),
            (r'[^。，]*(?:黑色|白色|蓝色|灰色|深色|浅色).*?(?:衣服|服装|上衣|裤子|裙子)[^。，]*', 7),
            
            # 第四优先级：体型特征
            (r'[^。，]*(?:瘦弱|健壮|高大|苗条|魁梧|纤细|丰满)[^。，]*', 6),
            
            # 第五优先级：面部特征
            (r'[^。，]*(?:圆脸|方脸|瓜子脸|大眼睛|高鼻梁)[^。，]*', 5),
            
            # 第六优先级：肤色
            (r'[^。，]*(?:白皙|黝黑|苍白|健康肤色)[^。，]*', 4),
        ]
        
        # 提取关键句子
        extracted_parts = []
        total_length = 0
        matched_text = set()  # 防止重复
        
        for pattern, priority in priority_keywords:
            if total_length >= max_length:
                break
            
            matches = re.findall(pattern, description)
            for match in matches:
                sentence = match if isinstance(match, str) else match[0] if match else ""
                sentence = sentence.strip("，。 ")
                
                # 避免重复和过长
                if sentence and sentence not in matched_text and len(sentence) < 50:
                    if total_length + len(sentence) <= max_length:
                        extracted_parts.append(sentence)
                        matched_text.add(sentence)
                        total_length += len(sentence)
        
        # 如果没有提取到足够内容，使用前N个字符
        if not extracted_parts or total_length < max_length // 2:
            # 简单截断，但尽量在句号或逗号处截断
            truncated = description[:max_length]
            # 找到最后一个句号或逗号
            last_punct = max(truncated.rfind("。"), truncated.rfind("，"), truncated.rfind(","))
            if last_punct > max_length // 2:  # 确保截断位置合理
                return truncated[:last_punct]
            return truncated
        
        return "，".join(extracted_parts)
    
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
        
        # 先检测性别和年龄（用于自然语言描述）
        is_male = any(kw in description for kw in [
            "男孩", "boy", "男生", "男", "male", "man", "先生", "他", "男性", "男人"
        ])
        is_female = any(kw in description for kw in [
            "女孩", "girl", "女生", "女", "female", "woman", "lady", "她", "女性", "女人"
        ])
        
        # 检测年龄（支持中文数字）
        age_number = None
        chinese_numbers = {
            "一": 1, "二": 2, "三": 3, "四": 4, "五": 5,
            "六": 6, "七": 7, "八": 8, "九": 9, "十": 10,
            "十一": 11, "十二": 12, "十三": 13, "十四": 14, "十五": 15,
            "十六": 16, "十七": 17, "十八": 18, "十九": 19, "二十": 20,
            "廿": 20, "三十": 30, "四十": 40, "五十": 50, "六十": 60
        }
        
        age_patterns = [
            r'(\d+)[岁多]', r'(\d+)[左右]', r'大约(\d+)', r'(\d+)来岁'
        ]
        for pattern in age_patterns:
            match = re.search(pattern, description)
            if match:
                age_number = int(match.group(1))
                break
        
        if age_number is None:
            for cn_num, num_val in chinese_numbers.items():
                if cn_num + "岁" in description or "约" + cn_num + "岁" in description:
                    age_number = num_val
                    break
        
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
            # === 第一优先级：明确单人约束（防止生成多人，最高优先级）===
            parts = [
                f"单人照片，仅一个人，只有一个人，{comp_text}",
                "绝对不要生成多个人，只生成一个人"
            ]
            
            # 明确性别和年龄（API需要明确说明，再次强调单人）
            if is_male:
                if age_number and age_number < 13:
                    parts.append(f"一个约{age_number}岁的男孩，只有这一个人")
                elif age_number and age_number < 20:
                    parts.append(f"一个约{age_number}岁的青少年男孩，只有这一个人")
                else:
                    parts.append("一名男性，只有这一个人")
            elif is_female:
                if age_number and age_number < 13:
                    parts.append(f"一个约{age_number}岁的女孩，只有这一个人")
                elif age_number and age_number < 20:
                    parts.append(f"一个约{age_number}岁的青少年女孩，只有这一个人")
                else:
                    parts.append("一名女性，只有这一个人")
            
            # 添加国籍
            if default_nationality == "chinese":
                if not any(kw in description for kw in ["外国", "欧美", "美国", "英国"]):
                    parts.append("中国人")
            
            # === 智能提取核心描述（限制长度，优先保留关键特征）===
            # 对于混元等有字数限制的API，需要提取最关键的特征
            desc_text = CharacterPromptBuilder._extract_core_description(description, max_length=100)
            parts.append(desc_text)
            
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
            
            # 默认站立姿势（如果没有额外动作要求）
            # 检查是否有动作相关的关键词
            has_action_keywords = any(kw in extra_details.lower() + description.lower() for kw in [
                "坐", "躺", "趴", "蹲", "跪", "跑", "跳", "走", "坐", "站", "动作", "姿势",
                "sitting", "lying", "kneeling", "running", "jumping", "walking", "action", "pose"
            ])
            if not has_action_keywords:
                # 根据构图类型添加站立描述
                if composition == "full_body":
                    parts.append("站立姿势，空手，不持任何物品")
                elif composition == "upper_body":
                    parts.append("直立站立，空手")
                elif composition == "portrait":
                    parts.append("直立，空手")
            else:
                # 即使有动作，也要强调空手
                parts.append("空手，不持任何物品")
            
            # 添加质量要求（简化，避免触发摄影设备）
            parts.append("高清，细节清晰，无背景，透明背景")
            
            return "，".join(parts)
        
        else:
            # 英文自然语言
            # === 第一优先级：明确单人约束（防止生成多人，最高优先级）===
            parts = [
                f"Single person portrait photo, only one person, only one character, {comp_text} photo of",
                "absolutely no other people, just one person only"
            ]
            
            # 明确性别和年龄（API需要明确说明，再次强调单人）
            if is_male:
                if age_number and age_number < 13:
                    parts.append(f"one {age_number}-year-old boy, only this one person")
                elif age_number and age_number < 20:
                    parts.append(f"one {age_number}-year-old teenage boy, only this one person")
                else:
                    parts.append("one male person, only this one person")
            elif is_female:
                if age_number and age_number < 13:
                    parts.append(f"one {age_number}-year-old girl, only this one person")
                elif age_number and age_number < 20:
                    parts.append(f"one {age_number}-year-old teenage girl, only this one person")
                else:
                    parts.append("one female person, only this one person")
            else:
                parts.append("one person, only this one person")
            
            # 添加国籍
            if default_nationality == "chinese":
                if not any(kw in description for kw in ["American", "European", "Western"]):
                    parts.append("Chinese")
            
            # === 智能提取核心描述（限制长度，优先保留关键特征）===
            desc_text = CharacterPromptBuilder._extract_core_description(description, max_length=150)
            parts.append(desc_text)
            
            # 添加表情
            if expression != "neutral":
                parts.append(f"with {expr_text} expression")
            
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
            
            # 默认站立姿势（如果没有额外动作要求）
            # 检查是否有动作相关的关键词
            has_action_keywords = any(kw in (extra_details.lower() + description.lower()) for kw in [
                "sitting", "lying", "kneeling", "running", "jumping", "walking", 
                "action", "pose", "crouching", "reclining", "prone"
            ])
            if not has_action_keywords:
                # 根据构图类型添加站立描述
                if composition == "full_body":
                    parts.append("standing pose, empty hands, not holding anything")
                elif composition == "upper_body":
                    parts.append("standing upright, empty hands")
                elif composition == "portrait":
                    parts.append("upright, empty hands")
            else:
                # 即使有动作，也要强调空手
                parts.append("empty hands, not holding anything")
            
            # 添加质量要求（简化，避免触发摄影设备）
            parts.append("high quality, detailed, no background, transparent background")
            
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
    def get_negative_prompt_for_character(api_type: str = "sd", description: str = "") -> str:
        """
        获取人物生成的负面提示词
        
        Args:
            api_type: API类型（主要用于SD）
            description: 人物描述（用于生成针对性的负面提示词）
        
        Returns:
            负面提示词字符串
        """
        if api_type == "sd":
            # SD负面提示词（极简版）- 只保留最核心的
            negative_tags = [
                # 最基本的质量问题
                "low quality", "worst quality", "blurry", "blurred",
                # 最基本的解剖学问题
                "bad anatomy", "bad hands", "deformed", "malformed",
                # ★★★ 多人（极高权重，最重要）★★★
                "(multiple people:2.0)", "(two people:2.0)", "(three people:2.0)", 
                "(group:2.0)", "(crowd:2.0)", "(pair:2.0)", "(duo:2.0)", "(couple:2.0)",
                "2people", "3people", "4people", "multiple persons", "many people",
                "extra person", "duplicate person", "clone", "twin", "another person",
                "second person", "third person", "more than 1 person",
                "2 persons", "3 persons", "multiple characters", "group photo",
                # 道具和设备（核心）
                "microphone", "equipment", "devices", "props",
                # 背景相关（禁止任何背景）
                "background", "scene", "environment", "indoor", "outdoor", "room", "street", "building",
                "landscape", "wall", "floor", "ceiling", "furniture", "interior", "exterior",
                "complex background", "detailed background", "busy background",
                # ★★★ 禁止抽象、艺术化风格（新增，防止生成抽象图片）★★★
                "abstract", "abstract art", "abstract style", "abstract painting",
                "artistic", "artistic style", "artistic painting", "artwork",
                "illustration", "illustrated", "illustration style", "drawing", "sketch",
                "cartoon", "cartoon style", "anime style", "manga style",
                "stylized", "stylized art", "stylized illustration",
                "watercolor", "oil painting", "digital painting", "concept art",
                "lowpoly", "vector art", "graphic art", "2d art",
                "distorted", "surreal", "fantasy art", "fantasy style",
                "unrealistic", "non-realistic", "stylized rendering",
                "no realistic", "not realistic", "not photorealistic"
            ]
            
            # 根据描述添加针对性的负面提示词
            if description:
                # 如果描述中是男孩，禁止生成女孩
                if any(kw in description for kw in ["男孩", "boy", "男生", "男"]):
                    negative_tags.extend([
                        "girl", "female", "woman", "女性", "女孩", "女人",
                        "feminine", "female character", "female person"
                    ])
                # 如果描述中是女孩，禁止生成男孩
                elif any(kw in description for kw in ["女孩", "girl", "女生", "女"]):
                    negative_tags.extend([
                        "boy", "male", "man", "男性", "男孩", "男人",
                        "masculine", "male character", "male person"
                    ])
                
                # 如果是儿童，禁止生成成年人
                if any(kw in description for kw in ["儿童", "小孩", "child", "kid", "十岁", "11岁", "12岁", "13岁"]):
                    negative_tags.extend([
                        "adult", "mature", "grown-up", "elderly",
                        "成年人", "成熟", "老人"
                    ])
                # 如果是成年人，禁止生成儿童
                elif any(kw in description for kw in ["成年", "adult", "mature", "30", "40", "50"]):
                    negative_tags.extend([
                        "child", "kid", "teenager", "baby",
                        "儿童", "小孩", "青少年", "婴儿"
                    ])
            
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
                # === 智能截断策略：保留最关键的信息 ===
                parts = prompt.split("，")
                
                # 1. 识别并保留关键约束词（必须保留）
                critical_parts = []
                other_parts = []
                
                critical_keywords = ["单人", "仅一个人", "一个", "solo", "only one person", "single person"]
                
                for part in parts:
                    is_critical = any(kw in part for kw in critical_keywords)
                    if is_critical:
                        critical_parts.append(part)
                    else:
                        other_parts.append(part)
                
                # 2. 优先保留关键约束
                core_parts = critical_parts.copy()
                current_length = sum(len(p) for p in core_parts) + len(core_parts)  # 包括逗号
                
                # 3. 剩余空间填充其他重要信息
                for part in other_parts:
                    if current_length + len(part) + 1 <= max_len:
                        core_parts.append(part)
                        current_length += len(part) + 1
                    else:
                        # 如果还有空间，尝试截断这个部分
                        remaining_space = max_len - current_length - 1
                        if remaining_space > 10:  # 至少保留10个字符才有意义
                            core_parts.append(part[:remaining_space])
                        break
                
                result = "，".join(core_parts)
                
                # 确保结果确实不超过限制
                if len(result) > max_len:
                    result = result[:max_len]
                
                return result
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


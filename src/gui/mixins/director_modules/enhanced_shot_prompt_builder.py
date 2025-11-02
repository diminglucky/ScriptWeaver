"""
增强型分镜头提示词构建器 - 充分利用shots.json中的所有故事细节
"""

import re  # 移到文件顶部，避免循环中重复导入


class EnhancedShotPromptBuilder:
    """增强型提示词构建器 - 将分镜头JSON的详细信息完整转换为图片生成提示词"""
    
    @staticmethod
    def build_from_shot_json(shot: dict, api_type: str = "sd") -> tuple:
        """
        从分镜头JSON构建完整提示词，确保故事细节不丢失
        
        Args:
            shot: 分镜头字典（从shots.json加载）
            api_type: API类型 ('sd', 'openai', 'hunyuan')
        
        Returns:
            (positive_prompt, negative_prompt)
        """
        if api_type == "sd":
            return EnhancedShotPromptBuilder._build_sd_prompt_from_shot(shot)
        else:
            return EnhancedShotPromptBuilder._build_natural_prompt_from_shot(shot)
    
    @staticmethod
    def _build_sd_prompt_from_shot(shot: dict) -> tuple:
        """为SD构建详细的英文标签提示词"""
        
        # 边界检查
        if not shot or not isinstance(shot, dict):
            return ("masterpiece, best quality", "low quality, bad anatomy")
        
        # ===== 第一部分：质量标签（最前面，权重最高） =====
        quality_tags = [
            "masterpiece",
            "best quality",
            "ultra detailed",
            "8k",
            "photorealistic",
            "professional photography",
            "cinematic lighting",
            "sharp focus",
            "highly detailed",
            "intricate details",
        ]
        
        # ===== 第二部分：人物一致性标签（核心！） =====
        consistency_tags = [
            "character consistency",
            "consistent character design",
            "same person",
            "same character",
        ]
        
        # ===== 第三部分：人物详细描述（从shots.json的character_details提取） =====
        character_prompts = []
        character_details = shot.get('character_details', {})
        
        # 🔥 修复多人场景问题：先判断总人数，再处理每个人物
        if not character_details or not isinstance(character_details, dict):
            character_details = {}
        
        num_characters = len(character_details)
        
        # 根据人物数量添加基础标签
        if num_characters == 0:
            base_char_tags = []
        elif num_characters == 1:
            # 单人场景：需要根据性别判断用 1boy/1girl
            base_char_tags = ["solo"]  # 稍后根据性别添加1boy或1girl
        elif num_characters == 2:
            base_char_tags = ["2people"]
        else:
            base_char_tags = [f"{num_characters}people"]
        
        for idx, (char_name, details) in enumerate(character_details.items()):
            char_tags = []
            
            # ★★★ appearance - 外貌特征 ★★★
            appearance = details.get('appearance', '')
            gender_detected = None  # 用于检测性别
            
            if appearance:
                # 年龄
                if "岁" in appearance:
                    age_match = re.search(r'(\d+)岁', appearance)
                    if age_match:
                        age = int(age_match.group(1))
                        if age < 18:
                            char_tags.append("teenage")
                        elif age < 25:
                            char_tags.append("young adult")
                        elif age < 35:
                            char_tags.append("adult")
                        else:
                            char_tags.append("middle-aged")
                
                # 性别（记录下来，稍后用于单人场景的1boy/1girl判断）
                if "男" in appearance:
                    char_tags.append("male")
                    gender_detected = "male"
                elif "女" in appearance:
                    char_tags.append("female")
                    gender_detected = "female"
                
                # 体型
                if "苗条" in appearance or "瘦" in appearance:
                    char_tags.append("slim build")
                    char_tags.append("slender body")
                elif "匀称" in appearance:
                    char_tags.append("average build")
                elif "健壮" in appearance:
                    char_tags.append("athletic build")
                
                # 脸型
                if "瓜子脸" in appearance or "鹅蛋脸" in appearance:
                    char_tags.append("oval face")
                    char_tags.append("delicate features")
                elif "圆脸" in appearance:
                    char_tags.append("round face")
                elif "国字脸" in appearance:
                    char_tags.append("square face")
                    char_tags.append("strong jawline")
                
                # 五官
                if "清秀" in appearance:
                    char_tags.append("refined features")
                if "立体" in appearance:
                    char_tags.append("defined features")
                
                # 肤色（🔥 修复：先匹配长词组，避免短词干扰）
                if "白皙" in appearance:
                    char_tags.append("fair skin")
                    char_tags.append("pale skin")
                elif "小麦" in appearance or "古铜" in appearance:
                    char_tags.append("tan skin")
                elif "健康" in appearance:
                    char_tags.append("healthy complexion")
                elif "白" in appearance:  # 放最后，避免"白皙"被重复匹配
                    char_tags.append("fair skin")
            
            # ★★★ hair - 发型 ★★★
            hair = details.get('hair', '')
            if hair:
                hair_parts = []
                
                # 颜色
                if "黑" in hair:
                    hair_parts.append("black")
                elif "棕" in hair or "褐" in hair:
                    hair_parts.append("brown")
                elif "金" in hair or "黄" in hair:
                    hair_parts.append("blonde")
                
                # 长度
                if "及肩" in hair or "中长" in hair:
                    hair_parts.append("shoulder length")
                elif "长发" in hair:
                    hair_parts.append("long")
                elif "短发" in hair:
                    hair_parts.append("short")
                
                # 样式
                if "披散" in hair or "自然" in hair:
                    hair_parts.append("loose")
                if "直" in hair:
                    hair_parts.append("straight")
                elif "卷" in hair or "微卷" in hair:
                    hair_parts.append("wavy")
                if "马尾" in hair:
                    hair_parts.append("ponytail")
                
                if hair_parts:
                    hair_parts.append("hair")
                    char_tags.append(" ".join(hair_parts))
            
            # ★★★ clothing - 服装（超级重要！） ★★★
            clothing = details.get('clothing', '')
            if clothing:
                clothing_tags = []
                
                # 上衣
                if "睡衣" in clothing:
                    if "灰色" in clothing or "浅灰" in clothing:
                        clothing_tags.append("light gray pajamas")
                    else:
                        clothing_tags.append("pajamas")
                if "衬衫" in clothing:
                    if "白" in clothing:
                        clothing_tags.append("white shirt")
                    else:
                        clothing_tags.append("shirt")
                if "T恤" in clothing:
                    clothing_tags.append("t-shirt")
                if "毛衣" in clothing:
                    if "深色" in clothing:
                        clothing_tags.append("dark sweater")
                    else:
                        clothing_tags.append("sweater")
                if "外套" in clothing:
                    if "深色" in clothing:
                        clothing_tags.append("dark coat")
                    else:
                        clothing_tags.append("coat")
                
                # 下装
                if "长裤" in clothing:
                    clothing_tags.append("long pants")
                if "牛仔裤" in clothing:
                    clothing_tags.append("jeans")
                if "裙" in clothing:
                    clothing_tags.append("skirt")
                
                # 鞋子
                if "运动鞋" in clothing:
                    clothing_tags.append("sneakers")
                if "皮鞋" in clothing:
                    clothing_tags.append("leather shoes")
                if "棉袜" in clothing or "白色棉袜" in clothing:
                    clothing_tags.append("white socks")
                
                # 配饰
                if "眼镜" in clothing:
                    clothing_tags.append("wearing glasses")
                if "围巾" in clothing:
                    clothing_tags.append("scarf")
                
                if clothing_tags:
                    char_tags.append("wearing " + ", ".join(clothing_tags))
            
            # ★★★ expression - 表情（体现情绪） ★★★
            expression = details.get('expression', '')
            if expression:
                expr_tags = []
                
                # 眉毛
                if "眉头" in expression:
                    if "蹙" in expression or "皱" in expression:
                        expr_tags.append("furrowed brows")
                    elif "扬" in expression:
                        expr_tags.append("raised eyebrows")
                
                # 眼神
                if "眼神" in expression:
                    if "若有所思" in expression or "迷茫" in expression:
                        expr_tags.append("thoughtful eyes")
                        expr_tags.append("pensive gaze")
                    elif "空洞" in expression:
                        expr_tags.append("empty eyes")
                        expr_tags.append("blank stare")
                    elif "坚定" in expression:
                        expr_tags.append("determined eyes")
                    elif "温柔" in expression:
                        expr_tags.append("gentle gaze")
                    elif "专注" in expression:
                        expr_tags.append("focused eyes")
                
                # 嘴角
                if "嘴角" in expression:
                    if "下垂" in expression:
                        expr_tags.append("downturned mouth")
                    elif "上扬" in expression or "微笑" in expression:
                        expr_tags.append("slight smile")
                    elif "紧抿" in expression:
                        expr_tags.append("lips pressed together")
                
                # 整体表情
                if "疲惫" in expression or "疲倦" in expression:
                    expr_tags.append("tired expression")
                    expr_tags.append("exhausted face")
                if "悲伤" in expression or "难过" in expression:
                    expr_tags.append("sad expression")
                if "开心" in expression or "微笑" in expression:
                    expr_tags.append("smiling")
                if "愤怒" in expression:
                    expr_tags.append("angry expression")
                if "惊讶" in expression:
                    expr_tags.append("surprised expression")
                if "害怕" in expression:
                    expr_tags.append("fearful expression")
                if "关切" in expression:
                    expr_tags.append("caring expression")
                if "温柔" in expression:
                    expr_tags.append("gentle expression")
                if "坚定" in expression:
                    expr_tags.append("determined expression")
                
                char_tags.extend(expr_tags)
            
            # ★★★ action - 当前动作（体现故事情节） ★★★
            char_action = details.get('action', '')
            if char_action:
                action_tags = []
                
                # 姿势
                if "倒在" in char_action or "躺" in char_action:
                    action_tags.append("lying on bed")
                elif "站" in char_action:
                    action_tags.append("standing")
                elif "坐" in char_action:
                    action_tags.append("sitting")
                elif "蜷缩" in char_action:
                    action_tags.append("curled up")
                elif "走" in char_action:
                    action_tags.append("walking")
                
                # 手部动作
                if "手持手机" in char_action or "拿着手机" in char_action:
                    action_tags.append("holding smartphone")
                if "查看" in char_action:
                    action_tags.append("looking at phone")
                if "掏出" in char_action:
                    action_tags.append("taking out")
                if "递给" in char_action:
                    action_tags.append("handing over")
                if "拍" in char_action and "后背" in char_action:
                    action_tags.append("patting back")
                if "转动" in char_action and "戒指" in char_action:
                    action_tags.append("twisting ring")
                
                # 面部动作
                if "凝视" in char_action or "盯着" in char_action:
                    action_tags.append("staring")
                if "低头" in char_action:
                    action_tags.append("looking down")
                if "抬头" in char_action:
                    action_tags.append("looking up")
                
                char_tags.extend(action_tags)
            
            # 🔥 修复：根据场景类型添加人物基础标签
            # 单人场景：根据性别添加1boy/1girl + male/female focus
            if num_characters == 1:
                if gender_detected == "male":
                    char_tags.insert(0, "1boy")
                    char_tags.insert(1, "male focus")
                elif gender_detected == "female":
                    char_tags.insert(0, "1girl")
                    char_tags.insert(1, "female focus")
                else:
                    char_tags.insert(0, "1person")
                char_tags.insert(2, "solo")  # 强调单人
            
            # 组合人物标签
            if char_tags:
                character_prompts.append(", ".join(char_tags))
        
        # ===== 第四部分：场景环境（从visual_description提取） =====
        scene_tags = []
        visual_desc = shot.get('visual_description', '')
        
        if visual_desc:
            # 环境类型
            if "宿舍" in visual_desc or "dormitory" in visual_desc.lower():
                scene_tags.append("dormitory room")
                scene_tags.append("bedroom interior")
            elif "教室" in visual_desc:
                scene_tags.append("classroom")
            elif "医院" in visual_desc or "走廊" in visual_desc:
                if "医院" in visual_desc:
                    scene_tags.append("hospital corridor")
                else:
                    scene_tags.append("corridor")
            elif "校园" in visual_desc or "樱花" in visual_desc:
                scene_tags.append("campus")
                if "樱花" in visual_desc:
                    scene_tags.append("cherry blossom trees")
                    scene_tags.append("pink petals falling")
            elif "访谈" in visual_desc or "沙发" in visual_desc:
                scene_tags.append("interview room")
                scene_tags.append("modern interior")
            
            # 物品道具
            if "床" in visual_desc:
                scene_tags.append("bed")
            if "书桌" in visual_desc or "desk" in visual_desc.lower():
                scene_tags.append("desk")
            if "窗" in visual_desc or "window" in visual_desc.lower():
                scene_tags.append("window")
            if "手机" in visual_desc:
                scene_tags.append("smartphone")
            if "屏幕" in visual_desc:
                scene_tags.append("screen light")
            
            # 光线氛围
            if "昏暗" in visual_desc or "黑暗" in visual_desc:
                scene_tags.append("dim lighting")
                scene_tags.append("dark room")
            elif "阳光" in visual_desc or "晨光" in visual_desc:
                scene_tags.append("sunlight")
                scene_tags.append("natural light")
            if "冷光" in visual_desc or "冷色" in visual_desc:
                scene_tags.append("cold light")
                scene_tags.append("blue tone")
            if "暖" in visual_desc and "光" in visual_desc:
                scene_tags.append("warm lighting")
        
        # ===== 第五部分：整体动作描述（从action字段） =====
        action_tags = []
        overall_action = shot.get('action', '')
        
        if overall_action:
            # 这里提取场景级别的动作描述
            if "推开门" in overall_action:
                action_tags.append("opening door")
            if "拥抱" in overall_action:
                action_tags.append("hugging")
                action_tags.append("embrace")
            if "亲吻" in overall_action:
                action_tags.append("kissing")
            if "对视" in overall_action:
                action_tags.append("eye contact")
                action_tags.append("looking at each other")
        
        # ===== 第六部分：情感氛围（从emotion字段） =====
        emotion_tags = []
        emotion = shot.get('emotion', '')
        
        if emotion:
            if "孤独" in emotion or "lonely" in emotion.lower():
                emotion_tags.append("lonely atmosphere")
                emotion_tags.append("solitary mood")
            if "疲惫" in emotion:
                emotion_tags.append("tired mood")
            if "矛盾" in emotion or "冲突" in emotion:
                emotion_tags.append("conflicted emotions")
            if "压抑" in emotion:
                emotion_tags.append("oppressive atmosphere")
            if "温馨" in emotion or "浪漫" in emotion:
                emotion_tags.append("warm atmosphere")
                emotion_tags.append("romantic mood")
            if "紧张" in emotion:
                emotion_tags.append("tense atmosphere")
            if "幸福" in emotion or "感动" in emotion:
                emotion_tags.append("touching moment")
                emotion_tags.append("emotional scene")
        
        # ===== 第七部分：镜头类型 =====
        shot_type_tags = []
        shot_type = shot.get('shot_type', '')
        
        if shot_type:
            if "Wide" in shot_type or "全景" in shot_type:
                shot_type_tags.append("wide shot")
                shot_type_tags.append("full scene")
            elif "Medium" in shot_type or "中景" in shot_type:
                shot_type_tags.append("medium shot")
            elif "Close" in shot_type or "特写" in shot_type:
                if "Extreme" in shot_type or "大特写" in shot_type:
                    shot_type_tags.append("extreme close-up")
                else:
                    shot_type_tags.append("close-up shot")
        
        # ===== 第八部分：光线细节（从lighting字段） =====
        lighting_tags = []
        lighting = shot.get('lighting', '')
        
        if lighting:
            if "手机屏幕" in lighting or "屏幕光" in lighting:
                lighting_tags.append("phone screen light")
                lighting_tags.append("screen glow on face")
            if "窗外" in lighting:
                lighting_tags.append("window light")
            if "柔和" in lighting or "soft" in lighting.lower():
                lighting_tags.append("soft lighting")
            if "冷" in lighting:
                lighting_tags.append("cool color temperature")
            if "暖" in lighting:
                lighting_tags.append("warm color temperature")
            if "逆光" in lighting:
                lighting_tags.append("backlit")
            if "侧光" in lighting:
                lighting_tags.append("side lighting")
        
        # ===== 组合最终正向提示词 =====
        # 顺序：质量 -> 一致性 -> 人物数量 -> 人物 -> 动作 -> 场景 -> 情感 -> 镜头 -> 光线
        final_prompt_parts = quality_tags + consistency_tags
        
        # 🔥 修复：多人场景需要添加base_char_tags（2people/3people等）
        if num_characters >= 2:
            final_prompt_parts.extend(base_char_tags)
        
        # 添加其他部分
        final_prompt_parts.extend(
            character_prompts +
            action_tags +
            scene_tags +
            emotion_tags +
            shot_type_tags +
            lighting_tags
        )
        
        positive_prompt = ", ".join(final_prompt_parts)
        
        # ===== 负向提示词 =====
        negative_tags = [
            # 质量
            "low quality", "worst quality", "normal quality", "lowres",
            "blurry", "fuzzy", "out of focus", "bad anatomy",
            "bad hands", "bad proportions", "ugly", "deformed",
            "disfigured", "mutation", "mutated",
            
            # 构图
            "cropped", "cut off", "out of frame",
            "watermark", "signature", "text", "username", "logo",
            
            # 风格
            "cartoon", "anime", "illustration", "painting", "drawing",
            "3d render", "cg", "unrealistic", "artistic style",
            
            # 其他
            "duplicate", "extra limbs", "missing limbs",
            "bad lighting", "overexposed", "underexposed"
        ]
        
        # 🔥 修复：根据人物数量添加不同的约束
        if num_characters == 1:
            # 单人场景：强烈禁止多人
            negative_tags.extend([
                "multiple people", "two people", "three people", "crowd", "group",
                "2girls", "2boys", "3girls", "3boys",
                "different person", "another person"
            ])
        elif num_characters >= 2:
            # 多人场景：不禁止多人，但禁止人数不对
            negative_tags.extend([
                "solo", "1person", "only one person",
                "crowd", "group", "many people"
            ])
        
        # 所有场景都添加的一致性约束
        negative_tags.extend([
            "changing appearance", "character inconsistency",
            "inconsistent clothing", "inconsistent hair", "inconsistent face",
            "different hairstyle", "hair color change", "different outfit",
            "face inconsistency", "multiple identities", "changing features",
            "different face", "face change"
        ])
        
        # 如果有人物，添加更多人物相关约束
        if character_prompts:
            negative_tags.extend([
                "multiple heads", "two faces", "deformed face",
                "extra fingers", "missing fingers", "fused fingers",
                "asymmetric eyes", "cross-eyed", "wrong anatomy"
            ])
        
        negative_prompt = ", ".join(negative_tags)
        
        return (positive_prompt, negative_prompt)
    
    @staticmethod
    def _build_natural_prompt_from_shot(shot: dict) -> tuple:
        """为OpenAI/Hunyuan构建自然语言提示词"""
        # 边界检查
        if not shot or not isinstance(shot, dict):
            return ("高质量照片，专业摄影", "")
        
        parts = []
        
        # 场景描述
        visual_desc = shot.get('visual_description', '')
        if visual_desc:
            parts.append(visual_desc[:200])  # 取前200字
        
        # 人物描述（详细）
        character_details = shot.get('character_details', {})
        if not character_details or not isinstance(character_details, dict):
            character_details = {}
        
        for char_name, details in character_details.items():
            char_parts = [char_name]
            
            if details.get('appearance'):
                char_parts.append(details['appearance'])
            if details.get('hair'):
                char_parts.append(details['hair'])
            if details.get('clothing'):
                char_parts.append(details['clothing'])
            if details.get('expression'):
                char_parts.append(f"表情：{details['expression']}")
            if details.get('action'):
                char_parts.append(f"动作：{details['action']}")
            
            parts.append("，".join(char_parts))
        
        # 整体动作
        action = shot.get('action', '')
        if action:
            parts.append(f"画面动作：{action[:100]}")
        
        # 情感氛围
        emotion = shot.get('emotion', '')
        if emotion:
            parts.append(f"情感：{emotion}")
        
        # 镜头类型
        shot_type = shot.get('shot_type', '')
        if shot_type:
            parts.append(f"镜头：{shot_type}")
        
        # 光线
        lighting = shot.get('lighting', '')
        if lighting:
            parts.append(f"光线：{lighting[:100]}")
        
        prompt = "。".join(parts) + "。高质量，专业摄影，电影级画质，细节丰富，故事性强。"
        negative = "低质量，模糊，变形，多余的人物，人物不一致"
        
        return (prompt, negative)


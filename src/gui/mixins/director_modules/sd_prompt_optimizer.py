"""
Stable Diffusion 提示词优化器
专门针对中文描述优化为SD友好的英文提示词
"""

from typing import Dict, List, Tuple


class SDPromptOptimizer:
    """SD提示词优化器"""
    
    # 人物特征映射表
    FACE_SHAPE_MAP = {
        "圆脸": "round face",
        "方脸": "square face", 
        "瓜子脸": "oval face, v-shaped face",
        "鹅蛋脸": "oval face",
        "长脸": "long face",
        "菱形脸": "diamond face",
        "国字脸": "square jaw face"
    }
    
    SKIN_TONE_MAP = {
        "白皙": "fair skin, pale skin",
        "自然": "natural skin tone",
        "小麦色": "wheat-colored skin, tan skin",
        "古铜色": "bronze skin, tanned",
        "黝黑": "dark skin"
    }
    
    HAIR_STYLE_MAP = {
        # 长度
        "短发": "short hair",
        "中长发": "medium length hair",
        "长发": "long hair",
        "及肩": "shoulder length",
        "及腰": "waist length",
        "光头": "bald",
        
        # 发型
        "直发": "straight hair",
        "卷发": "curly hair", 
        "波浪": "wavy hair",
        "马尾": "ponytail",
        "双马尾": "twin tails, pigtails",
        "丸子头": "bun hairstyle",
        "披肩发": "loose hair",
        "编发": "braided hair",
        
        # 刘海
        "齐刘海": "straight bangs",
        "斜刘海": "side swept bangs",
        "空气刘海": "see-through bangs",
        "中分": "center parted",
        "无刘海": "no bangs"
    }
    
    EXPRESSION_MAP = {
        "微笑": "smiling, gentle smile",
        "大笑": "laughing, big smile",
        "严肃": "serious expression",
        "思考": "thinking, contemplating",
        "惊讶": "surprised, shocked",
        "生气": "angry expression",
        "悲伤": "sad expression",
        "害羞": "shy, bashful",
        "自信": "confident look",
        "疲惫": "tired expression"
    }
    
    CLOTHING_MAP = {
        # 上装
        "T恤": "t-shirt",
        "衬衫": "shirt",
        "白衬衫": "white shirt",
        "格子衬衫": "checkered shirt, plaid shirt",
        "毛衣": "sweater",
        "卫衣": "hoodie",
        "外套": "jacket",
        "西装": "suit jacket",
        "风衣": "trench coat",
        
        # 下装
        "牛仔裤": "jeans, denim pants",
        "西裤": "dress pants, formal trousers",
        "短裤": "shorts",
        "裙子": "skirt",
        "连衣裙": "dress",
        
        # 特殊服装
        "校服": "school uniform",
        "运动服": "sports wear, athletic clothing",
        "正装": "formal wear, business attire",
        "休闲装": "casual wear"
    }
    
    SHOT_TYPE_MAP = {
        "远景": "long shot, wide shot, full scene",
        "全景": "full shot, entire scene visible",
        "中景": "medium shot, waist up",
        "近景": "medium close up",
        "特写": "close up, face focus",
        "大特写": "extreme close up"
    }
    
    LIGHTING_MAP = {
        "自然光": "natural lighting",
        "柔和光": "soft lighting",
        "强光": "bright lighting, harsh light",
        "逆光": "backlit, rim lighting",
        "侧光": "side lighting",
        "顶光": "top lighting",
        "暖光": "warm lighting, golden hour",
        "冷光": "cool lighting, blue tones"
    }
    
    @staticmethod
    def optimize_character_prompt(character_desc: Dict) -> str:
        """优化人物描述为SD提示词"""
        parts = []
        
        # 年龄性别
        age = character_desc.get('age', '')
        gender = character_desc.get('gender', '')
        if age and gender:
            # 转换年龄描述
            if "岁" in age:
                age_num = age.replace("岁", "").strip()
                age_eng = f"{age_num} years old"
            else:
                age_eng = age
            
            # 转换性别
            gender_map = {"男": "male", "女": "female", "男性": "man", "女性": "woman"}
            gender_eng = gender_map.get(gender, gender)
            
            parts.append(f"{age_eng} {gender_eng}")
        
        # 脸型
        face_shape = character_desc.get('face_shape', '')
        if face_shape in SDPromptOptimizer.FACE_SHAPE_MAP:
            parts.append(SDPromptOptimizer.FACE_SHAPE_MAP[face_shape])
        
        # 肤色
        skin_tone = character_desc.get('skin_tone', '')
        if skin_tone in SDPromptOptimizer.SKIN_TONE_MAP:
            parts.append(SDPromptOptimizer.SKIN_TONE_MAP[skin_tone])
        
        # 发型
        hair_desc = character_desc.get('hair', '')
        if hair_desc:
            hair_parts = []
            for cn_term, en_term in SDPromptOptimizer.HAIR_STYLE_MAP.items():
                if cn_term in hair_desc:
                    hair_parts.append(en_term)
            if hair_parts:
                parts.extend(hair_parts)
        
        # 服装
        outfit = character_desc.get('outfit', '')
        if outfit:
            outfit_parts = []
            for cn_term, en_term in SDPromptOptimizer.CLOTHING_MAP.items():
                if cn_term in outfit:
                    outfit_parts.append(f"wearing {en_term}")
            if outfit_parts:
                parts.extend(outfit_parts)
        
        return ", ".join(parts)
    
    @staticmethod
    def optimize_scene_prompt(scene_desc: str) -> str:
        """优化场景描述为SD提示词"""
        # 场景关键词映射
        scene_map = {
            "教室": "classroom",
            "办公室": "office",
            "街道": "street",
            "公园": "park",
            "餐厅": "restaurant",
            "咖啡厅": "coffee shop",
            "医院": "hospital",
            "学校": "school",
            "家里": "home interior",
            "室内": "indoor",
            "室外": "outdoor",
            "夜晚": "night time",
            "白天": "daytime",
            "清晨": "early morning",
            "黄昏": "sunset, dusk",
            "雨天": "rainy day",
            "晴天": "sunny day"
        }
        
        result = scene_desc
        for cn, en in scene_map.items():
            if cn in result:
                result = result.replace(cn, en)
        
        return result
    
    @staticmethod
    def build_quality_tags(style: str = "photorealistic") -> str:
        """构建质量标签"""
        base_tags = [
            "masterpiece",
            "best quality", 
            "highly detailed",
            "sharp focus",
            "professional"
        ]
        
        style_tags = {
            "photorealistic": ["photorealistic", "hyperrealistic", "8k uhd", "dslr", "high quality photo"],
            "cinematic": ["cinematic lighting", "cinematic composition", "film grain", "movie still"],
            "artistic": ["artstation", "concept art", "digital painting", "trending on artstation"],
            "anime": ["anime style", "anime aesthetic", "cel shading", "manga style"]
        }
        
        tags = base_tags + style_tags.get(style, [])
        return ", ".join(tags)
    
    @staticmethod
    def build_negative_prompt(content_type: str = "general") -> str:
        """构建负面提示词"""
        base_negative = [
            "nsfw", "nude", "naked",
            "low quality", "worst quality", 
            "bad anatomy", "bad hands",
            "missing fingers", "extra fingers",
            "poorly drawn face", "mutation",
            "deformed", "ugly", "blurry",
            "watermark", "signature", "text"
        ]
        
        content_negative = {
            "portrait": ["multiple people", "crowd", "bad face", "asymmetrical eyes"],
            "scene": ["bad composition", "cropped", "out of frame"],
            "character": ["wrong proportions", "bad anatomy", "distorted limbs"]
        }
        
        negatives = base_negative + content_negative.get(content_type, [])
        return ", ".join(negatives)
    
    @staticmethod
    def optimize_full_prompt(
        scene_desc: str,
        characters: List[Dict],
        shot_type: str,
        lighting: str = None,
        style: str = "photorealistic"
    ) -> Tuple[str, str]:
        """
        优化完整的提示词
        
        Returns:
            (positive_prompt, negative_prompt)
        """
        parts = []
        
        # 优化场景
        if scene_desc:
            parts.append(SDPromptOptimizer.optimize_scene_prompt(scene_desc))
        
        # 优化人物
        for char in characters:
            char_prompt = SDPromptOptimizer.optimize_character_prompt(char)
            if char_prompt:
                parts.append(char_prompt)
        
        # 添加镜头类型
        if shot_type in SDPromptOptimizer.SHOT_TYPE_MAP:
            parts.append(SDPromptOptimizer.SHOT_TYPE_MAP[shot_type])
        
        # 添加光线
        if lighting and lighting in SDPromptOptimizer.LIGHTING_MAP:
            parts.append(SDPromptOptimizer.LIGHTING_MAP[lighting])
        
        # 添加质量标签
        quality_tags = SDPromptOptimizer.build_quality_tags(style)
        parts.append(quality_tags)
        
        # 组合正面提示词
        positive_prompt = ", ".join(parts)
        
        # 构建负面提示词
        content_type = "portrait" if "close up" in positive_prompt else "scene"
        negative_prompt = SDPromptOptimizer.build_negative_prompt(content_type)
        
        return positive_prompt, negative_prompt


# 使用示例
if __name__ == "__main__":
    # 测试人物描述优化
    character = {
        "age": "25岁",
        "gender": "女",
        "face_shape": "瓜子脸",
        "skin_tone": "白皙",
        "hair": "黑色长发直发",
        "outfit": "白衬衫和牛仔裤"
    }
    
    prompt = SDPromptOptimizer.optimize_character_prompt(character)
    print("人物提示词:", prompt)
    
    # 测试完整场景优化
    scene = "清晨的教室，阳光透过窗户"
    positive, negative = SDPromptOptimizer.optimize_full_prompt(
        scene_desc=scene,
        characters=[character],
        shot_type="中景",
        lighting="自然光"
    )
    
    print("\n正面提示词:", positive)
    print("\n负面提示词:", negative)

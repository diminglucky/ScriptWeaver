"""
图片风格和类型定义
"""

# 图片类型列表
IMAGE_TYPES = [
    "写实照片",
    "日系动漫",
    "3D渲染",
    "水彩画",
    "油画",
    "素描",
    "赛博朋克",
    "蒸汽朋克",
    "像素风",
    "中国风",
    "国风插画",
    "古风",
    "仙侠",
    "武侠",
    "水墨画",
    "工笔画",
    "敦煌壁画",
    "恐怖",
    "惊悚",
    "诡异",
    "悬疑",
    "玄幻",
    "科幻",
    "魔幻"
]

# 腾讯混元风格映射
HUNYUAN_STYLE_MAP = {
    "写实照片": "201",
    "日系动漫": "201",
    "3D渲染": "201",
    "水彩画": "201",
    "油画": "201",
    "素描": "201",
    "赛博朋克": "201",
    "蒸汽朋克": "201",
    "像素风": "201",
    "中国风": "201",
    "国风插画": "201",
    "古风": "201",
    "仙侠": "201",
    "武侠": "201",
    "水墨画": "201",
    "工笔画": "201",
    "敦煌壁画": "201",
    "恐怖": "201",
    "惊悚": "201",
    "诡异": "201",
    "悬疑": "201",
    "玄幻": "201",
    "科幻": "201",
    "魔幻": "201"
}

# 英文风格关键词（用于OpenAI等英文API）
STYLE_KEYWORDS_EN = {
    "写实照片": "photorealistic, high quality photography, natural lighting, realistic, detailed, 8K",
    "日系动漫": "anime style, Japanese animation, vibrant colors, cel shading, anime artwork, high quality anime",
    "3D渲染": "3D render, CGI, high quality rendering, octane render, unreal engine, detailed textures",
    "水彩画": "watercolor painting, soft colors, artistic, traditional art, watercolor style, delicate brushstrokes",
    "油画": "oil painting, thick brushstrokes, classical art style, rich colors, fine art, painterly",
    "素描": "sketch style, pencil drawing, line art, monochrome, artistic sketch, detailed linework",
    "赛博朋克": "cyberpunk style, neon lights, futuristic, dark atmosphere, high-tech, sci-fi",
    "蒸汽朋克": "steampunk style, gears and machinery, Victorian era, retro-futuristic, industrial aesthetic",
    "像素风": "pixel art style, 8-bit/16-bit graphics, retro game art, pixelated",
    "中国风": "Chinese traditional painting style, ink wash painting, classical Chinese art, poetic atmosphere",
    "国风插画": "Chinese style illustration, modern Chinese aesthetic, delicate line art, traditional colors, elegant composition",
    "古风": "ancient Chinese style, traditional hanfu, classical architecture, historical atmosphere, Tang/Song dynasty aesthetic",
    "仙侠": "Chinese xianxia fantasy, immortal cultivator, celestial scenery, flowing robes, mystical clouds, jade palace",
    "武侠": "Chinese wuxia, martial arts, sword fighting, ancient warrior, bamboo forest, misty mountains",
    "水墨画": "Chinese ink wash painting, sumi-e style, black ink, minimal colors, artistic brushwork, zen aesthetic",
    "工笔画": "Chinese gongbi painting, meticulous brushwork, fine details, traditional pigments, classical composition",
    "敦煌壁画": "Dunhuang murals style, ancient Buddhist art, flying apsaras, Tang dynasty colors, religious iconography",
    "恐怖": "horror style, dark atmosphere, scary, terrifying, ominous lighting, nightmare, eerie",
    "惊悚": "thriller style, suspenseful, tense atmosphere, dramatic lighting, mysterious",
    "诡异": "creepy style, unsettling, strange, bizarre, uncanny atmosphere",
    "悬疑": "mystery style, intriguing, enigmatic, shadowy, noir atmosphere",
    "玄幻": "Chinese xuanhuan fantasy, mythical creatures, magical powers, epic scenes, fantasy world",
    "科幻": "sci-fi style, futuristic technology, space, advanced civilization, high-tech",
    "魔幻": "fantasy style, magic, enchanted, mythical, epic fantasy world"
}

# 中文风格描述（用于腾讯混元等中文API）
STYLE_DESC_CN = {
    "写实照片": "高清摄影，写实风格，自然光线，真实质感",
    "日系动漫": "日系动漫风格，精美作画，色彩鲜艳",
    "3D渲染": "3D渲染，高品质建模，精致材质",
    "水彩画": "水彩画风格，色彩柔和，艺术感强",
    "油画": "油画质感，笔触厚重，色彩浓郁",
    "素描": "素描风格，线条流畅，黑白灰调",
    "赛博朋克": "赛博朋克风格，霓虹灯光，未来科技感",
    "蒸汽朋克": "蒸汽朋克风格，机械齿轮，复古科技",
    "像素风": "像素艺术风格，复古游戏美术",
    "中国风": "中国传统绘画风格，水墨意境，古典韵味",
    "国风插画": "国风插画，现代中国美学，线条精美，色彩典雅",
    "古风": "古风，传统服饰，古代建筑，历史氛围，唐宋美学",
    "仙侠": "仙侠奇幻，修仙者，天宫仙境，飘逸长袍，仙气缭绕",
    "武侠": "武侠江湖，武林高手，剑客，竹林，烟雨山水",
    "水墨画": "中国水墨画，笔墨韵味，黑白灰调，禅意美学",
    "工笔画": "工笔重彩，精细笔法，传统颜料，古典构图",
    "敦煌壁画": "敦煌壁画风格，飞天，佛教艺术，唐代色彩",
    "恐怖": "恐怖氛围，阴森可怖，惊悚画面，诡异气氛",
    "惊悚": "惊悚悬疑，紧张刺激，戏剧化光影，神秘氛围",
    "诡异": "诡异风格，诡谲画面，离奇场景，怪诞氛围",
    "悬疑": "悬疑推理，扑朔迷离，阴影重重，黑色电影风",
    "玄幻": "玄幻奇幻，神话生物，魔法力量，史诗场景",
    "科幻": "科幻未来，前沿科技，太空场景，高科技文明",
    "魔幻": "魔幻世界，魔法元素，神话传说，奇幻史诗"
}

# 简短风格关键词（用于腾讯混元等有长度限制的API）
STYLE_KEYWORDS_SHORT = {
    "写实照片": "高清摄影",
    "日系动漫": "动漫风",
    "3D渲染": "3D渲染",
    "水彩画": "水彩",
    "油画": "油画质感",
    "素描": "素描",
    "赛博朋克": "赛博朋克",
    "蒸汽朋克": "蒸汽朋克",
    "像素风": "像素艺术",
    "中国风": "中国风",
    "国风插画": "国风插画",
    "古风": "古风",
    "仙侠": "仙侠",
    "武侠": "武侠",
    "水墨画": "水墨",
    "工笔画": "工笔",
    "敦煌壁画": "敦煌壁画",
    "恐怖": "恐怖",
    "惊悚": "惊悚",
    "诡异": "诡异",
    "悬疑": "悬疑",
    "玄幻": "玄幻",
    "科幻": "科幻",
    "魔幻": "魔幻"
}

# 详细风格说明（用于图片描述生成）
STYLE_INSTRUCTIONS = {
    "写实照片": "高清摄影作品，写实风格，自然光线，真实质感，细节丰富",
    "日系动漫": "日系动漫风格，精美作画，色彩鲜艳，人物可爱，动漫渲染",
    "3D渲染": "3D渲染，高品质建模，精致材质，专业渲染，光影逼真",
    "水彩画": "水彩画风格，色彩柔和，笔触自然，艺术感强，优雅细腻",
    "油画": "油画质感，笔触厚重，色彩浓郁，古典艺术风格，富有层次",
    "素描": "素描风格，线条流畅，黑白灰调，光影明确，艺术素描",
    "赛博朋克": "赛博朋克风格，霓虹灯光，未来科技感，暗黑氛围，高科技元素",
    "蒸汽朋克": "蒸汽朋克风格，机械齿轮，复古科技，维多利亚时代，工业美学",
    "像素风": "像素艺术风格，8bit/16bit画风，复古游戏美术，像素化",
    "中国风": "中国传统绘画风格，水墨意境，古典韵味，诗意氛围，传统美学",
    "国风插画": "国风插画，现代中国美学，精美线条，典雅色彩，细腻构图",
    "古风": "古风，传统汉服，古代建筑，历史氛围，唐宋美学，诗意画面",
    "仙侠": "仙侠奇幻，修仙世界，天宫仙境，飘逸衣袍，仙气缭绕，云雾山水",
    "武侠": "武侠江湖，侠客剑客，轻功飞跃，竹林烟雨，山水意境，武林氛围",
    "水墨画": "中国水墨画，笔墨韵味，黑白灰调，留白意境，禅意美学，传统笔法",
    "工笔画": "工笔重彩，精细笔法，传统颜料，古典构图，细腻刻画，层次丰富",
    "敦煌壁画": "敦煌壁画风格，飞天仙女，佛教艺术，唐代色彩，壁画质感，古典神圣",
    "恐怖": "恐怖风格，阴森恐怖，惊悚氛围，诡异光影，恐怖元素，不安感",
    "惊悚": "惊悚悬疑，紧张刺激，戏剧化照明，神秘气氛，悬念感",
    "诡异": "诡异风格，诡谲离奇，怪诞场景，不寻常氛围，超现实感",
    "悬疑": "悬疑推理，谜团重重，暗影层叠，黑色电影，推理氛围",
    "玄幻": "玄幻奇幻，神话世界，魔法力量，史诗场景，幻想元素，宏大场面",
    "科幻": "科幻未来，高科技，太空场景，前沿科技，未来文明，科技美学",
    "魔幻": "魔幻世界，魔法元素，奇幻生物，神话传说，魔法氛围，史诗感"
}


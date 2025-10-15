"""
测试人物提示词构建器
"""
from src.gui.mixins.character_prompt_builder import CharacterPromptBuilder

def test_single_photo():
    """测试单张照片提示词生成"""
    print("="*60)
    print("测试1：基础全身照（中文）")
    print("="*60)
    
    description = "22岁女性实习生，黑色齐肩短发，圆脸杏仁眼，身高162厘米，穿白色护士服"
    
    prompt = CharacterPromptBuilder.build_character_photo_prompt(
        description=description,
        style="写实照片",
        view_angle="front",
        expression="neutral",
        composition="full_body",
        language="zh"
    )
    
    print(f"提示词:\n{prompt}\n")
    print(f"长度: {len(prompt)} 字符\n")
    
    # 测试腾讯混元优化
    print("="*60)
    print("测试2：腾讯混元优化（限制256字符）")
    print("="*60)
    
    optimized = CharacterPromptBuilder.optimize_for_api(prompt, "hunyuan", 256)
    print(f"优化后提示词:\n{optimized}\n")
    print(f"长度: {len(optimized)} 字符\n")
    
    # 测试英文版
    print("="*60)
    print("测试3：英文版全身照")
    print("="*60)
    
    prompt_en = CharacterPromptBuilder.build_character_photo_prompt(
        description="22-year-old female intern nurse, black shoulder-length hair, round face, almond eyes, 162cm tall, wearing white nurse uniform",
        style="photorealistic",
        view_angle="front",
        expression="happy",
        composition="full_body",
        language="en"
    )
    
    print(f"提示词:\n{prompt_en}\n")
    print(f"长度: {len(prompt_en)} 字符\n")

def test_character_sheet():
    """测试角色设定表提示词生成"""
    print("="*60)
    print("测试4：角色设定表（多视角+多表情）")
    print("="*60)
    
    description = "25岁男性侦探，深棕色短发，鹰钩鼻，身材修长，穿深色风衣"
    
    prompts = CharacterPromptBuilder.build_character_sheet_prompt(
        description=description,
        style="写实照片",
        language="zh"
    )
    
    print(f"\n生成了 {len(prompts)} 个提示词：\n")
    
    for key, data in prompts.items():
        print(f"[{data['type']}] {data['name_zh']}:")
        print(f"  提示词长度: {len(data['prompt'])} 字符")
        print(f"  前100字符: {data['prompt'][:100]}...\n")

if __name__ == "__main__":
    test_single_photo()
    print("\n" + "="*60 + "\n")
    test_character_sheet()


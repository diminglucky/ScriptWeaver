"""
测试即梦AI提示词生成器
"""

from src.gui.mixins.director_modules.jimeng_prompt_generator import JimengPromptGenerator

# 测试分镜数据
test_shot = {
    "shot_number": 1,
    "location": "教室",
    "time": "早上",
    "visual_description": "阳光透过窗户洒进教室，书桌上摆满了课本",
    "characters": ["张强"],
    "action": "张强坐在座位上认真看书，时而推推眼镜",
    "emotion": "专注认真",
    "dialogue": None,
    "shot_type": "中景",
    "camera": {
        "movement": "缓慢推进",
        "angle": "侧面"
    }
}

# 人物信息
character_details = {
    "张强": {
        "description": "男，18岁，高中生，短发，戴黑框眼镜，穿白色衬衫，性格内向认真"
    }
}

print("="*80)
print("即梦AI提示词生成测试")
print("="*80)
print("\n【输入信息】")
print(f"分镜编号: {test_shot['shot_number']}")
print(f"地点: {test_shot['location']}")
print(f"人物: {test_shot['characters']}")
print(f"动作: {test_shot['action']}")
print(f"镜头类型: {test_shot['shot_type']}")
print("\n" + "="*80)

# 生成提示词
prompt = JimengPromptGenerator.generate_video_prompt(
    test_shot,
    character_details
)

print("\n【生成的即梦AI提示词】")
print("-"*80)
print(prompt)
print("-"*80)

print("\n【使用说明】")
print("1. 访问 https://jimeng.jianying.com/ai-tool/image/generate")
print("2. 上传分镜1的生成图片")
print("3. 复制上方提示词到输入框")
print("4. 点击生成视频")

print("\n" + "="*80)
print("测试完成！")
print("="*80)

# 测试批量生成
print("\n\n批量生成测试...")
test_shots = [
    test_shot,
    {
        "shot_number": 2,
        "location": "教室",
        "time": "片刻后",
        "visual_description": "林小雨走到张强旁边",
        "characters": ["张强", "林小雨"],
        "action": "林小雨拍拍张强的肩膀，张强抬头看向她",
        "emotion": "林小雨：开朗；张强：略显惊讶",
        "shot_type": "双人镜头",
        "camera": {
            "movement": "固定",
            "angle": "过肩"
        }
    }
]

character_details["林小雨"] = {
    "description": "女，17岁，高中生，长发马尾，穿蓝色连衣裙，性格活泼开朗"
}

prompts_dict = JimengPromptGenerator.generate_batch_prompts(
    test_shots,
    character_details
)

formatted = JimengPromptGenerator.format_prompts_for_display(prompts_dict)
print(formatted)

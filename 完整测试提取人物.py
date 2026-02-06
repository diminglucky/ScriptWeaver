#!/usr/bin/env python3
"""
完整测试提取人物功能 - 模拟应用环境
"""

import json
import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

from src.gui.services.ai_service import create_ai_service
from src.gui.models.character import Character, CharacterProfile

print("=" * 70)
print("🧪 完整测试提取人物功能")
print("=" * 70)
print()

# 1. 加载API配置
print("1️⃣ 加载API配置...")
try:
    with open('custom_api_presets.json', 'r', encoding='utf-8') as f:
        api_presets = json.load(f)
    print("✅ API配置加载成功")
    print(f"   可用API: {list(api_presets.keys())}")
except Exception as e:
    print(f"❌ 加载配置失败: {e}")
    exit(1)

print()

# 2. 创建AI服务
print("2️⃣ 创建AI服务...")
selected_api = "自定义"
print(f"   使用API: {selected_api}")

ai_service = create_ai_service(api_presets, selected_api)
if not ai_service:
    print("❌ 创建AI服务失败")
    exit(1)

print("✅ AI服务创建成功")
print(f"   Model: {ai_service.config.model}")
print()

# 3. 准备测试故事
print("3️⃣ 准备测试故事...")
story_text = """
第一章：新的开始

林晓是一个28岁的女律师，聪明干练，但内心孤独。她刚刚结束了一段失败的感情，决定重新开始。

某天，她在法庭上遇到了对手律师陈浩，一个35岁的成熟男人，沉稳冷静，眼神锐利。两人在法庭上针锋相对。

林晓的助理小王是个22岁的实习生，天真活泼，总是给林晓带来欢乐。

陈浩的秘书李姐是个50岁的中年女性，经验丰富，对陈浩照顾有加。

法官张法官是个60岁的老人，公正严明，德高望重。
"""

print(f"   故事长度: {len(story_text)} 字符")
print(f"   预期人物数: 5人")
print()

# 4. 提取人物
print("4️⃣ 提取人物...")
try:
    characters_data = ai_service.extract_characters(story_text)
    
    if not characters_data:
        print("❌ 未提取到任何人物")
        exit(1)
    
    print(f"✅ 成功提取 {len(characters_data)} 个人物")
    print()
    
    # 5. 创建Character对象
    print("5️⃣ 创建Character对象...")
    character_list = []
    
    for i, data in enumerate(characters_data, 1):
        print(f"   处理第 {i} 个人物: {data.get('name', '未知')}")
        
        char = Character(name=data.get("name", "未知"))
        char.profile = CharacterProfile(
            role=data.get("role", ""),
            gender=data.get("gender", ""),
            age_hint=data.get("age_hint", ""),
            identity=data.get("identity", ""),
            personality=data.get("personality", []),
            atmosphere=data.get("atmosphere", ""),
            story_role=data.get("story_role", ""),
            appearance_hints=data.get("appearance_hints", ""),
        )
        character_list.append(char)
    
    print(f"✅ 成功创建 {len(character_list)} 个Character对象")
    print()
    
    # 6. 显示结果
    print("6️⃣ 人物列表:")
    print("=" * 70)
    
    role_icons = {"主角": "⭐", "反派": "👿", "配角": "👤", "龙套": "·"}
    
    for char in character_list:
        icon = role_icons.get(char.profile.role, "")
        display = f"{icon} {char.name}" if icon else char.name
        
        print(f"\n{display}")
        print("-" * 70)
        
        if char.profile.role:
            print(f"📌 角色：{char.profile.role}")
        if char.profile.gender:
            print(f"👤 性别：{char.profile.gender}")
        if char.profile.age_hint:
            print(f"🎂 年龄：{char.profile.age_hint}")
        if char.profile.identity:
            print(f"💼 身份：{char.profile.identity}")
        if char.profile.personality:
            p = char.profile.personality
            print(f"💫 性格：{', '.join(p) if isinstance(p, list) else p}")
        if char.profile.atmosphere:
            print(f"🌟 气质：{char.profile.atmosphere}")
        if char.profile.story_role:
            print(f"📖 作用：{char.profile.story_role}")
    
    print()
    print("=" * 70)
    print("🎉 测试完全通过！")
    print("=" * 70)
    print()
    print("💡 提示:")
    print("   - 提取人物功能正常工作")
    print("   - 可以在应用中使用此功能")
    print("   - 如果应用中仍有问题，请检查:")
    print("     1. 故事内容是否为空")
    print("     2. API配置是否正确")
    print("     3. 控制台是否有错误信息")
    
except Exception as e:
    print(f"❌ 测试失败: {e}")
    print()
    
    import traceback
    print("详细错误:")
    traceback.print_exc()
    
    print()
    print("=" * 70)
    print("💡 故障排查:")
    print("=" * 70)
    print("1. 检查 custom_api_presets.json 配置")
    print("2. 确认API Key有效")
    print("3. 测试网络连接")
    print("4. 查看上面的详细错误信息")

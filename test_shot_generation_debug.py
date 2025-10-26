"""
调试分镜图片生成失败的问题
直接模拟UI中的生成流程
"""

import os
import json
from pathlib import Path

print("\n" + "="*70)
print("分镜图片生成调试")
print("="*70)

# 1. 加载测试项目
project_dir = Path("projects/你好_20251015_205648")
shots_file = project_dir / "director" / "shots.json"
char_file = project_dir / "characters" / "characters_info.json"

if not shots_file.exists():
    print("[ERROR] 分镜文件不存在")
    exit(1)

# 加载分镜
with open(shots_file, 'r', encoding='utf-8') as f:
    shots_data = json.load(f)
    shots = shots_data.get('shots', [])

print(f"[OK] 加载了 {len(shots)} 个分镜")

# 加载人物信息
character_details = {}
if char_file.exists():
    with open(char_file, 'r', encoding='utf-8') as f:
        char_data = json.load(f)
        character_details = char_data.get('characters', {})
    print(f"[OK] 加载了 {len(character_details)} 个人物")

# 2. 测试生成第一个分镜
first_shot = shots[0]
print(f"\n{'='*70}")
print(f"测试第一个分镜:")
print(f"  编号: {first_shot.get('shot_number')}")
print(f"  类型: {first_shot.get('shot_type')}")
print(f"  人物: {first_shot.get('characters')}")
print(f"  位置: {first_shot.get('location')}")
print(f"{'='*70}\n")

# 3. 构建提示词
try:
    from src.gui.mixins.director_modules.prompt_adapter import PromptAdapter
    
    characters = first_shot.get('characters', [])
    scene_desc = first_shot.get('visual_description', '')
    shot_type = first_shot.get('shot_type', '')
    action = first_shot.get('action', '')
    
    # 准备人物详情
    char_details_for_shot = {}
    for char_name in characters:
        if char_name in character_details:
            char_details_for_shot[char_name] = {
                'description': character_details[char_name].get('description', ''),
                'appearance': character_details[char_name].get('description', '')
            }
    
    print("[步骤1] 构建SD提示词...")
    prompt, negative = PromptAdapter.build_prompt_for_api(
        api_type="sd",
        scene_description=scene_desc,
        characters=characters,
        character_details=char_details_for_shot,
        shot_type=shot_type,
        action=action,
        is_img2img=False,
        consistency_mode=True
    )
    
    print(f"[OK] 提示词长度: {len(prompt)}")
    print(f"\n正面提示词:\n{prompt}\n")
    print(f"负面提示词:\n{negative}\n")
    
except Exception as e:
    print(f"[ERROR] 构建提示词失败: {e}")
    import traceback
    traceback.print_exc()
    exit(1)

# 4. 测试SD生成
try:
    from src.clients.sd_client import StableDiffusionClient
    
    print("[步骤2] 连接SD服务...")
    client = StableDiffusionClient()
    print("[OK] SD客户端创建成功")
    
    print("\n[步骤3] 生成图片...")
    images = client.txt2img(
        prompt=prompt,
        negative_prompt=negative,
        width=768,
        height=512,
        steps=35,
        cfg_scale=8.5,
        seed=12345
    )
    
    if images and len(images) > 0:
        output_dir = project_dir / "director" / "shots"
        output_dir.mkdir(parents=True, exist_ok=True)
        
        output_path = output_dir / "test_shot_001_debug.png"
        images[0].save(output_path)
        
        print(f"\n[SUCCESS] 图片生成成功！")
        print(f"保存路径: {output_path}")
        print(f"文件大小: {os.path.getsize(output_path) / 1024:.2f} KB")
    else:
        print("[FAIL] SD返回空结果")
        
except Exception as e:
    print(f"\n[ERROR] SD生成失败: {e}")
    import traceback
    traceback.print_exc()
    
print("\n" + "="*70)
print("调试完成")
print("="*70)

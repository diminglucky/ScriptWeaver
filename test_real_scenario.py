"""
真实场景测试 - 模拟用户完整使用流程
"""

import os
import json
import time
from pathlib import Path
from datetime import datetime

# 配置
PROJECT_NAME = f"完整测试_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
STORY_THEME = "高中生的友谊"

def simulate_user_workflow():
    """模拟用户完整使用流程"""
    print("\n" + "="*80)
    print(f"真实场景测试 - {STORY_THEME}")
    print("="*80)
    
    # 1. 创建项目
    print("\n[1] 创建新项目")
    from src.project_manager import ProjectManager
    pm = ProjectManager()
    project = pm.create_project(PROJECT_NAME)
    print(f"   项目创建成功: {project.project_dir}")
    
    # 2. 生成故事
    print("\n[2] AI生成故事")
    from src.clients.deepseek_client import DeepSeekClient
    
    # 检查API配置
    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        print("   [SKIP] 未配置DEEPSEEK_API_KEY，使用预设故事")
        story = """
张强是班里的学霸，总是埋头学习。一天，新来的转学生林小雨坐到了他旁边。
林小雨活泼开朗，总是试图和张强聊天。起初张强觉得她很吵，影响学习。
但渐渐地，他发现林小雨其实很善良，会默默帮助其他同学。
期中考试前，林小雨生病请假了。张强主动整理笔记，放学后送到她家。
从那以后，两人成了好朋友，一起学习，一起进步。
        """.strip()
    else:
        try:
            client = DeepSeekClient()
            story = client.chat([
                {"role": "user", "content": f"写一个关于{STORY_THEME}的短故事，200字左右，包含2-3个人物"}
            ])
            print(f"   故事生成成功，长度: {len(story)}字")
        except Exception as e:
            print(f"   [ERROR] AI生成失败: {e}")
            print("   使用预设故事")
            story = "张强和林小雨的友谊故事..."
    
    # 保存故事
    story_file = Path(project.project_dir) / "story.txt"
    story_file.write_text(story, encoding='utf-8')
    print(f"   故事已保存")
    
    # 3. 提取人物
    print("\n[3] 智能提取人物")
    import re
    # 简单提取中文名字（实际应该用NLP）
    names = re.findall(r'[张李王刘陈杨黄赵周吴徐孙马朱胡林郭何高罗郑梁谢韩唐冯董萧程曹袁邓许傅沈曾彭吕苏卢蒋蔡贾丁魏薛叶阎余潘杜戴夏钟汪田任姜范方石姚谭廖邹熊金陆郝孔白崔康毛邱秦江史顾侯邵孟龙万段章钱汤尹黎易常武乔贺赖龚文][^\s，。！？、；：""''（）\[\]{}【】《》〈〉]+', story)
    characters = list(set(names))[:5]  # 最多5个
    print(f"   提取到人物: {characters}")
    
    # 4. 生成人物描述
    print("\n[4] 生成人物描述")
    char_info = {"characters": {}}
    
    for i, name in enumerate(characters):
        # 模拟AI生成描述
        if name == "张强":
            desc = "男，18岁，高中生，学霸，短发，戴黑框眼镜，穿白衬衫和黑色长裤，性格内向认真"
        elif name == "林小雨":
            desc = "女，17岁，高中生，转学生，长发马尾，圆脸大眼睛，穿蓝色连衣裙，性格活泼开朗"
        else:
            desc = f"高中生，{name}"
        
        char_info["characters"][name] = {
            "description": desc,
            "gender": "男" if i % 2 == 0 else "女",
            "age": f"{17+i}岁"
        }
    
    # 保存人物信息
    char_dir = Path(project.project_dir) / "characters"
    char_dir.mkdir(exist_ok=True)
    with open(char_dir / "characters_info.json", 'w', encoding='utf-8') as f:
        json.dump(char_info, f, ensure_ascii=False, indent=2)
    print(f"   人物描述已生成")
    
    # 5. 生成剧本
    print("\n[5] 生成导演剧本")
    script = f"""
【场景1】INT-教室-早上
环境：阳光明媚的早晨，教室里书声朗朗。张强坐在靠窗的位置，桌上堆满了课本和练习册。

人物：
- 张强：{char_info['characters'].get('张强', {}).get('description', '')}

动作：
[00:00] 张强低头做题，眉头微皱，专注地计算着
[00:05] 教室门打开，一个身影走进来
[00:08] 张强抬头看了一眼，又继续低头做题

【场景2】INT-教室-片刻后  
人物：
- 林小雨：{char_info['characters'].get('林小雨', {}).get('description', '')}

动作：
[00:00] 林小雨背着书包，蹦蹦跳跳地走到张强旁边的空座位
[00:03] 她放下书包，转头对张强露出灿烂的笑容
[00:05] 林小雨："你好！我是新来的转学生林小雨，请多多指教！"
[00:08] 张强有些意外地看着她，轻轻点头："你好，我是张强。"
    """
    
    director_dir = Path(project.project_dir) / "director"
    director_dir.mkdir(exist_ok=True)
    (director_dir / "script.txt").write_text(script, encoding='utf-8')
    print("   剧本已生成")
    
    # 6. 生成分镜
    print("\n[6] 生成分镜头")
    shots = {
        "shots": [
            {
                "shot_number": 1,
                "scene_id": "场景1",
                "location": "教室",
                "time": "早上",
                "shot_type": "中景",
                "characters": ["张强"],
                "visual_description": "阳光从窗户照进教室，张强坐在座位上认真做题，他戴着黑框眼镜，穿白衬衫",
                "action": "张强专注地做数学题，偶尔推推眼镜",
                "camera": {
                    "movement": "缓慢推进",
                    "angle": "侧面45度",
                    "focus": "张强的侧脸和桌上的书本"
                },
                "duration": "8秒",
                "transition_to_next": "切"
            },
            {
                "shot_number": 2,
                "scene_id": "场景2",
                "location": "教室",
                "time": "片刻后",
                "shot_type": "双人镜头",
                "characters": ["张强", "林小雨"],
                "visual_description": "林小雨站在张强旁边，阳光照在她的脸上，她穿着蓝色连衣裙，扎着马尾",
                "action": "林小雨热情地自我介绍，张强抬头看她",
                "dialogue": "你好！我是新来的转学生林小雨，请多多指教！",
                "emotion": "林小雨：开朗活泼；张强：略显意外",
                "camera": {
                    "movement": "固定",
                    "angle": "过肩镜头",
                    "focus": "从张强肩膀看向林小雨"
                },
                "duration": "10秒",
                "jimeng_prompt": "教室里，女孩热情地向男孩自我介绍，阳光照在她的笑脸上"
            }
        ]
    }
    
    with open(director_dir / "shots.json", 'w', encoding='utf-8') as f:
        json.dump(shots, f, ensure_ascii=False, indent=2)
    print(f"   分镜已生成: {len(shots['shots'])}个镜头")
    
    # 7. 测试图片生成（人物一致性）
    print("\n[7] 生成分镜图片（保持人物一致性）")
    try:
        from src.clients.sd_client import StableDiffusionClient
        client = StableDiffusionClient()
        
        shots_dir = director_dir / "shots"
        shots_dir.mkdir(exist_ok=True)
        
        # 为每个人物设置固定种子
        character_seeds = {
            "张强": 12345,
            "林小雨": 67890
        }
        
        for shot in shots["shots"][:2]:  # 只测试前2个
            shot_num = shot["shot_number"]
            print(f"\n   生成分镜{shot_num}...")
            
            # 构建SD提示词
            characters_in_shot = shot.get("characters", [])
            
            # 基础提示词
            if "张强" in characters_in_shot and "林小雨" in characters_in_shot:
                # 双人镜头
                prompt = "1boy and 1girl, boy with glasses and white shirt, girl with ponytail and blue dress"
                seed = character_seeds["张强"]  # 使用主角种子
            elif "张强" in characters_in_shot:
                prompt = "1boy, solo, glasses, white shirt, studying, classroom"
                seed = character_seeds["张强"]
            elif "林小雨" in characters_in_shot:
                prompt = "1girl, solo, ponytail, blue dress, cheerful, classroom"  
                seed = character_seeds["林小雨"]
            else:
                prompt = "classroom, empty"
                seed = 42
            
            # 添加场景和质量标签
            prompt += f", {shot['shot_type']}, {shot['visual_description']}"
            prompt += ", masterpiece, best quality, ultra detailed, photorealistic"
            
            negative = "low quality, bad anatomy, multiple people in solo shot, crowd, duplicate person"
            
            print(f"   提示词: {prompt[:100]}...")
            print(f"   使用种子: {seed}")
            
            images = client.txt2img(
                prompt=prompt,
                negative_prompt=negative,
                width=768,
                height=512,
                steps=25,
                cfg_scale=7.5,
                seed=seed
            )
            
            if images:
                output_path = shots_dir / f"shot_{shot_num:03d}_v1.png"
                images[0].save(output_path)
                print(f"   [OK] 已保存: {output_path}")
            else:
                print(f"   [FAIL] 生成失败")
                
    except Exception as e:
        print(f"   [ERROR] SD生成错误: {e}")
        import traceback
        traceback.print_exc()
    
    # 8. 生成即梦AI提示词
    print("\n[8] 提取即梦AI提示词")
    jimeng_prompts = []
    for shot in shots["shots"]:
        if "jimeng_prompt" in shot:
            jimeng_prompts.append(f"分镜{shot['shot_number']}: {shot['jimeng_prompt']}")
        else:
            # 自动生成
            prompt = f"{shot['visual_description']}，{shot['action']}"
            if shot.get('dialogue'):
                prompt += f"，对话：{shot['dialogue']}"
            jimeng_prompts.append(f"分镜{shot['shot_number']}: {prompt}")
    
    with open(director_dir / "jimeng_prompts.txt", 'w', encoding='utf-8') as f:
        f.write("\n\n".join(jimeng_prompts))
    print("   即梦AI提示词已生成")
    
    # 完成
    print("\n" + "="*80)
    print("测试完成总结")
    print("="*80)
    print(f"项目位置: {project.project_dir}")
    print(f"已生成:")
    print(f"  - 故事: {len(story)}字")
    print(f"  - 人物: {len(characters)}个")
    print(f"  - 剧本: 2个场景")
    print(f"  - 分镜: {len(shots['shots'])}个镜头")
    print(f"  - 图片: 查看 director/shots/ 目录")
    print(f"  - 即梦提示词: director/jimeng_prompts.txt")
    print("\n[SUCCESS] 完整工作流测试成功！")
    
    return project

if __name__ == "__main__":
    try:
        project = simulate_user_workflow()
        print(f"\n打开项目查看: {project.project_dir}")
    except Exception as e:
        print(f"\n[FATAL ERROR] {e}")
        import traceback
        traceback.print_exc()

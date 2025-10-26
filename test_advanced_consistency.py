"""
测试高级人物一致性系统
"""

from pathlib import Path
from src.gui.mixins.director_modules.advanced_consistency import AdvancedConsistencySystem
from src.clients.sd_client import StableDiffusionClient

def test_advanced_consistency():
    """测试高级一致性"""
    print("\n" + "="*60)
    print("高级人物一致性测试")
    print("="*60)
    
    # 测试项目
    project_dir = "projects/测试项目_workflow"
    
    # 创建系统
    system = AdvancedConsistencySystem(project_dir)
    client = StableDiffusionClient()
    
    # 1. 生成张强的参考图像
    print("\n[步骤1] 生成人物参考图像")
    ref_path = system.generate_character_reference("张强", client)
    if ref_path:
        print(f"[OK] 参考图像: {ref_path}")
    else:
        print("[FAIL] 生成失败")
        return
    
    # 2. 使用参考图像生成不同动作
    print("\n[步骤2] 生成不同动作的分镜")
    
    test_shots = [
        {
            "shot_number": 1,
            "characters": ["张强"],
            "action": "sitting and reading",
            "shot_type": "中景",
            "visual_description": "张强坐在教室里看书",
            "location": "classroom"
        },
        {
            "shot_number": 2,
            "characters": ["张强"],
            "action": "standing and thinking",
            "shot_type": "特写",
            "visual_description": "张强站着思考问题",
            "location": "classroom"
        },
        {
            "shot_number": 3,
            "characters": ["张强"],
            "action": "walking",
            "shot_type": "全景",
            "visual_description": "张强在走廊里走路",
            "location": "hallway"
        }
    ]
    
    for shot in test_shots:
        print(f"\n测试分镜{shot['shot_number']}: {shot['action']}")
        result = system.generate_consistent_shot(shot, client, shot['shot_number'])
        if result:
            print(f"[OK] 生成成功: {result}")
        else:
            print("[FAIL] 生成失败")
    
    print("\n" + "="*60)
    print("测试完成！")
    print("请检查生成的图片，对比人物面部是否保持一致")
    print(f"参考图像: {project_dir}/characters/references/张强_reference.png")
    print(f"分镜图片: {project_dir}/director/shots/")

if __name__ == "__main__":
    test_advanced_consistency()

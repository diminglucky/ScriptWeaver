"""
诊断图片生成失败的原因
"""

import os
import sys
from pathlib import Path

print("\n" + "="*60)
print("图片生成失败诊断")
print("="*60)

# 1. 检查SD服务
print("\n[1] 检查 Stable Diffusion 服务")
try:
    from src.clients.sd_client import StableDiffusionClient
    client = StableDiffusionClient()
    
    # 测试连接
    import requests
    response = requests.get(f"{client.base_url}/sdapi/v1/sd-models", timeout=5)
    if response.status_code == 200:
        models = response.json()
        print(f"[OK] SD服务运行正常")
        print(f"   可用模型数量: {len(models)}")
        if models:
            print(f"   当前模型: {models[0].get('title', 'unknown')}")
    else:
        print(f"[FAIL] SD服务响应异常: {response.status_code}")
except requests.exceptions.ConnectionError:
    print("[FAIL] 无法连接到SD服务")
    print("   请确保:")
    print("   1. SD WebUI已启动")
    print("   2. 使用 --api 参数启动")
    print("   3. 端口号为 7860")
except Exception as e:
    print(f"[ERROR] 检查失败: {e}")

# 2. 检查API配置
print("\n[2] 检查 API 配置")
try:
    # 检查配置文件
    config_files = [
        "custom_api_presets.json",
        "custom_image_api_presets.json"
    ]
    
    for config_file in config_files:
        if os.path.exists(config_file):
            print(f"[OK] 找到配置文件: {config_file}")
            import json
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
                print(f"   配置数量: {len(config)}")
        else:
            print(f"[WARN] 未找到配置文件: {config_file}")
            
except Exception as e:
    print(f"[ERROR] 读取配置失败: {e}")

# 3. 检查项目结构
print("\n[3] 检查项目结构")
try:
    test_project = Path("projects/你好_20251015_205648")
    
    if test_project.exists():
        print(f"[OK] 找到测试项目: {test_project}")
        
        # 检查关键目录
        dirs_to_check = [
            test_project / "director",
            test_project / "director" / "shots",
            test_project / "characters"
        ]
        
        for dir_path in dirs_to_check:
            if dir_path.exists():
                print(f"[OK] {dir_path.relative_to(test_project)}")
            else:
                print(f"[WARN] 缺少目录: {dir_path.relative_to(test_project)}")
        
        # 检查分镜数据
        shots_file = test_project / "director" / "shots.json"
        if shots_file.exists():
            import json
            with open(shots_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                shots = data.get('shots', [])
                print(f"[OK] 分镜数据: {len(shots)} 个分镜")
                if shots:
                    first_shot = shots[0]
                    print(f"   第一个分镜:")
                    print(f"   - 编号: {first_shot.get('shot_number')}")
                    print(f"   - 类型: {first_shot.get('shot_type')}")
                    print(f"   - 人物: {first_shot.get('characters')}")
        else:
            print("[WARN] 未找到分镜数据")
            
    else:
        print(f"[FAIL] 未找到测试项目: {test_project}")
        
except Exception as e:
    print(f"[ERROR] 检查项目失败: {e}")

# 4. 测试简单生成
print("\n[4] 测试简单图片生成")
try:
    from src.clients.sd_client import StableDiffusionClient
    client = StableDiffusionClient()
    
    print("   正在生成测试图片...")
    images = client.txt2img(
        prompt="1boy, simple background, test image",
        negative_prompt="low quality",
        width=512,
        height=512,
        steps=10,  # 快速测试
        seed=12345
    )
    
    if images and len(images) > 0:
        test_path = "test_generation.png"
        images[0].save(test_path)
        print(f"[OK] 测试生成成功: {test_path}")
        print("   SD服务工作正常")
    else:
        print("[FAIL] 生成返回空结果")
        
except Exception as e:
    print(f"[ERROR] 测试生成失败: {e}")
    import traceback
    traceback.print_exc()

# 5. 检查依赖
print("\n[5] 检查Python依赖")
required_packages = [
    "requests",
    "Pillow",
    "tkinter"
]

for pkg in required_packages:
    try:
        if pkg == "tkinter":
            import tkinter
        else:
            __import__(pkg)
        print(f"[OK] {pkg}")
    except ImportError:
        print(f"[FAIL] 缺少: {pkg}")

# 总结
print("\n" + "="*60)
print("诊断完成")
print("="*60)
print("\n如果SD服务连接失败，请运行以下命令启动SD:")
print("cd <your-sd-webui-path>")
print("./webui.bat --api")
print("\n或者:")
print("python launch.py --api")
print("\n然后重新运行此诊断脚本。")


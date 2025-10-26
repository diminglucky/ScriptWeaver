"""
直接测试图片生成 - 最简单的验证
"""

import os
from pathlib import Path

def test_sd_connection():
    """测试1: SD连接"""
    print("\n=== 测试1: 检查SD连接 ===")
    try:
        from src.clients.sd_client import StableDiffusionClient
        client = StableDiffusionClient(base_url="http://localhost:7860")
        print("[OK] SD客户端初始化成功")
        return True
    except Exception as e:
        print(f"[ERROR] SD连接失败: {e}")
        print("\n请检查:")
        print("1. SD WebUI是否已启动")
        print("2. 启动命令是否包含 --api 参数")
        print("3. 访问地址是否为 http://localhost:7860")
        return False

def test_simple_generation():
    """测试2: 简单生成"""
    print("\n=== 测试2: 生成简单图片 ===")
    try:
        from src.clients.sd_client import StableDiffusionClient
        client = StableDiffusionClient(base_url="http://localhost:7860")
        
        prompt = "1boy, male focus, short black hair, white shirt, standing, looking at viewer, masterpiece, best quality, photorealistic"
        negative = "low quality, bad anatomy, multiple people, crowd"
        
        print(f"提示词: {prompt}")
        print("生成中...")
        
        images = client.txt2img(
            prompt=prompt,
            negative_prompt=negative,
            width=512,
            height=512,
            steps=20,
            cfg_scale=7.0,
            seed=42
        )
        
        if images and len(images) > 0:
            output_path = "test_output.png"
            images[0].save(output_path)
            print(f"[OK] 图片已保存: {output_path}")
            print(f"[OK] 文件大小: {os.path.getsize(output_path)} bytes")
            return True
        else:
            print("[ERROR] 未返回图片")
            return False
            
    except Exception as e:
        print(f"[ERROR] 生成失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_character_generation():
    """测试3: 人物一致性生成"""
    print("\n=== 测试3: 人物一致性测试 ===")
    try:
        from src.clients.sd_client import StableDiffusionClient
        client = StableDiffusionClient(base_url="http://localhost:7860")
        
        # 固定人物描述
        char_desc = "1boy, male focus, 18 years old, short black hair, brown eyes, white shirt, black pants"
        
        # 不同动作
        actions = [
            "standing, hands in pockets",
            "sitting, reading a book",
            "walking, looking back"
        ]
        
        base_seed = 12345  # 固定种子保证一致性
        
        for i, action in enumerate(actions):
            prompt = f"{char_desc}, {action}, masterpiece, best quality, photorealistic"
            negative = "low quality, bad anatomy, multiple people, different person, inconsistent face"
            
            print(f"\n动作 {i+1}: {action}")
            
            images = client.txt2img(
                prompt=prompt,
                negative_prompt=negative,
                width=512,
                height=512,
                steps=25,
                cfg_scale=7.5,
                seed=base_seed  # 同一个种子
            )
            
            if images:
                output_path = f"test_char_{i+1}.png"
                images[0].save(output_path)
                print(f"  [OK] 已保存: {output_path}")
            else:
                print(f"  [ERROR] 生成失败")
                return False
        
        print("\n[OK] 一致性测试完成，请对比 test_char_1.png, test_char_2.png, test_char_3.png")
        return True
        
    except Exception as e:
        print(f"[ERROR] 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    print("=" * 60)
    print("图片生成系统测试")
    print("=" * 60)
    
    results = []
    
    # 测试1
    results.append(("SD连接", test_sd_connection()))
    if not results[-1][1]:
        print("\n[FAIL] SD未连接，无法继续测试")
        return
    
    # 测试2
    results.append(("简单生成", test_simple_generation()))
    
    # 测试3
    if results[-1][1]:
        results.append(("人物一致性", test_character_generation()))
    
    # 总结
    print("\n" + "=" * 60)
    print("测试总结")
    print("=" * 60)
    for name, result in results:
        status = "[OK] 通过" if result else "[ERROR] 失败"
        print(f"{name}: {status}")
    
    passed = sum(1 for _, r in results if r)
    total = len(results)
    print(f"\n通过率: {passed}/{total}")
    
    if passed == total:
        print("\n[SUCCESS] 所有测试通过！系统工作正常")
    else:
        print("\n[WARN]  部分测试失败，请根据错误信息排查")

if __name__ == "__main__":
    main()


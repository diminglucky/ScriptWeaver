#!/usr/bin/env python3
"""
获取 API 支持的所有模型列表
"""

import requests
import json

# API 配置
API_KEY = "kg-HFdtg7L1tr7dNh3j4UOcjQUkCb3mJT5J"
BASE_URL = "https://superai.dihappy.cfd/v1"

print("=" * 80)
print("🔍 获取 API 支持的模型列表")
print("=" * 80)

try:
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "User-Agent": "Mozilla/5.0"
    }
    
    # 调用 /models 端点获取模型列表
    response = requests.get(
        f"{BASE_URL}/models",
        headers=headers,
        timeout=10
    )
    
    if response.status_code == 200:
        result = response.json()
        
        # 提取模型 ID
        if "data" in result:
            models = [model["id"] for model in result["data"]]
            print(f"\n✅ 成功获取 {len(models)} 个模型：\n")
            
            for i, model in enumerate(models, 1):
                print(f"{i:3d}. {model}")
            
            # 保存到文件
            with open("available_models.json", "w", encoding="utf-8") as f:
                json.dump({"models": models}, f, indent=2, ensure_ascii=False)
            
            print(f"\n💾 已保存到 available_models.json")
            
            # 生成 Python 列表格式
            print(f"\n📋 Python 列表格式：")
            print(f"models = {models}")
            
        else:
            print(f"⚠️  响应格式不符合预期: {result}")
    else:
        print(f"❌ 请求失败 ({response.status_code}): {response.text}")
        
except Exception as e:
    print(f"❌ 错误: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 80)

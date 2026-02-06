#!/usr/bin/env python3
"""
验证所有补丁是否正确应用

检查所有需要补丁的文件中是否包含正确的补丁代码
"""

import os
from pathlib import Path

def check_patch(file_path: str, search_text: str, description: str) -> bool:
    """检查文件中是否包含补丁代码"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            if search_text in content:
                print(f"✅ {description}")
                return True
            else:
                print(f"❌ {description} - 未找到补丁")
                return False
    except Exception as e:
        print(f"❌ {description} - 读取文件失败: {e}")
        return False

def main():
    print("=" * 60)
    print("🔍 验证补丁应用情况")
    print("=" * 60)
    print()
    
    patches = [
        # 故事生成模块
        ("src/gui/mixins/story_modules/outline_generator.py", 
         '🔧 [补丁] 强制使用 API', 
         "故事大纲生成"),
        
        ("src/gui/mixins/story_modules/story_generator.py", 
         '🔧 [补丁] 强制使用 API', 
         "故事正文生成"),
        
        # 图片生成模块
        ("src/gui/mixins/image_modules/char_extract.py", 
         '🔧 [补丁] 提取人物使用 API', 
         "提取人物"),
        
        ("src/gui/mixins/image_modules/char_description.py", 
         '🔧 [补丁] 设计外貌使用 API', 
         "设计人物外貌"),
        
        ("src/gui/mixins/image_modules/prompt_ops.py", 
         '🔧 [补丁] 优化提示词使用 API', 
         "优化提示词"),
        
        ("src/gui/mixins/image_modules/shot_manager.py", 
         '🔧 [补丁] 生成分镜使用 API', 
         "生成分镜"),
        
        ("src/gui/mixins/image_modules/shot_manager.py", 
         '🔧 [补丁] 生成图片描述使用 API', 
         "生成图片描述"),
        
        ("src/gui/mixins/image_modules/shot_manager.py", 
         '🔧 [补丁] 转换分镜描述使用 API', 
         "转换分镜描述"),
    ]
    
    print("📋 检查补丁文件:")
    print()
    
    results = []
    for file_path, search_text, description in patches:
        result = check_patch(file_path, search_text, description)
        results.append(result)
    
    print()
    print("=" * 60)
    print("📊 统计结果")
    print("=" * 60)
    
    total = len(results)
    success = sum(results)
    failed = total - success
    
    print(f"总计: {total} 个补丁")
    print(f"✅ 成功: {success} 个")
    print(f"❌ 失败: {failed} 个")
    print()
    
    if failed == 0:
        print("🎉 所有补丁都已正确应用！")
        print()
        print("💡 下一步:")
        print("   1. 运行应用: python run_modern_app.py")
        print("   2. 测试各项功能")
        print("   3. 查看控制台输出，确认显示 '🔧 [补丁] ... 使用 API: 自定义'")
        return 0
    else:
        print("⚠️  部分补丁未正确应用，请检查上述失败项")
        return 1

if __name__ == "__main__":
    exit(main())

"""清理代码中的 DEBUG 打印语句"""

import os
import re
from pathlib import Path

def clean_debug_prints(file_path):
    """清理文件中的 DEBUG 打印语句"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        lines = content.split('\n')
        cleaned_lines = []
        
        for line in lines:
            # 跳过包含 [DEBUG] 的 print 语句
            if 'print(' in line and '[DEBUG]' in line:
                # 保留缩进，添加注释
                indent = len(line) - len(line.lstrip())
                cleaned_lines.append(' ' * indent + f'# DEBUG: {line.strip()}')
            else:
                cleaned_lines.append(line)
        
        cleaned_content = '\n'.join(cleaned_lines)
        
        if cleaned_content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(cleaned_content)
            return True, file_path
        
        return False, None
        
    except Exception as e:
        print(f"❌ 处理文件失败 {file_path}: {e}")
        return False, None

def main():
    """主函数"""
    print("=" * 60)
    print("清理 DEBUG 打印语句")
    print("=" * 60)
    
    # 要处理的目录
    directories = [
        'src/gui/mixins/director_modules',
        'src/clients',
        'src/gui/mixins/image_modules',
    ]
    
    modified_files = []
    total_files = 0
    
    for directory in directories:
        dir_path = Path(directory)
        if not dir_path.exists():
            print(f"⚠️  目录不存在: {directory}")
            continue
        
        print(f"\n📂 处理目录: {directory}")
        
        for py_file in dir_path.rglob('*.py'):
            total_files += 1
            modified, file_path = clean_debug_prints(py_file)
            
            if modified:
                modified_files.append(file_path)
                print(f"  ✅ 已清理: {py_file.relative_to(dir_path.parent)}")
    
    print("\n" + "=" * 60)
    print(f"处理完成！")
    print(f"  • 总文件数: {total_files}")
    print(f"  • 修改文件数: {len(modified_files)}")
    print("=" * 60)
    
    if modified_files:
        print("\n修改的文件列表：")
        for f in modified_files:
            print(f"  - {f}")

if __name__ == "__main__":
    main()


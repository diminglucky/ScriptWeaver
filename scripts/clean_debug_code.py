#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
清理调试代码脚本
自动移除所有DEBUG print语句并替换为logging
"""

import re
import sys
from pathlib import Path
from typing import List, Tuple

# 要处理的文件扩展名
PYTHON_EXTENSIONS = {'.py'}

# 要排除的目录
EXCLUDE_DIRS = {
    '__pycache__',
    '.git',
    'venv',
    'env',
    '.venv',
    'node_modules',
    'build',
    'dist',
    '.pytest_cache',
    'htmlcov',
    '.coverage'
}

# 要排除的文件
EXCLUDE_FILES = {
    'clean_debug_prints.py',
    'remove_debug_prints.py',
    'clean_debug_code.py'
}


def should_process_file(file_path: Path) -> bool:
    """判断是否应该处理该文件"""
    # 检查扩展名
    if file_path.suffix not in PYTHON_EXTENSIONS:
        return False
    
    # 检查是否在排除列表中
    if file_path.name in EXCLUDE_FILES:
        return False
    
    # 检查是否在排除目录中
    for part in file_path.parts:
        if part in EXCLUDE_DIRS:
            return False
    
    return True


def find_python_files(root_dir: Path) -> List[Path]:
    """查找所有Python文件"""
    python_files = []
    
    for file_path in root_dir.rglob('*.py'):
        if should_process_file(file_path):
            python_files.append(file_path)
    
    return python_files


def has_debug_prints(content: str) -> bool:
    """检查是否包含DEBUG打印语句"""
    patterns = [
        r'print\(f?["\']\[DEBUG\]',
        r'print\(f?["\']\[INFO\]',
        r'print\(f?["\']\[OK\]',
        r'print\(f?"\[DEBUG\]',
        r'print\("\[DEBUG\]',
    ]
    
    for pattern in patterns:
        if re.search(pattern, content):
            return True
    return False


def clean_debug_prints(content: str, file_path: Path) -> Tuple[str, int]:
    """
    清理调试打印语句
    
    Returns:
        (cleaned_content, removed_count)
    """
    original_content = content
    removed_count = 0
    
    # 检查是否需要导入logging
    needs_logging_import = False
    
    # 模式1: print(f"[DEBUG] ...")
    pattern1 = r'print\(f?"\[DEBUG\](.*?)"\)'
    matches = re.findall(pattern1, content)
    if matches:
        needs_logging_import = True
        content = re.sub(pattern1, '', content)
        removed_count += len(matches)
    
    # 模式2: print("[DEBUG] ...")
    pattern2 = r'print\("\[DEBUG\](.*?)"\)'
    matches = re.findall(pattern2, content)
    if matches:
        needs_logging_import = True
        content = re.sub(pattern2, '', content)
        removed_count += len(matches)
    
    # 模式3: print(f"[INFO] ...")
    pattern3 = r'print\(f?"\[INFO\](.*?)"\)'
    matches = re.findall(pattern3, content)
    if matches:
        needs_logging_import = True
        # 转换为logger.info
        for match in matches:
            new_line = f'logger.info(f"{match.strip()}")'
            content = re.sub(
                r'print\(f?"\[INFO\](.*?)"\)',
                lambda m: f'logger.info(f"{m.group(1).strip()}")',
                content,
                count=1
            )
        removed_count += len(matches)
    
    # 模式4: print("[INFO] ...")
    pattern4 = r'print\("\[INFO\](.*?)"\)'
    matches = re.findall(pattern4, content)
    if matches:
        needs_logging_import = True
        content = re.sub(
            pattern4,
            lambda m: f'logger.info("{m.group(1).strip()}")',
            content
        )
        removed_count += len(matches)
    
    # 移除多余的空行（连续3个以上空行）
    content = re.sub(r'\n{4,}', '\n\n\n', content)
    
    # 如果需要logging，添加导入
    if needs_logging_import and 'import logging' not in content:
        # 查找文件开头的导入位置
        import_match = re.search(r'(^from __future__.*?\n)', content, re.MULTILINE)
        if import_match:
            # 在__future__导入后添加
            pos = import_match.end()
            content = content[:pos] + '\nimport logging\n' + content[pos:]
        else:
            # 在文件开头添加
            import_match = re.search(r'(^import |^from )', content, re.MULTILINE)
            if import_match:
                pos = import_match.start()
                content = content[:pos] + 'import logging\n\n' + content[pos:]
            else:
                content = 'import logging\n\n' + content
        
        # 添加logger实例（如果还没有）
        if 'logger = logging.getLogger' not in content:
            # 在类定义后或函数定义前添加logger
            module_name = file_path.stem
            logger_line = f'\nlogger = logging.getLogger(__name__)\n'
            
            # 在最后一个import语句后添加
            import_block = re.findall(r'(^import .*|^from .* import .*)', content, re.MULTILINE)
            if import_block:
                last_import = import_block[-1]
                pos = content.rfind(last_import) + len(last_import)
                content = content[:pos] + logger_line + content[pos:]
    
    return content, removed_count


def process_file(file_path: Path, dry_run: bool = False) -> Tuple[bool, int]:
    """
    处理单个文件
    
    Returns:
        (was_modified, removed_count)
    """
    try:
        content = file_path.read_text(encoding='utf-8')
        
        if not has_debug_prints(content):
            return False, 0
        
        cleaned_content, removed_count = clean_debug_prints(content, file_path)
        
        if removed_count > 0:
            if not dry_run:
                file_path.write_text(cleaned_content, encoding='utf-8')
            return True, removed_count
        
        return False, 0
    
    except Exception as e:
        print(f"❌ 处理文件失败 {file_path}: {e}")
        return False, 0


def main():
    """主函数"""
    if len(sys.argv) > 1:
        root_dir = Path(sys.argv[1])
    else:
        root_dir = Path(__file__).parent
    
    if not root_dir.exists():
        print(f"❌ 目录不存在: {root_dir}")
        sys.exit(1)
    
    dry_run = '--dry-run' in sys.argv
    
    print(f"🔍 扫描目录: {root_dir}")
    print(f"📝 模式: {'预览模式（不会修改文件）' if dry_run else '执行模式（会修改文件）'}")
    print("-" * 60)
    
    python_files = find_python_files(root_dir)
    print(f"📁 找到 {len(python_files)} 个Python文件")
    
    modified_files = []
    total_removed = 0
    
    for file_path in python_files:
        was_modified, removed_count = process_file(file_path, dry_run=dry_run)
        
        if was_modified:
            modified_files.append((file_path, removed_count))
            total_removed += removed_count
    
    print("-" * 60)
    print(f"📊 处理结果:")
    print(f"  • 处理文件数: {len(modified_files)}")
    print(f"  • 移除DEBUG语句数: {total_removed}")
    
    if modified_files:
        print(f"\n📝 修改的文件:")
        for file_path, count in modified_files:
            relative_path = file_path.relative_to(root_dir)
            print(f"  • {relative_path}: 移除 {count} 条DEBUG语句")
    
    if dry_run:
        print("\n💡 这是预览模式，文件未被修改。")
        print("   运行不带 --dry-run 参数来实际执行清理。")
    else:
        print("\n✅ 清理完成！")


if __name__ == "__main__":
    main()


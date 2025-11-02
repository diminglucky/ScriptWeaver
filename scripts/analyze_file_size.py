#!/usr/bin/env python3
"""分析Python文件大小，找出需要重构的大文件"""
from pathlib import Path

def analyze_files():
    """分析src目录下所有Python文件"""
    files = []
    for py_file in Path('src').rglob('*.py'):
        try:
            content = py_file.read_text(encoding='utf-8')
            lines = len(content.splitlines())
            files.append((py_file, lines, len(content)))
        except Exception as e:
            print(f"Error reading {py_file}: {e}")
    
    files.sort(key=lambda x: x[1], reverse=True)
    
    print("=" * 80)
    print("文件大小分析（按行数排序）")
    print("=" * 80)
    print(f"{'行数':<8} {'大小(KB)':<10} {'文件路径'}")
    print("-" * 80)
    
    for file_path, lines, size_bytes in files[:20]:
        size_kb = size_bytes / 1024
        rel_path = str(file_path).replace('\\', '/')
        print(f"{lines:<8} {size_kb:<10.1f} {rel_path}")
    
    print("\n" + "=" * 80)
    print("需要重构的文件（>500行）")
    print("=" * 80)
    large_files = [f for f in files if f[1] > 500]
    for file_path, lines, size_bytes in large_files:
        rel_path = str(file_path).replace('\\', '/')
        print(f"{lines:>6} 行 - {rel_path}")

if __name__ == '__main__':
    analyze_files()


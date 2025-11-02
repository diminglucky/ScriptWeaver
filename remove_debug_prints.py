#!/usr/bin/env python3
"""删除调试print语句"""
import re

file_path = "src/gui/mixins/director_modules/director_mixin.py"

with open(file_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

new_lines = []
removed_count = 0

for line in lines:
    # 删除 [DEBUG], [INFO], [OK] 开头的print语句
    if re.search(r'print\(f?["\'](\[DEBUG\]|\[INFO\]|\[OK\])', line):
        removed_count += 1
        continue
    
    # 删除单独的 print(f"[DEBUG] ...") 或 print("[DEBUG] ...") 
    if re.search(r'^\s+print\(f?["\'](\[DEBUG\]|\[INFO\]|\[OK\])', line):
        removed_count += 1
        continue
    
    new_lines.append(line)

with open(file_path, 'w', encoding='utf-8') as f:
    f.writelines(new_lines)

print(f"删除了 {removed_count} 行调试print")
print(f"文件从 {len(lines)} 行减少到 {len(new_lines)} 行")



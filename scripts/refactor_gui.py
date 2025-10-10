#!/usr/bin/env python3
"""
GUI代码重构脚本
自动将gui_app.py拆分成多个模块
"""

import re
from pathlib import Path
from typing import List, Dict

# 方法分类映射
METHOD_CATEGORIES = {
    'project': [
        '_refresh_project_list',
        '_on_new_project',
        '_on_load_project',
        '_on_save_story',
        '_on_delete_project',
        '_build_project_page',
    ],
    'story': [
        '_build_story_page',
        '_build_story_setup_tab',
        '_build_story_create_tab',
        'on_generate_outline',
        'on_generate',
        'on_generate_section',
        'on_continue_next_section',
        'on_auto_generate_all',
        '_generate_outline_model_only',
        '_generate_model_only',
        '_generate_in_sections',
        '_generate_single_section',
        '_do_generate_section',
        '_auto_generate_all_sections',
        '_build_outline_prompt',
        '_build_prompt',
        '_build_section_prompt',
        '_update_section_selector',
        'on_save_as',
        'on_clear_output',
        'on_copy_output',
    ],
    'image': [
        '_build_image_page',
        '_build_image_create_tab',
        '_build_image_setup_tab',
        '_img_choose_ref',
        '_on_img_generate',
        '_on_copy_img_prompt',
        '_on_clear_img_prompt',
        '_on_copy_shots',
        '_on_clear_shots',
        '_on_img_build_prompt',
        '_on_img_extract_shots',
        '_on_shot_selected',
        '_on_img_prompt_from_current_shot',
        '_on_img_prompt_from_shots',
        '_update_img_preview',
        '_on_img_save',
        '_auto_save_to_project',
        '_show_style_menu',
        '_add_style_tag',
        '_manual_input_style',
    ],
    'kb': [
        'on_ingest',
        'locate_existing_index',
        'choose_data',
        'choose_library_quick',
        'choose_index',
        'set_busy',
    ],
    'config': [
        'save_api_config',
        'load_api_config',
        '_auto_load_api_config',
        'save_img_api_config',
        'load_img_api_config',
        '_auto_load_image_api_config',
        'on_test_api',
        'on_test_image_api',
        '_on_api_preset_selected',
        '_on_img_api_preset_selected',
        '_save_image_api_config',
        '_load_custom_presets',
        '_save_custom_preset',
        '_delete_custom_preset',
        '_load_custom_image_presets',
        '_save_custom_image_preset',
        '_delete_custom_image_preset',
    ],
    'ui': [
        '_build_ui',
        '_clear_prompt_placeholder',
        '_restore_prompt_placeholder',
        '_get_prompt_content',
        'open_image_window',
    ],
}


def extract_method(content: str, method_name: str) -> str:
    """提取某个方法的完整代码"""
    pattern = rf'^\tdef {method_name}\(.*?\).*?:\n(.*?)(?=^\tdef\s|\Z)'
    match = re.search(pattern, content, re.MULTILINE | re.DOTALL)
    if match:
        return f"\tdef {method_name}{match.group(0).split(':', 1)[0].split(method_name)[1]}:\n{match.group(1)}"
    return ""


def generate_mixin_file(category: str, methods: List[str], original_content: str) -> str:
    """生成Mixin类文件内容"""
    class_name = f"{category.capitalize()}Mixin"
    
    # 提取方法
    method_codes = []
    for method in methods:
        code = extract_method(original_content, method)
        if code:
            method_codes.append(code)
    
    # 生成文件内容
    content = f'''"""
{category.capitalize()}相关功能模块
"""

from tkinter import BOTH, LEFT, RIGHT, DISABLED, NORMAL, END, messagebox, filedialog
import tkinter as tk
from tkinter import ttk


class {class_name}:
    """{category.capitalize()}管理功能"""
    
{''.join(method_codes)}
'''
    return content


def main():
    # 读取原文件
    gui_app_path = Path(__file__).parent.parent / "src" / "gui_app.py"
    if not gui_app_path.exists():
        print(f"错误: 找不到文件 {gui_app_path}")
        return
    
    with open(gui_app_path, 'r', encoding='utf-8') as f:
        original_content = f.read()
    
    # 创建mixins目录
    mixins_dir = Path(__file__).parent.parent / "src" / "gui" / "mixins"
    mixins_dir.mkdir(parents=True, exist_ok=True)
    
    # 生成各个Mixin文件
    for category, methods in METHOD_CATEGORIES.items():
        mixin_content = generate_mixin_file(category, methods, original_content)
        output_file = mixins_dir / f"{category}_mixin.py"
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(mixin_content)
        
        print(f"✓ 已生成: {output_file}")
    
    # 生成__init__.py
    init_content = """\"\"\"Mixin模块\"\"\"

from .project_mixin import ProjectMixin
from .story_mixin import StoryMixin
from .image_mixin import ImageMixin
from .kb_mixin import KbMixin
from .config_mixin import ConfigMixin
from .ui_mixin import UiMixin

__all__ = [
    'ProjectMixin',
    'StoryMixin',
    'ImageMixin',
    'KbMixin',
    'ConfigMixin',
    'UiMixin',
]
"""
    
    with open(mixins_dir / "__init__.py", 'w', encoding='utf-8') as f:
        f.write(init_content)
    
    print(f"✓ 已生成: {mixins_dir / '__init__.py'}")
    print("\n重构完成! 请查看 src/gui/mixins/ 目录")


if __name__ == "__main__":
    main()


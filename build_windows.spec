# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller配置文件 - AI故事创作工具
用于打包Windows可执行程序
"""

import sys
from pathlib import Path

# 项目根目录
project_root = Path(SPECPATH)

# 分析主程序
block_cipher = None

a = Analysis(
    ['run_modern_app.py'],  # 主入口文件
    pathex=[str(project_root)],
    binaries=[],
    datas=[
        # 包含配置文件
        ('custom_api_presets.json', '.'),
        ('custom_image_api_presets.json', '.'),
        # 包含源代码（作为数据文件，防止import问题）
        ('src', 'src'),
        # 包含文档
        ('docs', 'docs'),
        # 包含README
        ('README.md', '.'),
    ],
    hiddenimports=[
        # GUI相关
        'tkinter',
        'tkinter.ttk',
        'tkinter.filedialog',
        'tkinter.messagebox',
        'tkinter.scrolledtext',
        # 项目模块
        'src',
        'src.gui',
        'src.gui.modern_app',
        'src.gui.main_window',
        'src.gui.config_manager',
        'src.gui.custom_widgets',
        'src.gui.theme',
        'src.gui.utils',
        'src.gui.mixins',
        'src.gui.mixins.config_mixin',
        'src.gui.mixins.image_mixin',
        'src.gui.mixins.kb_mixin',
        'src.gui.mixins.project_mixin',
        'src.gui.mixins.story_mixin',
        'src.gui.mixins.ui_mixin',
        'src.gui_app',
        'src.clients',
        'src.clients.deepseek_client',
        'src.clients.image_client',
        'src.clients.hunyuan_image_client',
        'src.kb',
        'src.kb.ingest',
        'src.kb.search',
        'src.utils',
        'src.utils.text',
        'src.project_manager',
        # 第三方库
        'dotenv',
        'openai',
        'faiss',
        'numpy',
        'sentence_transformers',
        'transformers',
        'torch',
        'PIL',
        'PIL.Image',
        'PIL.ImageTk',
        'requests',
        'tqdm',
        'rich',
        'typer',
        # sentence-transformers依赖
        'sentence_transformers.models',
        'sentence_transformers.util',
        'transformers.models.bert',
        'transformers.models.roberta',
        'transformers.models.xlm_roberta',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # 排除不需要的模块以减小体积
        'matplotlib',
        'scipy',
        'pandas',
        'jupyter',
        'notebook',
        'IPython',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='AI故事创作工具',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,  # 不显示控制台窗口
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,  # 如果有图标文件，可以指定路径
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='AI故事创作工具',
)


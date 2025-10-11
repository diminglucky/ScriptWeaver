# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller简化配置文件 - AI故事创作工具
生成单个exe文件（体积较大但更方便）
"""

import sys
from pathlib import Path

# 项目根目录
project_root = Path(SPECPATH)

# 分析主程序
block_cipher = None

a = Analysis(
    ['run_modern_app.py'],
    pathex=[str(project_root)],
    binaries=[],
    datas=[
        ('custom_api_presets.json', '.'),
        ('custom_image_api_presets.json', '.'),
        ('src', 'src'),
        ('docs', 'docs'),
        ('README.md', '.'),
    ],
    hiddenimports=[
        'tkinter',
        'tkinter.ttk',
        'tkinter.filedialog',
        'tkinter.messagebox',
        'tkinter.scrolledtext',
        'src.gui.modern_app',
        'src.gui.main_window',
        'src.gui_app',
        'src.clients.deepseek_client',
        'src.clients.image_client',
        'src.clients.hunyuan_image_client',
        'src.kb.ingest',
        'src.kb.search',
        'src.utils.text',
        'src.project_manager',
        'dotenv',
        'openai',
        'faiss',
        'numpy',
        'sentence_transformers',
        'PIL',
        'PIL.Image',
        'PIL.ImageTk',
        'requests',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['matplotlib', 'scipy', 'pandas', 'jupyter'],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='AI故事创作工具',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)


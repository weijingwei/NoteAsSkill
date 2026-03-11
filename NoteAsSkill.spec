# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec file for NoteAsSkill

Usage:
    pyinstaller NoteAsSkill.spec
"""

import sys
from pathlib import Path

block_cipher = None

# 项目根目录
project_root = Path(SPECPATH)

# 收集数据文件
datas = [
    (str(project_root / 'assets'), 'assets'),
    (str(project_root / 'notebook' / 'templates'), 'notebook/templates'),
]

# 收集 PySide6 的插件
from PySide6 import QtCore, QtGui, QtWidgets
pyside6_path = Path(QtCore.__file__).parent
datas.append((str(pyside6_path / 'plugins'), 'PySide6/plugins'))

a = Analysis(
    ['main.py'],
    pathex=[str(project_root)],
    binaries=[],
    datas=datas,
    hiddenimports=[
        'PySide6',
        'PySide6.QtCore',
        'PySide6.QtGui',
        'PySide6.QtWidgets',
        'PySide6.QtWebEngineWidgets',
        'PySide6.QtWebEngineCore',
        'markdown',
        'yaml',
        'openai',
        'anthropic',
        'requests',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tkinter',
        'matplotlib',
        'numpy',
        'pandas',
        'scipy',
        'PIL',
        'cv2',
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
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='NoteAsSkill',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # 不显示控制台窗口
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(project_root / 'assets' / 'icons' / 'icon.ico') if (project_root / 'assets' / 'icons' / 'icon.ico').exists() else None,
)

# macOS 应用包配置
if sys.platform == 'darwin':
    app = BUNDLE(
        exe,
        name='NoteAsSkill.app',
        icon=str(project_root / 'assets' / 'icons' / 'icon.icns') if (project_root / 'assets' / 'icons' / 'icon.icns').exists() else None,
        bundle_identifier='com.noteasskill.app',
        info_plist={
            'CFBundleName': 'NoteAsSkill',
            'CFBundleDisplayName': 'NoteAsSkill - 笔技',
            'CFBundleVersion': '0.2.15',
            'CFBundleShortVersionString': '0.2.15',
            'NSHighResolutionCapable': True,
        },
    )
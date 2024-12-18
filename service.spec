# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_data_files
from PyInstaller.utils.hooks import copy_metadata

datas = []
datas += collect_data_files('torch')
datas += collect_data_files('torchvision')
datas += collect_data_files('langchain')
datas += collect_data_files('torchaudio')
datas += copy_metadata('torch')
datas += copy_metadata('langchain')
datas += copy_metadata('torchvision')
datas += copy_metadata('torchaudio')
datas += copy_metadata('packaging')
datas += copy_metadata('safetensors')
datas += copy_metadata('regex')
datas += copy_metadata('huggingface-hub')
datas += copy_metadata('tokenizers')
datas += copy_metadata('filelock')
datas += copy_metadata('datasets')
datas += copy_metadata('numpy')
datas += copy_metadata('tqdm')
datas += copy_metadata('requests')
datas += copy_metadata('pyyaml')


a = Analysis(
    ['src\\windows\\service.py'],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=['win32timezone', 'torch', 'torchvision', 'torchaudio'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='service',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='service',
)

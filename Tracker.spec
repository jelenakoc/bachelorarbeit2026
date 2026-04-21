# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_data_files
from PyInstaller.utils.hooks import collect_submodules

datas = [('C:\\Users\\milli\\AppData\\Local\\Programs\\Python\\Python313\\tcl\\tcl8.6', '_tcl_data'), ('C:\\Users\\milli\\AppData\\Local\\Programs\\Python\\Python313\\tcl\\tk8.6', '_tk_data')]
hiddenimports = ['win32timezone', '_tkinter']
datas += collect_data_files('tkinter')
hiddenimports += collect_submodules('tkinter')


a = Analysis(
    ['app\\tracker.py'],
    pathex=['.'],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=['pyinstaller_hooks'],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='Tracker',
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
    name='Tracker',
)

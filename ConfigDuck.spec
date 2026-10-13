# -*- mode: python ; coding: utf-8 -*-

a = Analysis(
    ['ConfigDuck.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('duck.ico', '.'),
        ('civ_data.json', '.'),
        ('units_db.json', '.'),
        ('typical_strategies.json', '.'),
        ('AgeIcons', 'AgeIcons'),
    ],
    hiddenimports=[],
    hookspath=[],
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
    name='ConfigDuck',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    icon=['duck.ico'],
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='ConfigDuck',
)

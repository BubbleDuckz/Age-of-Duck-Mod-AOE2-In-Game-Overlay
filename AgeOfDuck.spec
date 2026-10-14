# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['AgeofDuck.py'],
    pathex=[],
    binaries=[],
    datas=[('tc_reminder/samples/resolution-clock-0340.png', 'tc_reminder/samples'), ('villager-glyphs.json', '.'), ('build_order_voice.ps1', '.'), ('BuildOrders', 'BuildOrders'), ('techtree_data.json', '.'), ('unit_counters_v2.json', '.'), ('UnitIcons', 'UnitIcons'), ('techtree_source/LICENSE', 'techtree_source'), ('tc_reminder/calibration.json', 'tc_reminder'), ('tc_reminder/clock-calibration.json', 'tc_reminder'), ('tc_reminder/population-glyphs.json', 'tc_reminder'), ('tc_reminder/validation-approval.json', 'tc_reminder'), ('tc_reminder/*.wav', 'tc_reminder'), ('tc_reminder/templates', 'tc_reminder/templates'), ('tc_reminder/samples/clock-0228.png', 'tc_reminder/samples'), ('tc_reminder/samples/foundation-five.png', 'tc_reminder/samples'), ('tc_reminder/samples/independent-four.png', 'tc_reminder/samples'), ('tc_reminder/samples/independent-one.png', 'tc_reminder/samples'), ('tc_reminder/samples/independent-single.png', 'tc_reminder/samples'), ('tc_reminder/samples/selected-three.png', 'tc_reminder/samples'), ('duck.png', '.'), ('profile.png', '.'), ('civ_data.json', '.'), ('units_db.json', '.'), ('typical_strategies.json', '.'), ('Units', 'Units'), ('CivIcons', 'CivIcons'), ('AgeIcons', 'AgeIcons')],
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
    name='AgeOfDuck',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['duck.ico'],
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='AgeOfDuck',
)

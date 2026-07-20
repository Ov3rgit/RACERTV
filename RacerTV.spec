# -*- mode: python ; coding: utf-8 -*-
import glob
import os

# ---- ASSETS -------------------------------------------------------------
# These used to be copied into dist/RacerTV by hand (see README), which meant
# every new asset was a chance to forget one — the radio-card art (icon_*.png)
# was exactly that risk. PyInstaller now collects them, and the icon glob
# picks up any helmet the user adds later without touching this file.
#
# Everything lands NEXT TO the exe ('.') because the app resolves its own
# _DIR to os.path.dirname(sys.executable) when frozen — matching how the
# unfrozen app reads them from the source folder.
datas = []
for _f in ('r3e-data.json', 'racer-tv.png', 'tts_worker.ps1',
           'setup_voices.ps1', 'README.txt'):
    if os.path.exists(_f):
        datas.append((_f, '.'))
for _pat in ('*.ttf', 'icon_*.png'):          # fonts + user radio-card art
    for _p in sorted(glob.glob(_pat)):
        datas.append((_p, '.'))
for _d in ('lines_data', 'stings'):           # dialogue pools + pre-rendered stings
    if os.path.isdir(_d):
        datas.append((os.path.join(_d, '*'), _d))

a = Analysis(
    ['r3e_overlay.py'],
    pathex=[],
    binaries=[],
    datas=datas,
    # PIL._tkinter_finder: ImageTk's tk binding is imported dynamically, so
    # PyInstaller can't see it — without this the user's PNG icons silently
    # fall back to the vector drawings in a frozen build.
    hiddenimports=['_cffi_backend', 'PIL._tkinter_finder'],
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
    name='RacerTV',
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
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='RacerTV',
)

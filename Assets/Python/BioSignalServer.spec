# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all, collect_submodules

datas = []
binaries = []
hiddenimports = []

# ── Third-party packages that need full collection ─────────────────────────
for pkg in ('uvicorn', 'fastapi', 'starlette', 'neurokit2', 'pylsl'):
    tmp = collect_all(pkg)
    datas     += tmp[0]
    binaries  += tmp[1]
    hiddenimports += tmp[2]

# ── Local packages with runtime / lazy imports ─────────────────────────────
# gui.panels modules are imported inside create_panel() at runtime, so
# PyInstaller's static analyser misses them. collect_submodules picks up
# every panel automatically — including ones added in the future.
hiddenimports += collect_submodules('gui.panels')
hiddenimports += collect_submodules('processors')
hiddenimports += collect_submodules('signals')

a = Analysis(
    ['main.py'],
    # Tell PyInstaller where the top-level packages live.
    # '.' assumes pyinstaller runs from the project root (next to main.py).
    pathex=['.'],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
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
    a.binaries,
    a.datas,
    [],
    name='BioSignalServer',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,          # flip to False once the log window is no longer needed
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

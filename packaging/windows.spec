from pathlib import Path
ROOT = Path(SPECPATH).resolve().parent
# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    [str(ROOT / 'src' / 'launcher.py')],
    pathex=[str(ROOT / 'src')],
    binaries=[],
    datas=[(str(ROOT / 'assets'), 'assets'), (str(ROOT / 'LICENSE'), '.'), (str(ROOT / 'THIRD_PARTY_NOTICES.md'), '.')],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
# Qt6Core on Windows imports the unversioned ICU API from System32.
# A similarly named ICU DLL on the build machine's PATH is incompatible.
a.binaries = [entry for entry in a.binaries
              if entry[0].lower() not in ('icuuc.dll', 'icudt78.dll')]
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='SR Inqly',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    icon=str(ROOT / 'assets/sr-inqly.ico'),
    version=str(ROOT / 'packaging/windows_version.txt'),
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
    name='SR Inqly',
)

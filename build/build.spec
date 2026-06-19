# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for mc-config-editor.
Single-file executable for Windows, macOS, and Linux.

Build:
    pyinstaller build/build.spec

Output:
    dist/mc-config-editor       (Linux/macOS)
    dist/mc-config-editor.exe   (Windows)
"""

import os
import sys

block_cipher = None

# Resolve project root (parent of this build/ directory)
_BUILD_DIR = os.path.abspath(SPECPATH)
_PROJECT_ROOT = os.path.dirname(_BUILD_DIR)

# ── Determine icon per platform ────────────────────────────────────────
_icon_path = None
if sys.platform == "win32":
    _icon_path = os.path.join(_BUILD_DIR, "mc-config-editor.ico")
elif sys.platform == "darwin":
    _icon_path = os.path.join(_BUILD_DIR, "icon.icns")

a = Analysis(
    [os.path.join(_PROJECT_ROOT, "mc-config-editor-qt.py")],
    pathex=[_PROJECT_ROOT],
    binaries=[],
    datas=[
        (os.path.join(_PROJECT_ROOT, "icons"), "icons"),
        (os.path.join(_PROJECT_ROOT, "style"), "style"),
        (os.path.join(_PROJECT_ROOT, "i18n"), "i18n"),
    ],
    hiddenimports=[
        "tomlkit",
        "pyjson5",
        "yaml",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "tkinter",
    ],
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
    name="mc-config-editor",
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
)

# Platform-specific icon
if _icon_path and os.path.isfile(_icon_path):
    exe.icon = _icon_path

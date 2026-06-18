#!/usr/bin/env python3
"""
mc-config-editor.py — Minecraft Mod Config Editor (entry point)

Wrapper multiplataforma que importa e executa o modulo principal.
Garante comportamento identico em Windows, macOS e Linux.

Uso:
    python mc-config-editor.py
    python mc-config-editor.py --instance /caminho/para/instancia
"""

import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent

# ── Dependencias ────────────────────────────────────────────────────────

_MISSING = []
try:
    import PyQt6
except ImportError:
    try:
        import PyQt5
    except ImportError:
        _MISSING.append("PyQt6 (ou PyQt5)")

for _mod, _pkg in [("yaml", "pyyaml"), ("tomlkit", "tomlkit"), ("pyjson5", "pyjson5")]:
    try:
        __import__(_mod)
    except ImportError:
        _MISSING.append(_pkg)

if _MISSING:
    _venv_hint = ""
    _venv_path = SCRIPT_DIR / "venv" / ("Scripts" if sys.platform == "win32" else "bin") / "python3"
    if not _venv_path.is_file():
        _venv_path = SCRIPT_DIR / "venv" / ("Scripts" if sys.platform == "win32" else "bin") / "python"
    if _venv_path.is_file():
        _venv_hint = f"\n   Ou use o venv: {_venv_path} {' '.join(sys.argv)}"
    print(
        f"\n❌ Dependencias faltando: {', '.join(_MISSING)}\n"
        f"   Instale com: pip install PyQt6 tomlkit pyjson5 pyyaml{_venv_hint}\n",
        file=sys.stderr,
    )
    sys.exit(1)

# ── Executa o modulo principal ──────────────────────────────────────────

sys.path.insert(0, str(SCRIPT_DIR))

# The main module is mc-config-editor-qt.py (PyQt6)
# Import it and call its main() — guaranteed identical behavior on all platforms
import importlib.util as _util

_main_spec = _util.spec_from_file_location(
    "mc_config_editor_qt",
    str(SCRIPT_DIR / "mc-config-editor-qt.py"),
)
_main_module = _util.module_from_spec(_main_spec)
_main_spec.loader.exec_module(_main_module)
_main_module.main()

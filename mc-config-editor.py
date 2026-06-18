#!/usr/bin/env python3
"""
mc-config-editor.py — Minecraft Mod Config Editor (entry point)

Wrapper multiplataforma com validacao de dependencias.
Se faltar PyQt6, yaml, tomlkit ou pyjson5, pergunta ao usuario
se deseja instalar automaticamente.

Uso:
    python mc-config-editor.py
    python mc-config-editor.py --instance /caminho/para/instancia
"""

import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent

# ── OS / env detection ──────────────────────────────────────────────────

_IS_WINDOWS = sys.platform == "win32"
_IS_MACOS = sys.platform == "darwin"
_IS_LINUX = sys.platform.startswith("linux")
_IN_VENV = sys.prefix != sys.base_prefix


def _pip_install_cmd(packages):
    """Retorna o comando pip apropriado para o SO e ambiente."""
    cmd = [sys.executable, "-m", "pip", "install"]
    if not _IN_VENV and not _IS_WINDOWS:
        cmd.append("--user")
    return cmd + packages


def _try_install(packages):
    """
    Tenta instalar os pacotes. Retorna (ok, mensagem).
    Se falhar por PEP 668, tenta --break-system-packages no Linux.
    """
    cmd = _pip_install_cmd(packages)
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if result.returncode == 0:
            return True, "Instalado com sucesso"
        stderr = result.stderr.strip()
        if _IS_LINUX and not _IN_VENV and "externally-managed" in stderr:
            cmd2 = [sys.executable, "-m", "pip", "install", "--break-system-packages"] + packages
            r2 = subprocess.run(cmd2, capture_output=True, text=True, timeout=120)
            if r2.returncode == 0:
                return True, "Instalado (--break-system-packages)"
            return False, r2.stderr.strip()[-200:]
        return False, stderr[-200:] if stderr else "Erro desconhecido do pip"
    except FileNotFoundError:
        return False, "pip nao encontrado. Certifique-se de que o Python esta instalado com pip."
    except subprocess.TimeoutExpired:
        return False, "Timeout ao instalar (verifique sua conexao de internet)"


# ── Check dependencies ──────────────────────────────────────────────────

_REQUIRED = [
    ("PyQt6", "PyQt6"),
    ("yaml", "pyyaml"),
    ("tomlkit", "tomlkit"),
    ("pyjson5", "pyjson5"),
]

_MISSING_PKGS = []
_MISSING_NAMES = []

for _mod, _pkg in _REQUIRED:
    try:
        __import__(_mod)
    except ImportError:
        _MISSING_PKGS.append(_pkg)
        _MISSING_NAMES.append(_mod)

if _MISSING_PKGS:
    import tkinter as tk
    from tkinter import messagebox

    root = tk.Tk()
    root.withdraw()

    names = ", ".join(_MISSING_NAMES)
    answer = messagebox.askyesno(
        "Dependencias Faltando",
        f"As seguintes dependencias nao foram encontradas:\n\n"
        f"  \u2726 {names}\n\n"
        f"Deseja instalar automaticamente com pip?",
    )

    if answer:
        ok, detail = _try_install(_MISSING_PKGS)
        if not ok:
            messagebox.showerror(
                "Erro na Instalacao",
                f"Falha ao instalar:\n\n{detail}\n\n"
                f"Instale manualmente:\n"
                f"  pip install {' '.join(_MISSING_PKGS)}",
            )
            root.destroy()
            sys.exit(1)

        still_missing = []
        for _mod, _pkg in _REQUIRED:
            try:
                __import__(_mod)
            except ImportError:
                still_missing.append(_mod)

        if still_missing:
            messagebox.showerror(
                "Erro na Instalacao",
                f"Ainda nao encontrado apos instalar:\n"
                f"  {', '.join(still_missing)}\n\n"
                f"Instale manualmente e tente novamente.",
            )
            root.destroy()
            sys.exit(1)

        messagebox.showinfo(
            "Instalacao Concluida",
            "Todas as dependencias foram instaladas.\nO app sera iniciado agora.",
        )
        root.destroy()
    else:
        root.destroy()
        sys.exit(0)


# ── Run main module ─────────────────────────────────────────────────────

sys.path.insert(0, str(SCRIPT_DIR))

_MAIN_FILE = SCRIPT_DIR / "mc-config-editor-qt.py"
_code = compile(_MAIN_FILE.read_text(), str(_MAIN_FILE), "exec")
_globals = {"__file__": str(_MAIN_FILE), "__name__": "__main__"}
exec(_code, _globals)

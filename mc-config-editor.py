#!/usr/bin/env python3
"""
mc-config-editor.py — Minecraft Mod Config Editor — by Makalove

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


# ── i18n ─────────────────────────────────────────────────────────────────

def _detect_lang() -> str:
    import locale
    try:
        loc = locale.getlocale()[0] or ""
    except Exception:
        loc = ""
    if loc.startswith("en"):
        return "en"
    if loc.startswith("es"):
        return "es"
    return "pt_BR"

_LANG = _detect_lang()

_TRANSLATIONS: dict = {
    "en": {
        "Instalado com sucesso": "Installed successfully",
        "Instalado (--break-system-packages)": "Installed (--break-system-packages)",
        "Erro desconhecido do pip": "Unknown pip error",
        "pip nao encontrado. Certifique-se de que o Python esta instalado com pip.":
            "pip not found. Make sure Python is installed with pip.",
        "Timeout ao instalar (verifique sua conexao de internet)":
            "Installation timeout (check your internet connection).",
        "Dependencias Faltando": "Missing Dependencies",
        "As seguintes dependencias nao foram encontradas:\n\n"
        "  \u2726 {names}\n\n"
        "Deseja instalar automaticamente com pip?":
            "The following dependencies were not found:\n\n"
            "  \u2726 {names}\n\n"
            "Would you like to install them automatically with pip?",
        "Erro na Instalacao": "Installation Error",
        "Falha ao instalar:\n\n{detail}\n\n"
        "Instale manualmente:\n"
        "  pip install {pkgs}":
            "Installation failed:\n\n{detail}\n\n"
            "Please install manually:\n"
            "  pip install {pkgs}",
        "Ainda nao encontrado apos instalar:\n"
        "  {mods}\n\n"
        "Instale manualmente e tente novamente.":
            "Still not found after installation:\n"
            "  {mods}\n\n"
            "Please install manually and try again.",
        "Instalacao Concluida": "Installation Complete",
        "Todas as dependencias foram instaladas.\nO app sera iniciado agora.":
            "All dependencies have been installed.\nThe app will start now.",
    },
    "es": {
        "Instalado com sucesso": "Instalado exitosamente",
        "Instalado (--break-system-packages)": "Instalado (--break-system-packages)",
        "Erro desconhecido do pip": "Error desconocido de pip",
        "pip nao encontrado. Certifique-se de que o Python esta instalado com pip.":
            "pip no encontrado. Asegúrese de que Python esté instalado con pip.",
        "Timeout ao instalar (verifique sua conexao de internet)":
            "Timeout de instalación (verifique su conexión a internet).",
        "Dependencias Faltando": "Dependencias Faltantes",
        "As seguintes dependencias nao foram encontradas:\n\n"
        "  \u2726 {names}\n\n"
        "Deseja instalar automaticamente com pip?":
            "Las siguientes dependencias no fueron encontradas:\n\n"
            "  \u2726 {names}\n\n"
            "¿Desea instalarlas automáticamente con pip?",
        "Erro na Instalacao": "Error de Instalación",
        "Falha ao instalar:\n\n{detail}\n\n"
        "Instale manualmente:\n"
        "  pip install {pkgs}":
            "Error al instalar:\n\n{detail}\n\n"
            "Instale manualmente:\n"
            "  pip install {pkgs}",
        "Ainda nao encontrado apos instalar:\n"
        "  {mods}\n\n"
        "Instale manualmente e tente novamente.":
            "Aún no encontrado después de instalar:\n"
            "  {mods}\n\n"
            "Instale manualmente e intente nuevamente.",
        "Instalacao Concluida": "Instalación Completa",
        "Todas as dependencias foram instaladas.\nO app sera iniciado agora.":
            "Todas las dependencias han sido instaladas.\nLa aplicación se iniciará ahora.",
    },
}

def _(text: str, **kwargs) -> str:
    if _LANG in _TRANSLATIONS and text in _TRANSLATIONS[_LANG]:
        result = _TRANSLATIONS[_LANG][text]
    else:
        result = text
    if kwargs:
        result = result.format(**kwargs)
    return result


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
            return True, _("Instalado com sucesso")
        stderr = result.stderr.strip()
        if _IS_LINUX and not _IN_VENV and "externally-managed" in stderr:
            cmd2 = [sys.executable, "-m", "pip", "install", "--break-system-packages"] + packages
            r2 = subprocess.run(cmd2, capture_output=True, text=True, timeout=120)
            if r2.returncode == 0:
                return True, _("Instalado (--break-system-packages)")
            return False, r2.stderr.strip()[-200:]
        return False, stderr[-200:] if stderr else _("Erro desconhecido do pip")
    except FileNotFoundError:
        return False, _("pip nao encontrado. Certifique-se de que o Python esta instalado com pip.")
    except subprocess.TimeoutExpired:
        return False, _("Timeout ao instalar (verifique sua conexao de internet)")


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
        _("Dependencias Faltando"),
        _("As seguintes dependencias nao foram encontradas:\n\n"
          "  \u2726 {names}\n\n"
          "Deseja instalar automaticamente com pip?", names=names),
    )

    if answer:
        ok, detail = _try_install(_MISSING_PKGS)
        if not ok:
            messagebox.showerror(
                _("Erro na Instalacao"),
                _("Falha ao instalar:\n\n{detail}\n\n"
                  "Instale manualmente:\n"
                  "  pip install {pkgs}", detail=detail, pkgs=' '.join(_MISSING_PKGS)),
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
                _("Erro na Instalacao"),
                _("Ainda nao encontrado apos instalar:\n"
                  "  {mods}\n\n"
                  "Instale manualmente e tente novamente.", mods=', '.join(still_missing)),
            )
            root.destroy()
            sys.exit(1)

        messagebox.showinfo(
            _("Instalacao Concluida"),
            _("Todas as dependencias foram instaladas.\nO app sera iniciado agora."),
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

#!/usr/bin/env python3
"""
mc-config-editor.py — Minecraft Mod Config Editor

GUI em customtkinter para navegar, editar e salvar arquivos de configuração
de mods em instâncias do PrismLauncher / ElyPrismLauncher.

Multiplataforma: Windows, Linux, macOS.

Uso:
    python mc-config-editor.py
    python mc-config-editor.py --instance /caminho/para/instancia
"""

import datetime
import json
import logging
import os
import platform
import re
import shutil
import sys
import tkinter as tk
import traceback
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# ── OS detection ────────────────────────────────────────────────────────

IS_WINDOWS = sys.platform == "win32"
IS_MACOS = sys.platform == "darwin"
IS_LINUX = sys.platform.startswith("linux")

log = logging.getLogger("mc-config-editor")  # placeholder; real config abaixo

def _detect_default_launcher_paths() -> List[Path]:
    """Retorna os paths padrao onde instancias do PrismLauncher podem estar."""
    home = Path.home()
    paths: List[Path] = []
    if IS_WINDOWS:
        appdata = os.environ.get("APPDATA", "")
        if appdata:
            paths.append(Path(appdata) / "PrismLauncher" / "instances")
        localappdata = os.environ.get("LOCALAPPDATA", "")
        if localappdata:
            paths.append(Path(localappdata) / "PrismLauncher" / "instances")
    elif IS_MACOS:
        paths.append(home / "Library" / "Application Support" / "PrismLauncher" / "instances")
    else:
        paths.append(home / ".local" / "share" / "PrismLauncher" / "instances")
        paths.append(home / ".var" / "app" / "io.github.elyprismlauncher.ElyPrismLauncher"
                     / "data" / "ElyPrismLauncher" / "instances")
        paths.append(home / ".var" / "app" / "org.prismlauncher.PrismLauncher"
                     / "data" / "PrismLauncher" / "instances")
    return [p for p in paths if p.is_dir()]

DEFAULT_LAUNCHER_PATHS = _detect_default_launcher_paths()

def _detect_venv_python() -> Optional[str]:
    """Encontra o python do venv local ou global associado ao script."""
    candidates = [
        SCRIPT_DIR / "venv" / ("Scripts" if IS_WINDOWS else "bin") / "python3",
        SCRIPT_DIR / "venv" / ("Scripts" if IS_WINDOWS else "bin") / "python",
        SCRIPT_DIR / ".venv" / ("Scripts" if IS_WINDOWS else "bin") / "python3",
        Path.home() / ".cache" / "mc-config-editor-venv" / ("Scripts" if IS_WINDOWS else "bin") / "python3",
        Path.home() / ".cache" / "mc-config-editor-venv" / ("Scripts" if IS_WINDOWS else "bin") / "python",
    ]
    if IS_WINDOWS:
        # Python on Windows uses python.exe
        ext = ".exe"
        candidates = [Path(str(c).replace("python3", "python" + ext)) for c in candidates]
    for p in candidates:
        if p.is_file():
            return str(p.resolve())
    return None

# ── Logging ─────────────────────────────────────────────────────────────

SCRIPT_DIR = Path(__file__).resolve().parent
LOG_DIR = SCRIPT_DIR / "logs"
LOG_DIR.mkdir(exist_ok=True)
LOG_FILE = LOG_DIR / f"{datetime.datetime.now().strftime('%Y-%m-%d_%H%M%S')}.log"

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.FileHandler(str(LOG_FILE), encoding="utf-8"),
        logging.StreamHandler(sys.stderr),
    ],
)
log = logging.getLogger("mc-config-editor")
log.info("=== mc-config-editor iniciando ===")
log.info("Python: %s", sys.version)
log.info("Executable: %s", sys.executable)
log.info("Log file: %s", LOG_FILE)
log.info("Script dir: %s", SCRIPT_DIR)
log.info("OS: %s | platform: %s", platform.system(), sys.platform)
log.info("Launcher paths detectados: %s", [str(p) for p in DEFAULT_LAUNCHER_PATHS])

try:
    import customtkinter as ctk
    log.info("customtkinter %s importado", ctk.__version__)
except ImportError:
    _venv = _detect_venv_python()
    log.error("customtkinter nao encontrado")
    if _venv:
        log.error("Execute com: %s %s", _venv, " ".join(sys.argv))
        print(
            f"\n❌ customtkinter nao instalado no Python do sistema.\n"
            f"   Use o launcher: ./mc-config-editor{' (Linux/macOS)' if not IS_WINDOWS else ' (ou mc-config-editor.bat no Windows)'}\n"
            f"   Ou execute com: {_venv} {' '.join(sys.argv)}\n",
            file=sys.stderr,
        )
    else:
        print(
            f"\n❌ customtkinter nao instalado.\n"
            f"   Instale com: pip install customtkinter tomlkit pyjson5 pyyaml\n",
            file=sys.stderr,
        )
    sys.exit(1)

import yaml
log.info("yaml importado")

# ── TOML / JSON5 — import opcionais com fallback ──────────────────────────

try:
    import tomlkit
    from tomlkit.exceptions import TOMLKitError

    HAS_TOMLKIT = True
except ImportError:
    HAS_TOMLKIT = False

try:
    import pyjson5
    HAS_JSON5 = True
except ImportError:
    HAS_JSON5 = False

# ── Constantes ────────────────────────────────────────────────────────────

KNOWN_SIDE_SUFFIXES: List[str] = [
    "-client", "-common", "-server", "-forge", "-fabric", "-neoforge",
    "-pack_config",
]

FORMAT_LABELS: Dict[str, str] = {
    "toml": "TOML (editor visual)",
    "json": "JSON (editor visual)",
    "json5": "JSON5 (editor visual)",
    "yaml": "YAML (editor visual)",
    "cfg": "Raw (Forge CFG)",
    "properties": "Raw (Properties)",
    "txt": "Raw (texto)",
    "snbt": "Raw (SNBT)",
    "ini": "Raw (INI)",
    "other": "Raw (desconhecido)",
}

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("green")

# ── Helpers ───────────────────────────────────────────────────────────────


def extract_mod_key(filename: str) -> str:
    """Extrai a chave do mod a partir do nome do arquivo."""
    stem = Path(filename).stem  # sem extensão
    # Remove .bak suffix if present
    if stem.endswith((".bak", ".backup")):
        stem = Path(stem).stem
    lower = stem.lower()
    for suffix in KNOWN_SIDE_SUFFIXES:
        if lower.endswith(suffix):
            stem = stem[: -len(suffix)]
            break
    # Split on first number if preceded by letter (edge case)
    return stem


def mod_key_to_display(key: str) -> str:
    """Converte chave do mod em nome legível."""
    # Substitui underscores e hífens por espaços
    name = re.sub(r'[_-]', ' ', key)
    # Capitaliza palavras
    return name.strip().title() or key


def format_timestamp() -> str:
    return datetime.datetime.now().strftime("%Y%m%d_%H%M%S")


# ── Estruturas de dados ───────────────────────────────────────────────────


class ConfigFile:
    """Representa um único arquivo de configuração."""

    def __init__(self, path: Path, fmt: str) -> None:
        self.path = path
        self.fmt = fmt  # toml, json, json5, yaml, cfg, properties, txt, snbt, ini, other
        self.parsed_data: Any = None
        self.parsed_ok = False
        self.parse_error: Optional[str] = None
        self.modified = False
        self._original_raw: Optional[str] = None
        self._modified_data: Any = None

    @property
    def display_name(self) -> str:
        return self.path.name

    @property
    def format_label(self) -> str:
        return FORMAT_LABELS.get(self.fmt, "Raw (desconhecido)")

    @property
    def is_structured(self) -> bool:
        return self.fmt in ("toml", "json", "json5", "yaml")

    def parse(self) -> None:
        """Parseia o arquivo conforme o formato."""
        if self.parsed_ok:
            return
        try:
            raw = self.path.read_text(encoding="utf-8", errors="replace")
            self._original_raw = raw
        except Exception as e:
            self.parsed_ok = False
            self.parse_error = f"Erro ao ler: {e}"
            return

        parsers = {
            "toml": self._parse_toml,
            "json": self._parse_json,
            "json5": self._parse_json5,
            "yaml": self._parse_yaml,
        }
        parser = parsers.get(self.fmt)
        if parser:
            parser(raw)
        else:
            # Raw — mantém como string
            self.parsed_data = raw
            self._modified_data = raw
            self.parsed_ok = True

    def _parse_toml(self, raw: str) -> None:
        if not HAS_TOMLKIT:
            self.parsed_ok = False
            self.parse_error = "tomlkit não instalado (pip install tomlkit)"
            return
        try:
            self.parsed_data = tomlkit.parse(raw)
            self._modified_data = self.parsed_data  # referência mutável
            self.parsed_ok = True
        except TOMLKitError as e:
            self.parsed_ok = False
            self.parse_error = f"Erro ao parsear TOML: {e}"

    def _parse_json(self, raw: str) -> None:
        try:
            self.parsed_data = json.loads(raw)
            self._modified_data = self.parsed_data
            self.parsed_ok = True
        except json.JSONDecodeError as e:
            self.parsed_ok = False
            self.parse_error = f"Erro ao parsear JSON: {e}"

    def _parse_json5(self, raw: str) -> None:
        if not HAS_JSON5:
            self.parsed_ok = False
            self.parse_error = "pyjson5 não instalado (pip install pyjson5)"
            return
        try:
            self.parsed_data = pyjson5.loads(raw)
            self._modified_data = self.parsed_data
            self.parsed_ok = True
        except Exception as e:
            self.parsed_ok = False
            self.parse_error = f"Erro ao parsear JSON5: {e}"

    def _parse_yaml(self, raw: str) -> None:
        try:
            self.parsed_data = yaml.safe_load(raw)
            self._modified_data = self.parsed_data
            self.parsed_ok = True
        except yaml.YAMLError as e:
            self.parsed_ok = False
            self.parse_error = f"Erro ao parsear YAML: {e}"

    def get_value(self, key_path: List[str]) -> Any:
        """Obtém valor por caminho de chaves (ex: ['section', 'key'])."""
        if not self.parsed_ok:
            return None
        if self.is_structured:
            data = self._modified_data
            for k in key_path:
                if isinstance(data, dict):
                    data = data.get(k)
                else:
                    return None
            return data
        return None

    def set_value(self, key_path: List[str], value: Any) -> None:
        """Define valor por caminho de chaves."""
        if not self.parsed_ok or not self.is_structured:
            return
        data = self._modified_data
        for i, k in enumerate(key_path[:-1]):
            if isinstance(data, dict) and k in data:
                data = data[k]
            else:
                return  # caminho não encontrado
        if isinstance(data, dict):
            data[key_path[-1]] = value
            self.modified = True

    def serialize(self) -> Optional[str]:
        """Serializa os dados de volta para string."""
        if not self.parsed_ok:
            return None
        if not self.is_structured:
            return str(self._modified_data) if self._modified_data is not None else None
        serializers = {
            "toml": self._serialize_toml,
            "json": self._serialize_json,
            "json5": self._serialize_json5,
            "yaml": self._serialize_yaml,
        }
        serializer = serializers.get(self.fmt)
        if serializer:
            return serializer()
        return None

    def _serialize_toml(self) -> Optional[str]:
        if HAS_TOMLKIT:
            try:
                return tomlkit.dumps(self._modified_data)
            except Exception:
                pass
        # fallback
        return tomlkit.dumps(self._modified_data) if HAS_TOMLKIT else None

    def _serialize_json(self) -> str:
        return json.dumps(self._modified_data, indent=2, ensure_ascii=False) + "\n"

    def _serialize_json5(self) -> str:
        if HAS_JSON5 and hasattr(pyjson5, "dumps"):
            try:
                return pyjson5.dumps(self._modified_data, indent=2, ensure_ascii=False) + "\n"
            except Exception:
                pass
        return json.dumps(self._modified_data, indent=2, ensure_ascii=False) + "\n"

    def _serialize_yaml(self) -> str:
        return yaml.dump(self._modified_data, default_flow_style=False, allow_unicode=True)

    def backup(self) -> Optional[Path]:
        """Cria backup timestampado. Retorna o path do backup ou None."""
        bak_path = self.path.with_name(f"{self.path.name}.bak.{format_timestamp()}")
        try:
            shutil.copy2(str(self.path), str(bak_path))
            return bak_path
        except OSError:
            return None

    def save(self) -> Tuple[bool, str]:
        """Salva o arquivo (criando backup primeiro). Retorna (ok, msg)."""
        if not self.parsed_ok:
            return False, "Arquivo não foi parseado corretamente."
        if not self.modified:
            return False, "Nenhuma modificação para salvar."
        # Backup
        bak = self.backup()
        # Serializa
        content = self.serialize()
        if content is None:
            return False, "Erro ao serializar o arquivo."
        try:
            self.path.write_text(content, encoding="utf-8")
        except OSError as e:
            return False, f"Erro ao escrever: {e}"
        msg = "Salvo com sucesso."
        if bak:
            msg += f" Backup: {bak.name}"
        self.modified = False
        return True, msg

    def raw_content(self) -> str:
        """Retorna o conteúdo raw (para editor de texto)."""
        if self._original_raw is not None:
            return self._original_raw
        return self.path.read_text(encoding="utf-8", errors="replace")

    def set_raw_content(self, text: str) -> None:
        self._modified_data = text
        self.modified = True


class ModGroup:
    """Agrupa arquivos de config de um mesmo mod."""

    def __init__(self, key: str) -> None:
        self.key = key
        self.display_name = mod_key_to_display(key)
        self.files: List[ConfigFile] = []
        self.expanded = False

    def add_file(self, cf: ConfigFile) -> None:
        self.files.append(cf)

    @property
    def has_parse_errors(self) -> bool:
        return any(f.parse_error for f in self.files if f.parse_error)


# ── Scanner ───────────────────────────────────────────────────────────────


class ConfigScanner:
    """Varre o diretório config/ e agrupa arquivos por mod."""

    FORMAT_MAP: Dict[str, str] = {
        ".toml": "toml",
        ".json": "json",
        ".json5": "json5",
        ".yaml": "yaml",
        ".yml": "yaml",
        ".cfg": "cfg",
        ".properties": "properties",
        ".txt": "txt",
        ".snbt": "snbt",
        ".ini": "ini",
    }

    def __init__(self, config_dir: Path) -> None:
        self.config_dir = config_dir.resolve()
        self.groups: Dict[str, ModGroup] = {}
        self._scanned = False

    def scan(self) -> List[ModGroup]:
        """Varre o diretório e retorna grupos ordenados."""
        if self._scanned:
            return list(self.groups.values())
        self._scanned = True

        log.info("Scanner: iniciando scan em %s", self.config_dir)

        # 1. Arquivos na raiz do config
        root_files = 0
        for entry in sorted(self.config_dir.iterdir()):
            if entry.is_file():
                self._process_file(entry)
                root_files += 1
        log.info("Scanner: %d arquivos na raiz", root_files)

        # 2. Subdiretórios (recursivo)
        subdirs = 0
        for entry in sorted(self.config_dir.iterdir()):
            if entry.is_dir() and not entry.name.startswith("."):
                mod_key = entry.name.lower()
                if mod_key not in self.groups:
                    self.groups[mod_key] = ModGroup(mod_key)
                self._scan_dir_recursive(entry, mod_key)
                subdirs += 1
        log.info("Scanner: %d subdiretorios processados", subdirs)

        total_files = sum(len(g.files) for g in self.groups.values())
        log.info("Scanner: %d mods, %d arquivos", len(self.groups), total_files)

        # Ordena grupos por nome
        return sorted(self.groups.values(), key=lambda g: g.display_name.lower())

    def _scan_dir_recursive(self, directory: Path, mod_key: str) -> None:
        """Varre recursivamente um diretório de config."""
        for entry in sorted(directory.iterdir()):
            if entry.name.startswith("."):
                continue
            if entry.is_file():
                self._process_file(entry, parent_mod=mod_key)
            elif entry.is_dir():
                self._scan_dir_recursive(entry, mod_key)

    def _process_file(self, path: Path, parent_mod: Optional[str] = None) -> None:
        """Processa um único arquivo."""
        if path.name.startswith("."):
            return
        # Pula backups
        if path.suffix == ".bak" or ".bak." in path.name or path.suffix in (".backup",):
            return
        if path.suffix not in self.FORMAT_MAP:
            # Tenta por nome (ex: arquivos sem extensão)
            return

        fmt = self.FORMAT_MAP[path.suffix]
        mod_key = parent_mod or extract_mod_key(path.name)

        if mod_key not in self.groups:
            self.groups[mod_key] = ModGroup(mod_key)
        self.groups[mod_key].add_file(ConfigFile(path, fmt))


# ── GUI ───────────────────────────────────────────────────────────────────

# Tema Minecraft
MC_DIRT = "#3B2E1E"
MC_DARK_OAK = "#1C1208"
MC_STONE = "#6B6B6B"
MC_GRASS = "#5A8F31"
MC_GOLD = "#E5A835"
MC_DIAMOND = "#4AAED4"
MC_REDSTONE = "#A83838"
MC_PARCHMENT = "#F5EFDF"
MC_COBBLESTONE = "#7A7A7A"
MC_WOOD = "#8B6914"
MC_EMERALD = "#47A84A"
MC_IRON = "#C8C8C8"
MC_NETHER = "#3D1A1A"
MC_CRAFTING = "#6B4226"
MC_SKYBLUE = "#8ECAE6"
MC_WATER = "#3A7BD5"

COLOR_BG = MC_DARK_OAK
COLOR_SURFACE = MC_DIRT
COLOR_PRIMARY = MC_WOOD
COLOR_ACCENT = MC_GOLD
COLOR_TEXT = MC_PARCHMENT
COLOR_TEXT_SECONDARY = MC_COBBLESTONE
COLOR_SUCCESS = MC_EMERALD
COLOR_WARNING = MC_GOLD
COLOR_TREE_HOVER = MC_CRAFTING
COLOR_BORDER = MC_STONE
COLOR_CODE_BG = "#0D0A05"
COLOR_BTN_HOVER = "#7A5C20"

# Fonte Minecraft-like — precisa de um root Tk temporario
import tkinter as _tk
_temp_root = _tk.Tk()
_temp_root.withdraw()
MC_FONT_FAMILY = "Courier" if not IS_WINDOWS else "Courier New"
MC_FONT_BOLD = ctk.CTkFont(family=MC_FONT_FAMILY, size=13, weight="bold")
MC_FONT = ctk.CTkFont(family=MC_FONT_FAMILY, size=12)
MC_FONT_SM = ctk.CTkFont(family=MC_FONT_FAMILY, size=11)
MC_FONT_LG = ctk.CTkFont(family=MC_FONT_FAMILY, size=16, weight="bold")
MC_FONT_TITLE = ctk.CTkFont(family=MC_FONT_FAMILY, size=18, weight="bold")
_temp_root.destroy()
del _tk, _temp_root


class InstanceSelector(ctk.CTkToplevel):
    """Janela de selecao de instancia — toplevel flutuante."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.title("Selecionar Instância Minecraft")
        self.geometry("640x380")
        self.resizable(False, False)

        self.result: Optional[str] = None

        self.update_idletasks()
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        self.geometry(f"+{sw // 2 - 320}+{sh // 2 - 190}")
        self.lift()
        self.focus_force()

        # Layout
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        title_lbl = ctk.CTkLabel(
            self,
            text="Editor de Config de Mods Minecraft",
            font=MC_FONT_TITLE,
            text_color=COLOR_ACCENT,
        )
        title_lbl.grid(row=0, column=0, pady=(30, 10))

        subtitle = ctk.CTkLabel(
            self,
            text="Selecione a instância do PrismLauncher/ElyPrismLauncher",
            font=MC_FONT,
            text_color=COLOR_TEXT_SECONDARY,
        )
        subtitle.grid(row=1, column=0, pady=(0, 20))

        # Frame do path
        path_frame = ctk.CTkFrame(self, fg_color=COLOR_SURFACE)
        path_frame.grid(row=2, column=0, padx=30, sticky="nsew")
        path_frame.grid_columnconfigure(1, weight=1)

        path_label = ctk.CTkLabel(
            path_frame, text="Caminho da instância:", font=MC_FONT_BOLD
        )
        path_label.grid(row=0, column=0, padx=(15, 10), pady=(20, 5), sticky="w")

        default_path = Path(
            os.path.expanduser(
                "~/.var/app/io.github.elyprismlauncher.ElyPrismLauncher"
                "/data/ElyPrismLauncher/instances"
            )
        )

        self.path_var = ctk.StringVar(
            value=str(default_path / "Abyssal Ascent") if default_path.exists() else ""
        )
        self.path_entry = ctk.CTkEntry(
            path_frame,
            textvariable=self.path_var,
            font=MC_FONT,
            placeholder_text="/caminho/para/instancia/minecraft",
        )
        self.path_entry.grid(row=1, column=0, columnspan=2, padx=15, pady=(0, 10), sticky="ew")

        browse_btn = ctk.CTkButton(
            path_frame,
            text="🗺️ Procurar",
            command=self._browse,
            fg_color=COLOR_PRIMARY,
            hover_color=COLOR_BTN_HOVER,
            width=100,
        )
        browse_btn.grid(row=2, column=0, padx=15, pady=(0, 5), sticky="w")

        self.status_label = ctk.CTkLabel(
            path_frame,
            text="",
            font=MC_FONT_SM,
            text_color=COLOR_TEXT_SECONDARY,
        )
        self.status_label.grid(row=3, column=0, columnspan=2, padx=15, pady=(0, 10), sticky="w")

        self.validate_btn = ctk.CTkButton(
            path_frame,
            text="Validar instância",
            command=self._validate,
            fg_color=COLOR_PRIMARY,
            hover_color=COLOR_BTN_HOVER,
            width=120,
        )
        self.validate_btn.grid(row=3, column=1, padx=15, pady=(0, 10), sticky="e")

        # Botão OK
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.grid(row=3, column=0, pady=20)
        btn_frame.grid_columnconfigure((0, 1), weight=1)

        ok_btn = ctk.CTkButton(
            btn_frame,
            text="Abrir Editor",
            command=self._confirm,
            fg_color=MC_EMERALD,
            hover_color="#3A853B",
            state="disabled",
            width=160,
            height=38,
            font=MC_FONT_BOLD,
        )
        ok_btn.grid(row=0, column=1, padx=(10, 0))

        cancel_btn = ctk.CTkButton(
            btn_frame,
            text="Cancelar",
            command=self._cancel,
            fg_color=MC_REDSTONE,
            hover_color="#8E2E2E",
            width=100,
        )
        cancel_btn.grid(row=0, column=0, padx=(0, 10))

        self.ok_btn = ok_btn
        self._validated = False

        # Enter key binding
        self.bind("<Return>", lambda e: self._confirm())

    def _browse(self) -> None:
        from tkinter import filedialog

        path = filedialog.askdirectory(
            title="Selecione a pasta da instância",
            mustexist=True,
        )
        if path:
            self.path_var.set(path)
            self._validated = False
            self.ok_btn.configure(state="disabled")
            self.status_label.configure(text="Clique em 'Validar instância' para verificar")

    def _validate(self) -> None:
        path_str = self.path_var.get().strip()
        if not path_str:
            self.status_label.configure(text="⚠ Caminho vazio.", text_color=COLOR_WARNING)
            return

        inst_path = Path(path_str).expanduser().resolve()

        # Procura pelo diretório minecraft
        if (inst_path / "minecraft" / "config").is_dir():
            config_dir = inst_path / "minecraft" / "config"
        elif (inst_path / "config").is_dir():
            config_dir = inst_path / "config"
        elif (inst_path / "minecraft").is_dir():
            # Pode ser a pasta minecraft diretamente
            config_dir = inst_path / "config" if (inst_path / "config").is_dir() else None
        else:
            config_dir = None

        if config_dir is None:
            self.status_label.configure(
                text="✗ Instância inválida — diretório 'config/' não encontrado.",
                text_color=COLOR_ACCENT,
            )
            self._validated = False
            self.ok_btn.configure(state="disabled")
            return

        # Conta configs
        toml_files = list(config_dir.rglob("*.toml"))
        json_files = list(config_dir.rglob("*.json"))
        total = len(toml_files) + len(json_files)
        self.status_label.configure(
            text=f"✓ Instância válida! {total} arquivos de config encontrados.",
            text_color=COLOR_SUCCESS,
        )
        self._validated = True
        self._config_dir = config_dir
        self._instance_path = inst_path
        self.ok_btn.configure(state="normal")

    def _confirm(self) -> None:
        if not self._validated:
            return
        self.result = str(self._config_dir)
        self.destroy()

    def _cancel(self) -> None:
        self.result = None
        self.destroy()


# ── Editor de Parâmetros ──────────────────────────────────────────────────


class ParameterEditor(ctk.CTkScrollableFrame):
    """Painel direito que exibe e edita os parâmetros de um arquivo."""

    def __init__(self, master: Any, **kwargs: Any) -> None:
        super().__init__(master, **kwargs)
        self.current_file: Optional[ConfigFile] = None
        self._widgets: Dict[str, Any] = {}
        self._key_paths: Dict[str, List[str]] = {}
        self._callbacks: List = []

    def load_file(self, cf: ConfigFile) -> None:
        """Carrega um arquivo para edição."""
        self.current_file = cf
        self._widgets.clear()
        self._key_paths.clear()

        # Limpa o frame
        for w in self.winfo_children():
            w.destroy()

        if cf.parse_error:
            self._show_error(cf)
            return

        if not cf.parsed_ok:
            cf.parse()
            if cf.parse_error:
                self._show_error(cf)
                return

        # Header
        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.pack(fill="x", padx=10, pady=(10, 5))
        header_frame.grid_columnconfigure(0, weight=1)

        name_lbl = ctk.CTkLabel(
            header_frame,
            text=cf.display_name,
            font=MC_FONT_TITLE,
            text_color=COLOR_ACCENT,
            anchor="w",
        )
        name_lbl.grid(row=0, column=0, sticky="w")

        fmt_lbl = ctk.CTkLabel(
            header_frame,
            text=cf.format_label,
            font=MC_FONT_SM,
            text_color=COLOR_TEXT_SECONDARY,
            anchor="w",
        )
        fmt_lbl.grid(row=1, column=0, sticky="w")

        sep = ctk.CTkFrame(header_frame, height=2, fg_color=COLOR_ACCENT, corner_radius=1)
        sep.grid(row=2, column=0, sticky="ew", pady=(10, 0))

        if cf.is_structured:
            self._build_structured_editor(cf)
        else:
            self._build_raw_editor(cf)

    def _show_error(self, cf: ConfigFile) -> None:
        """Mostra mensagem de erro."""
        err_frame = ctk.CTkFrame(self, fg_color=MC_NETHER)
        err_frame.pack(fill="x", padx=20, pady=20)

        ctk.CTkLabel(
            err_frame,
            text="Erro ao ler arquivo",
            font=MC_FONT_BOLD,
            text_color=COLOR_ACCENT,
        ).pack(padx=20, pady=(15, 5), anchor="w")

        ctk.CTkLabel(
            err_frame,
            text=cf.parse_error or "Erro desconhecido",
            font=MC_FONT,
            text_color=COLOR_TEXT,
            wraplength=500,
            justify="left",
        ).pack(padx=20, pady=(0, 15), anchor="w")

    def _build_structured_editor(self, cf: ConfigFile) -> None:
        """Constrói o editor visual para arquivos estruturados."""
        data = cf._modified_data
        if isinstance(data, dict):
            self._render_dict(cf, data, [], 0)
        elif isinstance(data, list):
            self._render_list(cf, data, ["_root"], 0)
        else:
            self._render_scalar(cf, "", data, ["_root"], 0)

    def _render_dict(
        self, cf: ConfigFile, d: Dict, prefix: List[str], depth: int
    ) -> None:
        """Renderiza um dicionário recursivamente."""
        for key in d.keys():
            key_path = prefix + [key]
            value = d[key]
            if isinstance(value, dict):
                # Seção aninhada
                self._add_section_header(key, depth)
                self._render_dict(cf, value, key_path, depth + 1)
            elif isinstance(value, list):
                self._add_param_row(cf, key, value, key_path, depth)
            else:
                self._add_param_row(cf, key, value, key_path, depth)

    def _add_section_header(self, name: str, depth: int) -> None:
        pad = 10 + depth * 20
        f = ctk.CTkFrame(self, fg_color=COLOR_SURFACE, corner_radius=4)
        f.pack(fill="x", padx=pad, pady=(8, 2))

        lbl = ctk.CTkLabel(
            f,
            text=f"[ {name} ]",
            font=MC_FONT_BOLD,
            text_color=COLOR_PRIMARY,
            anchor="w",
        )
        lbl.pack(padx=12, pady=4, fill="x")

    def _add_param_row(
        self, cf: ConfigFile, key: str, value: Any, key_path: List[str], depth: int
    ) -> None:
        pad = 10 + depth * 20

        frame = ctk.CTkFrame(self, fg_color="transparent")
        frame.pack(fill="x", padx=pad, pady=2)
        frame.grid_columnconfigure(1, weight=1)

        # Label
        lbl_text = key
        if isinstance(value, bool):
            lbl_text += "  [bool]"
        elif isinstance(value, int):
            lbl_text += "  [int]"
        elif isinstance(value, float):
            lbl_text += "  [float]"
        elif isinstance(value, str):
            lbl_text += "  [text]"
        elif isinstance(value, list):
            lbl_text += f"  [list ({len(value)} itens)]"

        # Tooltip-like hint: show current value next to label
        lbl = ctk.CTkLabel(
            frame,
            text=lbl_text,
            font=MC_FONT,
            text_color=COLOR_TEXT,
            anchor="w",
            width=200,
        )
        lbl.grid(row=0, column=0, padx=(5, 10), pady=2, sticky="w")

        # Widget de edição
        widget_id = ".".join(key_path)
        self._key_paths[widget_id] = key_path

        if isinstance(value, bool):
            var = ctk.BooleanVar(value=value)
            cb = ctk.CTkSwitch(
                frame,
                text="",
                variable=var,
                onvalue=True,
                offvalue=False,
                command=lambda wid=widget_id: self._on_change(cf, wid),
                progress_color=COLOR_ACCENT,
            )
            cb.grid(row=0, column=1, padx=(0, 5), pady=2, sticky="w")
            self._widgets[widget_id] = var

        elif isinstance(value, int):
            var = ctk.StringVar(value=str(value))
            entry = ctk.CTkEntry(
                frame,
                textvariable=var,
                width=120,
                font=MC_FONT,
                justify="center",
                validate="key",
                validatecommand=(self.register(self._validate_int), "%P"),
            )
            entry.grid(row=0, column=1, padx=(0, 5), pady=2, sticky="w")
            # Track changes
            var.trace_add("write", lambda *a, wid=widget_id: self._on_change(cf, wid))
            self._widgets[widget_id] = var

        elif isinstance(value, float):
            var = ctk.StringVar(value=str(value))
            entry = ctk.CTkEntry(
                frame,
                textvariable=var,
                width=120,
                font=MC_FONT,
                justify="center",
                validate="key",
                validatecommand=(self.register(self._validate_float), "%P"),
            )
            entry.grid(row=0, column=1, padx=(0, 5), pady=2, sticky="w")
            var.trace_add("write", lambda *a, wid=widget_id: self._on_change(cf, wid))
            self._widgets[widget_id] = var

        elif isinstance(value, str):
            if len(value) > 60:
                # Texto longo — expande
                var = ctk.StringVar(value=value)
                txt = ctk.CTkTextbox(frame, height=60, width=300, font=MC_FONT_SM)
                txt.insert("1.0", value)
                txt.grid(row=0, column=1, padx=(0, 5), pady=2, sticky="ew")
                # Auto-save on focus loss
                txt.bind(
                    "<FocusOut>",
                    lambda e, wid=widget_id, t=txt: self._on_change_text(cf, wid, t),
                )
                self._widgets[widget_id] = txt
            else:
                var = ctk.StringVar(value=value)
                entry = ctk.CTkEntry(
                    frame,
                    textvariable=var,
                    font=MC_FONT,
                )
                entry.grid(row=0, column=1, padx=(0, 5), pady=2, sticky="ew")
                var.trace_add("write", lambda *a, wid=widget_id: self._on_change(cf, wid))
                self._widgets[widget_id] = var

        elif isinstance(value, list):
            # Mostra como textbox multi-linha
            txt_val = "\n".join(str(item) for item in value)
            txt = ctk.CTkTextbox(frame, height=60, width=300, font=MC_FONT_SM)
            txt.insert("1.0", txt_val)
            txt.grid(row=0, column=1, padx=(0, 5), pady=2, sticky="ew")
            txt.bind(
                "<FocusOut>",
                lambda e, wid=widget_id, t=txt: self._on_change_list(cf, wid, t),
            )
            self._widgets[widget_id] = txt

        else:
            # Fallback: mostra como string
            var = ctk.StringVar(value=str(value) if value is not None else "")
            entry = ctk.CTkEntry(
                frame,
                textvariable=var,
                font=MC_FONT,
            )
            entry.grid(row=0, column=1, padx=(0, 5), pady=2, sticky="ew")
            var.trace_add("write", lambda *a, wid=widget_id: self._on_change(cf, wid))
            self._widgets[widget_id] = var

    def _render_list(self, cf: ConfigFile, lst: List, prefix: List[str], depth: int) -> None:
        self._add_section_header(f"Array ({len(lst)} itens)", depth)
        # Para listas simples, mostra como área de texto editável
        frame = ctk.CTkFrame(self, fg_color="transparent")
        frame.pack(fill="x", padx=10 + depth * 20, pady=2)
        frame.grid_columnconfigure(0, weight=1)

        txt_val = "\n".join(str(item) for item in lst)
        txt = ctk.CTkTextbox(frame, height=max(60, min(200, len(lst) * 20)), font=MC_FONT_SM)
        txt.insert("1.0", txt_val)
        txt.grid(row=0, column=0, sticky="ew")
        txt.bind(
            "<FocusOut>",
            lambda e, wid="__list__", t=txt: self._on_change_list(cf, "_root", t),
        )
        self._widgets["__list__"] = txt

    def _render_scalar(self, cf: ConfigFile, key: str, value: Any, key_path: List[str], depth: int) -> None:
        self._add_param_row(cf, key or "(valor)", value, key_path, depth)

    def _build_raw_editor(self, cf: ConfigFile) -> None:
        """Constrói editor de texto raw."""
        self._raw_text_dirty = False
        raw = cf.raw_content()

        txt = ctk.CTkTextbox(self, font=ctk.CTkFont(family="Consolas, monospace", size=12), wrap="none")
        txt.pack(fill="both", expand=True, padx=10, pady=10)
        txt.insert("1.0", raw)
        txt.bind("<<Modified>>", lambda e: self._on_raw_modified(txt))
        txt.bind("<FocusOut>", lambda e: self._on_raw_focus_out(cf, txt))
        self._widgets["__raw__"] = txt

    def _on_raw_modified(self, txt: ctk.CTkTextbox) -> None:
        if txt.edit_modified():
            self._raw_text_dirty = True
            txt.edit_modified(False)

    def _on_raw_focus_out(self, cf: ConfigFile, txt: ctk.CTkTextbox) -> None:
        if self._raw_text_dirty:
            content = txt.get("1.0", "end-1c")
            cf.set_raw_content(content)
            self._raw_text_dirty = False

    def _validate_int(self, value: str) -> bool:
        if value == "" or value == "-":
            return True
        try:
            int(value)
            return True
        except ValueError:
            return False

    def _validate_float(self, value: str) -> bool:
        if value == "" or value == "-" or value == ".":
            return True
        try:
            float(value)
            return True
        except ValueError:
            return False

    def _on_change(self, cf: ConfigFile, widget_id: str) -> None:
        """Called when a parameter widget changes."""
        key_path = self._key_paths.get(widget_id)
        if not key_path:
            return
        widget = self._widgets.get(widget_id)
        if widget is None:
            return

        try:
            if isinstance(widget, ctk.BooleanVar):
                cf.set_value(key_path, widget.get())
            elif isinstance(widget, ctk.StringVar):
                raw = widget.get()
                # Tenta inferir tipo
                current = cf.get_value(key_path)
                if isinstance(current, int):
                    try:
                        cf.set_value(key_path, int(raw))
                    except ValueError:
                        cf.set_value(key_path, raw)
                elif isinstance(current, float):
                    try:
                        cf.set_value(key_path, float(raw))
                    except ValueError:
                        cf.set_value(key_path, raw)
                else:
                    cf.set_value(key_path, raw)
        except Exception:
            pass

    def _on_change_text(self, cf: ConfigFile, widget_id: str, txt: ctk.CTkTextbox) -> None:
        key_path = self._key_paths.get(widget_id)
        if not key_path:
            return
        value = txt.get("1.0", "end-1c")
        cf.set_value(key_path, value)

    def _on_change_list(self, cf: ConfigFile, widget_id: str, txt: ctk.CTkTextbox) -> None:
        key_path = self._key_paths.get(widget_id)
        if not key_path and widget_id == "_root":
            key_path = ["_root"]
            # Parse list items
            text = txt.get("1.0", "end-1c")
            items = [line.strip() for line in text.split("\n") if line.strip()]
            # Try to convert types
            typed_items = []
            for item in items:
                try:
                    typed_items.append(int(item))
                except ValueError:
                    try:
                        typed_items.append(float(item))
                    except ValueError:
                        typed_items.append(item)
            if cf._modified_data is not None and isinstance(cf._modified_data, list):
                # Update in-place is tricky for lists — replace the content
                cf._modified_data[:] = typed_items
                cf.modified = True
                return
            return
        if not key_path:
            return
        text = txt.get("1.0", "end-1c")
        items = [line.strip() for line in text.split("\n") if line.strip()]
        typed_items = []
        for item in items:
            try:
                typed_items.append(int(item))
            except ValueError:
                try:
                    typed_items.append(float(item))
                except ValueError:
                    typed_items.append(item)
        cf.set_value(key_path, typed_items)


# ── Tree View ──────────────────────────────────────────────────────────────


class FileTreeItem(ctk.CTkFrame):
    """Um item na árvore de arquivos (mod ou arquivo individual)."""

    def __init__(
        self,
        master: Any,
        label: str,
        subtitle: str = "",
        icon: str = "",
        is_mod: bool = False,
        file_ref: Optional[ConfigFile] = None,
        on_select: Optional[callable] = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(master, fg_color="transparent", **kwargs)
        self.is_mod = is_mod
        self.file_ref = file_ref
        self.on_select = on_select
        self._children_frame: Optional[ctk.CTkFrame] = None
        self._child_widgets: List[ctk.CTkFrame] = []
        self._expanded = False

        self.grid_columnconfigure(0, weight=0)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=0)
        self.grid_rowconfigure(1, weight=0)

        hover_color = COLOR_TREE_HOVER

        if is_mod:
            self.btn = ctk.CTkButton(
                self,
                text=f"  {icon} {label}",
                anchor="w",
                fg_color="transparent",
                text_color=COLOR_TEXT,
                hover_color=hover_color,
                font=MC_FONT_BOLD,
                command=self._toggle,
                corner_radius=4,
            )
        else:
            self.btn = ctk.CTkButton(
                self,
                text=f"  {icon} {label}",
                anchor="w",
                fg_color="transparent",
                text_color=COLOR_TEXT_SECONDARY,
                hover_color=hover_color,
                font=MC_FONT,
                command=self._select,
                corner_radius=4,
            )
        self.btn.grid(row=0, column=0, columnspan=2, sticky="ew", padx=2, pady=1)

        if subtitle:
            sub_lbl = ctk.CTkLabel(
                self,
                text=subtitle,
                font=MC_FONT_SM,
                text_color=COLOR_TEXT_SECONDARY,
                anchor="w",
            )
            sub_lbl.grid(row=0, column=1, sticky="e", padx=(0, 8))

    def get_child_container(self) -> ctk.CTkFrame:
        if self._children_frame is None:
            self._children_frame = ctk.CTkFrame(self, fg_color="transparent")
        return self._children_frame

    def get_children(self) -> List:
        return self._child_widgets

    def add_child(self, child_widget: ctk.CTkFrame) -> None:
        self._child_widgets.append(child_widget)
        child_widget.pack(in_=self.get_child_container(), fill="x", padx=(20, 0))

    def _toggle(self) -> None:
        if not self.is_mod:
            return
        self._expanded = not self._expanded
        if self._children_frame:
            if self._expanded:
                self._children_frame.grid(row=1, column=0, columnspan=2, sticky="ew", padx=(20, 0))
            else:
                self._children_frame.grid_remove()
        # Update icon
        icon = "▼" if self._expanded else "▶"
        current = self.btn.cget("text")
        clean = re.sub(r'^[▶▼]\s*', '', current)
        self.btn.configure(text=f"{icon} {clean}")

    def _select(self) -> None:
        log.debug("FileTreeItem._select: file_ref=%s", self.file_ref)
        if self.on_select and self.file_ref:
            self.on_select(self.file_ref)

    def set_expanded(self, expanded: bool) -> None:
        self._expanded = not expanded  # force toggle
        self._toggle()

    def is_expanded(self) -> bool:
        return self._expanded


class TreePanel(ctk.CTkScrollableFrame):
    """Painel esquerdo com a árvore de mods."""

    def __init__(self, master: Any, on_file_select: Optional[callable] = None, **kwargs: Any) -> None:
        super().__init__(master, **kwargs)
        self.on_file_select = on_file_select
        self._items: Dict[str, FileTreeItem] = {}
        self._mod_frames: Dict[str, ctk.CTkFrame] = {}
        self._file_items: Dict[str, FileTreeItem] = {}

    def load_groups(self, groups: List[ModGroup]) -> None:
        """Popula a árvore com grupos de mods."""
        for w in self.winfo_children():
            w.destroy()
        self._items.clear()
        self._mod_frames.clear()
        self._file_items.clear()

        for group in groups:
            # Mod header
            has_files = len(group.files) > 0
            has_errors = group.has_parse_errors

            icon = "⚠" if has_errors else "🧱"
            item = FileTreeItem(
                self,
                label=f"{group.display_name}",
                subtitle=f"{len(group.files)} arquivo(s)",
                icon=icon,
                is_mod=True,
            )
            item.pack(fill="x", padx=5, pady=1)
            self._items[group.key] = item

            # File children
            child_container = item.get_child_container()
            for cf in group.files:
                file_icon = self._file_icon(cf)
                child = FileTreeItem(
                    child_container,
                    label=cf.display_name,
                    subtitle=cf.format_label.split()[0],
                    icon=file_icon,
                    is_mod=False,
                    file_ref=cf,
                    on_select=self._on_file_selected,
                )
                item.add_child(child)
                self._file_items[cf.path.name] = child

            # Auto-expand first few mods
            if has_files and len(groups) <= 15:
                item._expanded = True  # trick: set true so toggle makes it true → false → show
                item._expanded = False
                item._toggle()

    def _file_icon(self, cf: ConfigFile) -> str:
        icons = {
            "toml": "⚙",
            "json": "🛠",
            "json5": "🛠",
            "yaml": "📜",
            "cfg": "🏷",
            "properties": "🏷",
            "txt": "🏷",
            "snbt": "🏷",
            "ini": "🏷",
        }
        return icons.get(cf.fmt, "🏷")

    def _on_file_selected(self, cf: ConfigFile) -> None:
        log.debug("TreePanel._on_file_selected: %s", cf.path.name)
        if self.on_file_select:
            self.on_file_select(cf)

    def highlight_file(self, filename: str) -> None:
        """Destaca visualmente o arquivo selecionado."""
        for name, widget in self._file_items.items():
            # Reset all
            widget.btn.configure(fg_color="transparent")
        item = self._file_items.get(filename)
        if item:
            item.btn.configure(fg_color=COLOR_PRIMARY)


# ── Aplicação Principal ───────────────────────────────────────────────────


class ConfigEditorApp(ctk.CTk):
    """Aplicação principal do editor de config."""

    def __init__(self, config_dir: Optional[str] = None) -> None:
        super().__init__()
        self.title("Minecraft Mod Config Editor")
        self.geometry("1300x800")
        self.minsize(900, 600)

        # Grid: header(row=0) | tree+editor(row=1) | action(row=2) | status(row=3)
        self.grid_columnconfigure(0, weight=0)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=0)
        self.grid_rowconfigure(1, weight=1)
        self.grid_rowconfigure(2, weight=0)
        self.grid_rowconfigure(3, weight=0)

        # Dados
        self._groups: List[ModGroup] = []
        self._current_file: Optional[ConfigFile] = None

        # ── Header (row 0) ──
        self._build_header()

        # ── Tree panel (row 1, col 0) ──
        tree_frame = ctk.CTkFrame(self, fg_color=COLOR_SURFACE, corner_radius=0)
        tree_frame.grid(row=1, column=0, sticky="nswe")
        tree_frame.grid_rowconfigure(1, weight=1)
        tree_frame.grid_columnconfigure(0, weight=1)

        tree_header = ctk.CTkLabel(
            tree_frame,
            text="⛏ Mods",
            font=MC_FONT_BOLD,
            text_color=COLOR_TEXT,
            anchor="w",
        )
        tree_header.grid(row=0, column=0, padx=12, pady=(10, 5), sticky="w")

        self.tree_panel = TreePanel(
            tree_frame,
            on_file_select=self._on_file_select,
            fg_color="transparent",
            corner_radius=0,
        )
        self.tree_panel.grid(row=1, column=0, sticky="nswe", padx=5, pady=(0, 5))

        # ── Editor panel ──
        editor_frame = ctk.CTkFrame(self, fg_color=COLOR_BG, corner_radius=0)
        editor_frame.grid(row=1, column=1, sticky="nswe")
        editor_frame.grid_rowconfigure(0, weight=1)
        editor_frame.grid_columnconfigure(0, weight=1)

        # Placeholder central quando nenhum arquivo está selecionado
        self._placeholder = ctk.CTkFrame(editor_frame, fg_color="transparent")
        self._placeholder.grid(row=0, column=0, sticky="nswe")
        self._placeholder.grid_columnconfigure(0, weight=1)
        self._placeholder.grid_rowconfigure(0, weight=1)
        self._placeholder.grid_rowconfigure(1, weight=1)

        placeholder_icon = ctk.CTkLabel(
            self._placeholder,
            text="🏰",
            font=ctk.CTkFont(size=72),
            text_color=MC_GOLD,
        )
        placeholder_icon.grid(row=0, column=0)

        placeholder_text = ctk.CTkLabel(
            self._placeholder,
            text="Selecione um arquivo de configuração na árvore ao lado\npara começar a editar.",
            font=MC_FONT,
            text_color=COLOR_TEXT_SECONDARY,
            justify="center",
        )
        placeholder_text.grid(row=1, column=0, pady=(10, 0))

        self.editor_panel = ParameterEditor(
            editor_frame,
            fg_color="transparent",
            corner_radius=0,
            scrollbar_button_color=MC_STONE,
        )

        # ── Status bar ──
        self._build_status_bar()

        # ── Botões de ação ──
        self._build_action_bar(editor_frame)

        # Carrega dados se config_dir foi fornecido
        if config_dir:
            self._load_configs(config_dir)

        # Bind teclas
        self.bind("<Control-s>", lambda e: self._save_current())
        self.bind("<Control-q>", lambda e: self.destroy())

    def _build_header(self) -> None:
        header = ctk.CTkFrame(self, fg_color=COLOR_SURFACE, height=48, corner_radius=0)
        header.grid(row=0, column=0, columnspan=2, sticky="ew", padx=0, pady=0)
        header.grid_columnconfigure(0, weight=1)
        header.grid_propagate(False)

        title = ctk.CTkLabel(
            header,
            text="⛏ Minecraft Mod Config Editor",
            font=MC_FONT_LG,
            text_color=COLOR_ACCENT,
            anchor="w",
        )
        title.grid(row=0, column=0, padx=15, pady=8, sticky="w")

        self.instance_label = ctk.CTkLabel(
            header,
            text="",
            font=MC_FONT_SM,
            text_color=COLOR_TEXT_SECONDARY,
            anchor="e",
        )
        self.instance_label.grid(row=0, column=1, padx=15, pady=8, sticky="e")

    def _build_status_bar(self) -> None:
        status_bar = ctk.CTkFrame(self, fg_color=COLOR_SURFACE, height=28, corner_radius=0)
        status_bar.grid(row=3, column=0, columnspan=2, sticky="ew")
        status_bar.grid_columnconfigure(0, weight=1)
        status_bar.grid_propagate(False)

        self.status_var = ctk.StringVar(value="✅ Pronto. Selecione um arquivo para editar.")
        status_label = ctk.CTkLabel(
            status_bar,
            textvariable=self.status_var,
            font=MC_FONT_SM,
            text_color=COLOR_TEXT_SECONDARY,
            anchor="w",
        )
        status_label.grid(row=0, column=0, padx=12, pady=2, sticky="w")

    def _build_action_bar(self, editor_frame: ctk.CTkFrame) -> None:
        action_frame = ctk.CTkFrame(self, fg_color=COLOR_SURFACE, height=50, corner_radius=0)
        action_frame.grid(row=2, column=0, columnspan=2, sticky="ew")
        action_frame.grid_columnconfigure(0, weight=1)
        action_frame.grid_propagate(False)

        # File info
        self.file_info_var = ctk.StringVar(value="Nenhum arquivo selecionado")
        file_info = ctk.CTkLabel(
            action_frame,
            textvariable=self.file_info_var,
            font=MC_FONT_SM,
            text_color=COLOR_TEXT_SECONDARY,
            anchor="w",
        )
        file_info.grid(row=0, column=0, padx=15, pady=2, sticky="w")

        # Buttons
        btn_frame = ctk.CTkFrame(action_frame, fg_color="transparent")
        btn_frame.grid(row=0, column=1, padx=10, pady=2, sticky="e")

        self.backup_btn = ctk.CTkButton(
            btn_frame,
            text="💾 Backup",
            command=self._backup_current,
            fg_color=MC_DIAMOND,
            hover_color="#3A95C4",
            width=90,
            state="disabled",
        )
        self.backup_btn.pack(side="left", padx=3)

        self.cancel_btn = ctk.CTkButton(
            btn_frame,
            text="↩ Cancelar",
            command=self._cancel_changes,
            fg_color=MC_REDSTONE,
            hover_color="#8E2E2E",
            width=90,
            state="disabled",
        )
        self.cancel_btn.pack(side="left", padx=3)

        self.save_btn = ctk.CTkButton(
            btn_frame,
            text="💾 Salvar",
            command=self._save_current,
            fg_color=MC_EMERALD,
            hover_color="#3A853B",
            width=100,
            state="disabled",
            font=MC_FONT_BOLD,
        )
        self.save_btn.pack(side="left", padx=3)

    def _load_configs(self, config_dir_str: str) -> None:
        """Carrega e exibe as configurações."""
        config_dir = Path(config_dir_str)
        if not config_dir.is_dir():
            self.status_var.set(f"✗ Diretório não encontrado: {config_dir}")
            return

        # Atualiza label
        inst_name = config_dir.parent.name if config_dir.parent.name != "minecraft" else config_dir.parent.parent.name
        self.instance_label.configure(text=f"📁 {inst_name}")

        try:
            scanner = ConfigScanner(config_dir)
            self._groups = scanner.scan()
            self.tree_panel.load_groups(self._groups)
            total_files = sum(len(g.files) for g in self._groups)
            self.status_var.set(
                f"✅ {len(self._groups)} mods, {total_files} arquivos de configuração carregados."
            )
        except Exception as e:
            self.status_var.set(f"✗ Erro ao carregar configs: {e}")

    def _on_file_select(self, cf: ConfigFile) -> None:
        """Callback quando um arquivo é selecionado na árvore."""
        log.info("_on_file_select: %s (%s)", cf.path.name, cf.fmt)
        self._current_file = cf
        self.tree_panel.highlight_file(cf.path.name)

        # Parse se necessário
        if not cf.parsed_ok:
            cf.parse()

        # Mostra editor
        self._placeholder.grid_forget()
        self.editor_panel.grid(row=0, column=0, sticky="nswe")
        self.update_idletasks()

        # Recarrega o editor
        self.editor_panel.load_file(cf)
        log.info("Editor carregado para %s, parsed_ok=%s", cf.path.name, cf.parsed_ok)

        # Atualiza info
        mod_name = "?"
        for g in self._groups:
            if any(f.path == cf.path for f in g.files):
                mod_name = g.display_name
                break

        modified_str = " ⚠ Modificado" if cf.modified else ""
        self.file_info_var.set(f"{mod_name} › {cf.display_name}{modified_str}  |  {cf.format_label}")

        # Habilita botões
        self.save_btn.configure(state="normal" if cf.parsed_ok else "disabled")
        self.cancel_btn.configure(state="normal" if cf.modified else "disabled")
        self.backup_btn.configure(state="normal")

        self.status_var.set(f"📝 Editando: {cf.path.name}")

    def _backup_current(self) -> None:
        """Faz backup do arquivo atual."""
        if not self._current_file:
            return
        bak = self._current_file.backup()
        if bak:
            self.status_var.set(f"✅ Backup criado: {bak.name}")
        else:
            self.status_var.set("✗ Erro ao criar backup.")

    def _cancel_changes(self) -> None:
        """Cancela as alterações e recarrega o arquivo."""
        if not self._current_file:
            return
        if not self._current_file.modified:
            return

        cf = self._current_file
        # Re-parse do zero
        cf.parsed_ok = False
        cf._modified_data = None
        cf.modified = False
        cf.parse()

        # Recarrega editor
        self.editor_panel.load_file(cf)

        # Atualiza info
        self.file_info_var.set(
            f"{self.file_info_var.get().split(' ⚠')[0]}  |  {cf.format_label}"
        )
        self.cancel_btn.configure(state="disabled")
        self.status_var.set("↩ Alterações descartadas. Arquivo recarregado.")

    def _save_current(self) -> None:
        """Salva o arquivo atual."""
        if not self._current_file:
            return

        # Força atualização de widgets raw
        if not self._current_file.is_structured:
            raw_widget = self.editor_panel._widgets.get("__raw__")
            if raw_widget and self.editor_panel._raw_text_dirty:
                content = raw_widget.get("1.0", "end-1c")
                self._current_file.set_raw_content(content)
                self.editor_panel._raw_text_dirty = False

        if not self._current_file.modified:
            self.status_var.set("ℹ Nenhuma alteração para salvar.")
            return

        ok, msg = self._current_file.save()
        if ok:
            self.status_var.set(f"✅ {msg}")
            self.file_info_var.set(
                f"{self.file_info_var.get().split(' ⚠')[0]}  |  {self._current_file.format_label}"
            )
            self.cancel_btn.configure(state="disabled")
            # Recarrega editor para refletir estado limpo
            self.editor_panel.load_file(self._current_file)
        else:
            self.status_var.set(f"✗ {msg}")


# ── Parser de argumentos ─────────────────────────────────────────────────


def parse_args() -> Tuple[Optional[str], bool]:
    """Parseia argumentos da linha de comando."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Minecraft Mod Config Editor - GUI para editar configs de mods",
        epilog="Exemplo: python3 mc-config-editor.py --instance ~/PrismLauncher/instances/MinhaInstancia",
    )
    parser.add_argument(
        "--instance", "-i",
        type=str,
        default=None,
        help="Caminho para a pasta da instância (contendo minecraft/config/)",
    )
    parser.add_argument(
        "--no-instance-dialog",
        action="store_true",
        help="Não mostrar diálogo de seleção se --instance não for fornecido",
    )
    return parser.parse_args()


# ── Entry point ───────────────────────────────────────────────────────────


def main() -> None:
    import atexit
    atexit.register(lambda: logging.shutdown())
    log.info("Logging configurado, handlers: %d", len(logging.root.handlers))

    args = parse_args()
    log.info("Args: %s", sys.argv)

    try:
        app = ConfigEditorApp()
        config_dir: Optional[Path] = None

        if args.instance:
            inst_path = Path(args.instance).expanduser().resolve()
            log.info("Instancia via arg: %s", inst_path)
            if (inst_path / "minecraft" / "config").is_dir():
                config_dir = inst_path / "minecraft" / "config"
            elif (inst_path / "config").is_dir():
                config_dir = inst_path / "config"
            else:
                config_dir = inst_path
        else:
            log.info("Abrindo dialogo de selecao de instancia...")
            print("📂 Abrindo seletor de instância...", file=sys.stderr)
            from tkinter import filedialog
            app.withdraw()
            initial_dir = str(DEFAULT_LAUNCHER_PATHS[0]) if DEFAULT_LAUNCHER_PATHS else str(Path.home())
            path = filedialog.askdirectory(
                title="Selecione a pasta da instância Minecraft",
                initialdir=initial_dir,
                mustexist=True,
            )
            if not path:
                log.info("Dialogo cancelado pelo usuario")
                print("❌ Cancelado pelo usuário.", file=sys.stderr)
                app.destroy()
                return
            app.deiconify()
            config_dir = Path(path)

        assert config_dir is not None
        log.info("Carregando configs de %s", config_dir)
        app._load_configs(str(config_dir))
        log.info("Configs carregadas, entrando no mainloop")
        print("✅ Editor carregado. A janela deve estar aberta.", file=sys.stderr)
        app.mainloop()
        log.info("Mainloop encerrado normalmente")

    except Exception:
        log.critical("Erro fatal:\n%s", traceback.format_exc())
        logging.shutdown()
        print(f"\n❌ Erro fatal - veja o log: {LOG_FILE}\n", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
mc-config-editor-qt.py — Minecraft Mod Config Editor — by Makalove

GUI em PyQt6 com tema customizavel via CSS/QSS.
Multiplataforma: Windows, Linux, macOS.
Salva automaticamente a ultima instancia usada.
Suporta CSS customizado pelo usuario.
"""

import datetime
import json
import logging
import os
import platform
import re
import shutil
import sys
import zipfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# PyQt6
from PyQt6.QtCore import Qt, QLocale, QSettings, QSize, QTimer, QTranslator, QUrl, pyqtSignal
from PyQt6.QtGui import QAction, QDesktopServices, QIcon, QPixmap
from PyQt6.QtNetwork import QNetworkAccessManager, QNetworkReply, QNetworkRequest
from PyQt6.QtWidgets import (
    QAbstractItemView, QApplication, QDialog, QFileDialog, QFrame, QHBoxLayout,
    QHeaderView, QLabel, QLineEdit, QMainWindow, QMenu, QMenuBar,
    QMessageBox, QPushButton, QScrollArea, QSizePolicy,
    QSplitter, QStackedWidget, QStatusBar, QTabWidget, QTextEdit, QTreeWidget,
    QTreeWidgetItem, QVBoxLayout, QWidget,
)

# ── Path resolution ─────────────────────────────────────────────────────
# In PyInstaller onefile: __file__ points to temp extraction dir.
# Use executable's directory for persistent files (logs, custom CSS, icons).

if getattr(sys, 'frozen', False):
    SCRIPT_DIR = Path(sys.executable).resolve().parent
    _MEIPASS_DIR = Path(sys._MEIPASS)
else:
    SCRIPT_DIR = Path(__file__).resolve().parent
    _MEIPASS_DIR = None

# ── Logging ─────────────────────────────────────────────────────────────

VERSION = "1.1.4"
GITHUB_RELEASES_API = "https://api.github.com/repos/Adiog0/mc-mod-config/releases/latest"
GITHUB_RELEASES_URL = "https://github.com/Adiog0/mc-mod-config/releases"
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
log.info("=== mc-config-editor (PyQt6) iniciando ===")
log.info("Python: %s", sys.version)
log.info("Executable: %s", sys.executable)
log.info("Script dir: %s", SCRIPT_DIR)

# ── Copy bundled assets on first run (PyInstaller onefile) ────────────
if _MEIPASS_DIR is not None:
    for _folder in ("icons", "style", "i18n"):
        _src = _MEIPASS_DIR / _folder
        _dst = SCRIPT_DIR / _folder
        if _src.is_dir() and not _dst.exists():
            shutil.copytree(_src, _dst)
            log.info("Assets extraidos: %s -> %s", _src, _dst)

# ── OS detection ────────────────────────────────────────────────────────

IS_WINDOWS = sys.platform == "win32"
IS_MACOS = sys.platform == "darwin"
IS_LINUX = sys.platform.startswith("linux")

# ── Icon Loader ────────────────────────────────────────────────────────

ICONS_DIR = SCRIPT_DIR / "icons"

ICON_FALLBACKS: Dict[str, str] = {
    "pickaxe": "⛏",
    "castle": "🏰",
    "folder": "📂",
    "refresh": "🔄",
    "palette": "🎨",
    "save": "💾",
    "undo": "↩",
    "block": "🧱",
    "settings": "⚙",
    "crafting": "🛠",
    "scroll": "📜",
    "file": "🏷",
    "add": "➕",
    "delete": "✕",
    "wrench": "🔨",
    "check": "✅",
    "error": "❌",
}
def _find_icon_file(name: str) -> Optional[Path]:
    """Procura arquivo de icone (case-insensitive, ignora espacos)."""
    name = name.strip().lower()
    if ICONS_DIR.is_dir():
        for entry in ICONS_DIR.iterdir():
            if entry.is_file() and entry.stem.strip().lower() == name:
                return entry
    return None


def load_icon(name: str) -> QIcon:
    """Carrega icone do arquivo icons/<name>.png, fallback para emoji."""
    found = _find_icon_file(name)
    if found:
        return QIcon(str(found))
    return QIcon()


def load_icon_pixmap(name: str, size: int = 30) -> QPixmap:
    """Carrega icone como QPixmap redimensionado, fallback vazio."""
    found = _find_icon_file(name)
    if found:
        pix = QPixmap(str(found))
        return pix.scaled(size, size, Qt.AspectRatioMode.KeepAspectRatio,
                          Qt.TransformationMode.SmoothTransformation)
    return QPixmap()

def icon_text(name: str) -> str:
    """Retorna texto com emoji (fallback) ou espaco reservado para icone."""
    if _find_icon_file(name):
        return "  "
    return f"{ICON_FALLBACKS.get(name, '')} "

def icon_button(btn: QPushButton, icon_name: str) -> None:
    """Aplica icone PNG a um QPushButton. Se nao existir, usa emoji no texto."""
    icon = load_icon(icon_name)
    if not icon.isNull():
        btn.setIcon(icon)
        btn.setIconSize(QSize(30, 30))
    else:
        current = btn.text()
        if not current.strip():
            btn.setText(ICON_FALLBACKS.get(icon_name, ""))

def labeled_icon(icon_name: str, text: str, parent=None) -> QWidget:
    """Retorna widget com icone PNG + texto lado a lado."""
    w = QWidget(parent)
    layout = QHBoxLayout(w)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(4)
    pix = load_icon_pixmap(icon_name, 30)
    if not pix.isNull():
        icon_lbl = QLabel()
        icon_lbl.setPixmap(pix)
        icon_lbl.setFixedSize(30, 30)
        layout.addWidget(icon_lbl)
    else:
        fallback = QLabel(ICON_FALLBACKS.get(icon_name, ""))
        fallback.setObjectName("iconFallback")
        layout.addWidget(fallback)
    text_lbl = QLabel(text)
    layout.addWidget(text_lbl)
    layout.addStretch()
    return w

def _settings_dir() -> Path:
    if IS_WINDOWS:
        base = os.environ.get("APPDATA", str(Path.home()))
        return Path(base) / "mc-config-editor"
    elif IS_MACOS:
        return Path.home() / "Library" / "Application Support" / "mc-config-editor"
    else:
        xdg = os.environ.get("XDG_CONFIG_HOME", str(Path.home() / ".config"))
        return Path(xdg) / "mc-config-editor"

SETTINGS_DIR = _settings_dir()
SETTINGS_DIR.mkdir(parents=True, exist_ok=True)
SETTINGS_FILE = SETTINGS_DIR / "settings.json"

def load_settings() -> dict:
    if SETTINGS_FILE.is_file():
        try:
            return json.loads(SETTINGS_FILE.read_text())
        except Exception:
            return {}
    return {}

def save_settings(data: dict) -> None:
    SETTINGS_DIR.mkdir(parents=True, exist_ok=True)
    SETTINGS_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False))

def get_last_instance() -> Optional[str]:
    return load_settings().get("last_instance")

def set_last_instance(path: str) -> None:
    data = load_settings()
    data["last_instance"] = str(path)
    save_settings(data)

def get_custom_css() -> Optional[str]:
    """Retorna o CSS customizado, se configurado e o arquivo existir."""
    data = load_settings()
    path = data.get("custom_css_path")
    if path and not Path(path).is_file():
        path = None  # caminho salvo nao existe mais
    if not path:
        candidate = STYLE_DIR / "custom.css"
        if candidate.is_file():
            path = str(candidate)
    if path:
        try:
            return Path(path).read_text(encoding="utf-8")
        except Exception:
            return None
    return None

def save_custom_css_path(path: str) -> None:
    data = load_settings()
    data["custom_css_path"] = str(path)
    save_settings(data)

# ── i18n ───────────────────────────────────────────────────────────────

def detect_language() -> str:
    """Detecta idioma: settings > locale SO > pt_BR."""
    settings = load_settings()
    if "language" in settings:
        return settings["language"]
    locale = QLocale.system().name()
    if locale.startswith("en"):
        return "en"
    if locale.startswith("es"):
        return "es"
    return "pt_BR"

def load_translator(app: QApplication, lang: str) -> Optional[QTranslator]:
    """Carrega .qm para o idioma. Retorna None se source ou arquivo faltar."""
    if lang == "pt_BR":
        return None  # lingua padrao, nao precisa de tradutor
    path = SCRIPT_DIR / "i18n" / f"{lang}.qm"
    if not path.is_file():
        log.warning("Translation file not found: %s", path)
        return None
    translator = QTranslator()
    if translator.load(str(path)):
        app.installTranslator(translator)
        log.info("Translator loaded: %s", lang)
        return translator
    log.warning("Failed to load translator: %s", path)
    return None

# ── CSS Loading ─────────────────────────────────────────────────────────

STYLE_DIR = SCRIPT_DIR / "style"
DEFAULT_CSS_PATH = STYLE_DIR / "default.css"

def _load_default_css() -> str:
    """Carrega CSS padrao do arquivo style/default.css."""
    if DEFAULT_CSS_PATH.is_file():
        try:
            return DEFAULT_CSS_PATH.read_text(encoding="utf-8")
        except Exception:
            pass
    return _FALLBACK_CSS

_FALLBACK_CSS = r"""
"""

DEFAULT_CSS = _load_default_css()

# ── Data Layer (reused from original) ──────────────────────────────────

KNOWN_SIDE_SUFFIXES = [
    "-client", "-common", "-server", "-forge", "-fabric", "-neoforge",
    "-pack_config",
]


def extract_mod_key(filename: str) -> str:
    stem = Path(filename).stem
    if stem.endswith((".bak", ".backup")):
        stem = Path(stem).stem
    lower = stem.lower()
    for suffix in KNOWN_SIDE_SUFFIXES:
        if lower.endswith(suffix):
            stem = stem[: -len(suffix)]
            break
    return stem


def mod_key_to_display(key: str) -> str:
    name = re.sub(r"[_-]", " ", key)
    return name.strip().title() or key


def format_timestamp() -> str:
    return datetime.datetime.now().strftime("%Y%m%d_%H%M%S")


_FILE_ICON_MAP: Dict[str, str] = {
    "toml": "settings",
    "json": "crafting",
    "json5": "crafting",
    "yaml": "scroll",
}


def _file_format_icon(fmt: str) -> QIcon:
    name = _FILE_ICON_MAP.get(fmt, "file")
    return load_icon(name)


class ConfigFile:
    def __init__(self, path: Path, fmt: str) -> None:
        self.path = path
        self.fmt = fmt
        self.parsed_data: Any = None
        self.parsed_ok = False
        self.parse_error: Optional[str] = None
        self.modified = False
        self._original_raw: Optional[str] = None
        self._modified_data: Any = None
        self._is_semicolon = False
        self._semicolon_root = ""

    @property
    def display_name(self) -> str:
        return self.path.name

    @property
    def is_structured(self) -> bool:
        return self.fmt in ("toml", "json", "json5", "yaml", "properties", "snbt", "ini", "cfg", "txt")

    def parse(self) -> None:
        if self.parsed_ok:
            return
        try:
            raw = self.path.read_text(encoding="utf-8", errors="replace")
            self._original_raw = raw
        except Exception as e:
            self.parsed_ok = False
            self.parse_error = "Read error: " + str(e)
            return
        parsers = {
            "toml": self._parse_toml,
            "json": self._parse_json,
            "json5": self._parse_json5,
            "yaml": self._parse_yaml,
            "properties": self._parse_properties,
            "snbt": self._parse_snbt,
            "ini": self._parse_ini,
            "cfg": self._parse_cfg,
            "txt": self._parse_text,
        }
        parser = parsers.get(self.fmt)
        if parser:
            parser(raw)
        else:
            self.parsed_data = raw
            self._modified_data = raw
            self.parsed_ok = True

    def _parse_toml(self, raw: str) -> None:
        try:
            import tomlkit
            from tomlkit.exceptions import TOMLKitError
            self.parsed_data = tomlkit.parse(raw)
            self._modified_data = self.parsed_data
            self.parsed_ok = True
        except (ImportError, TOMLKitError) as e:
            self.parsed_ok = False
            self.parse_error = "TOML error: " + str(e)

    def _parse_json(self, raw: str) -> None:
        try:
            self.parsed_data = json.loads(raw)
            self._modified_data = self.parsed_data
            self.parsed_ok = True
        except json.JSONDecodeError as e:
            self.parsed_ok = False
            self.parse_error = "JSON error: " + str(e)

    def _parse_json5(self, raw: str) -> None:
        try:
            import pyjson5
            self.parsed_data = pyjson5.loads(raw)
            self._modified_data = self.parsed_data
            self.parsed_ok = True
        except (ImportError, Exception) as e:
            self.parsed_ok = False
            self.parse_error = "JSON5 error: " + str(e)

    def _parse_yaml(self, raw: str) -> None:
        try:
            import yaml
            self.parsed_data = yaml.safe_load(raw)
            self._modified_data = self.parsed_data
            self.parsed_ok = True
        except (ImportError, Exception) as e:
            self.parsed_ok = False
            self.parse_error = "YAML error: " + str(e)

    def _parse_properties(self, raw: str) -> None:
        data: Dict[str, str] = {}
        try:
            for line in raw.splitlines():
                line = line.strip()
                if not line or line.startswith("#") or line.startswith("!"):
                    continue
                if "=" in line:
                    key, val = line.split("=", 1)
                elif ":" in line:
                    key, val = line.split(":", 1)
                else:
                    continue
                data[key.strip()] = val.strip()
            self.parsed_data = data
            self._modified_data = data
            self.parsed_ok = True
        except Exception as e:
            self.parsed_ok = False
            self.parse_error = "Properties error: " + str(e)

    def _parse_snbt(self, raw: str) -> None:
        import re as _re
        cleaned = raw
        # Strip Minecraft SNBT type suffixes: 1.0d, 40b, 2.5f, 100L, 3s
        cleaned = _re.sub(r'(\d+(?:\.\d+)?)\s*[bBsSlLfFdD](?=[\s,\]\n\r}])', r'\1', cleaned)
        try:
            import pyjson5
            self.parsed_data = pyjson5.loads(cleaned)
            self._modified_data = self.parsed_data
            self.parsed_ok = True
        except Exception:
            try:
                self.parsed_data = json.loads(cleaned)
                self._modified_data = self.parsed_data
                self.parsed_ok = True
            except Exception as e:
                self.parsed_ok = False
                self.parse_error = "SNBT error: " + str(e)

    def _parse_ini(self, raw: str) -> None:
        data: Dict[str, Dict[str, str]] = {}
        current_section = "__root__"
        data[current_section] = {}
        try:
            for line in raw.splitlines():
                stripped = line.strip()
                if not stripped or stripped.startswith("#") or stripped.startswith(";"):
                    continue
                if stripped.startswith("[") and stripped.endswith("]"):
                    current_section = stripped[1:-1].strip()
                    if current_section not in data:
                        data[current_section] = {}
                    continue
                if "=" in stripped:
                    key, val = stripped.split("=", 1)
                    data[current_section][key.strip()] = val.strip()
            self.parsed_data = data
            self._modified_data = data
            self.parsed_ok = True
        except Exception as e:
            self.parsed_ok = False
            self.parse_error = "INI error: " + str(e)

    def _parse_cfg(self, raw: str) -> None:
        data: Dict[str, str] = {}
        try:
            for line in raw.splitlines():
                stripped = line.strip()
                if not stripped or stripped.startswith("#") or stripped.startswith("//"):
                    continue
                if "=" not in stripped:
                    continue
                key, val = stripped.split("=", 1)
                key = key.strip()
                if key:
                    data[key] = val.strip()
            if data:
                self.parsed_data = data
                self._modified_data = data
                self.parsed_ok = True
            else:
                self.parsed_ok = False
                self.parse_error = "CFG format uses raw editor"
        except Exception as e:
            self.parsed_ok = False
            self.parse_error = "CFG error: " + str(e)

    def _parse_text(self, raw: str) -> None:
        data: Dict[str, str] = {}
        self._is_semicolon = False
        self._semicolon_root = ""
        try:
            for line in raw.splitlines():
                stripped = line.strip()
                if not stripped or stripped.startswith("#"):
                    continue
                if ";" in stripped and "=" in stripped:
                    self._is_semicolon = True
                    parts = [p.strip() for p in stripped.split(";") if p.strip()]
                    for i, part in enumerate(parts):
                        if "=" in part:
                            key, val = part.split("=", 1)
                            key = key.strip()
                            if key:
                                data[key] = val.strip()
                        elif i == 0:
                            self._semicolon_root = part
                    continue
                if "=" in stripped:
                    key, val = stripped.split("=", 1)
                elif ":" in stripped:
                    key, val = stripped.split(":", 1)
                else:
                    continue
                key = key.strip()
                if key:
                    data[key] = val.strip()
            if data:
                self.parsed_data = data
                self._modified_data = data
                self.parsed_ok = True
            else:
                self.parsed_ok = False
                self.parse_error = "No key=value or key:value pairs found"
        except Exception as e:
            self.parsed_ok = False
            self.parse_error = "TXT error: " + str(e)

    def get_value(self, key_path: List[str]) -> Any:
        if not self.parsed_ok or not self.is_structured:
            return None
        data = self._modified_data
        for k in key_path:
            if isinstance(data, dict):
                data = data.get(k)
            else:
                return None
        return data

    def set_value(self, key_path: List[str], value: Any) -> None:
        if not self.parsed_ok or not self.is_structured:
            return
        data = self._modified_data
        for i, k in enumerate(key_path[:-1]):
            if isinstance(data, dict) and k in data:
                data = data[k]
            else:
                return
        if isinstance(data, dict):
            data[key_path[-1]] = value
            self.modified = True

    def serialize(self) -> Optional[str]:
        if not self.parsed_ok:
            return None
        if not self.is_structured:
            return str(self._modified_data) if self._modified_data is not None else None
        serializers = {
            "toml": self._serialize_toml,
            "json": self._serialize_json,
            "json5": self._serialize_json5,
            "yaml": self._serialize_yaml,
            "properties": self._serialize_properties,
            "snbt": self._serialize_snbt,
            "ini": self._serialize_ini,
            "cfg": self._serialize_properties,
            "txt": self._serialize_txt,
        }
        serializer = serializers.get(self.fmt)
        return serializer() if serializer else None

    def _serialize_toml(self) -> Optional[str]:
        try:
            import tomlkit
            return tomlkit.dumps(self._modified_data)
        except Exception:
            return None

    def _serialize_json(self) -> str:
        return json.dumps(self._modified_data, indent=2, ensure_ascii=False) + "\n"

    def _serialize_json5(self) -> str:
        try:
            import pyjson5
            if hasattr(pyjson5, "dumps"):
                return pyjson5.dumps(self._modified_data, indent=2, ensure_ascii=False) + "\n"
        except Exception:
            pass
        return json.dumps(self._modified_data, indent=2, ensure_ascii=False) + "\n"

    def _serialize_yaml(self) -> str:
        import yaml
        return yaml.dump(self._modified_data, default_flow_style=False, allow_unicode=True)

    def _serialize_properties(self) -> str:
        lines = []
        for k, v in self._modified_data.items():
            if isinstance(v, bool):
                v = str(v).lower()
            lines.append(f"{k}={v}")
        return "\n".join(lines) + "\n"

    def _serialize_snbt(self) -> Optional[str]:
        try:
            import pyjson5
            return pyjson5.dumps(self._modified_data, indent=2, ensure_ascii=False)
        except Exception:
            try:
                return json.dumps(self._modified_data, indent=2, ensure_ascii=False)
            except Exception:
                return None

    def _serialize_ini(self) -> str:
        lines = []
        for section, items in self._modified_data.items():
            if section == "__root__":
                for k, v in items.items():
                    if isinstance(v, bool):
                        v = str(v).lower()
                    lines.append(f"{k} = {v}")
            else:
                lines.append(f"[{section}]")
                for k, v in items.items():
                    if isinstance(v, bool):
                        v = str(v).lower()
                    lines.append(f"{k} = {v}")
        return "\n".join(lines) + "\n"

    def _serialize_txt(self) -> str:
        if getattr(self, "_is_semicolon", False):
            root = getattr(self, "_semicolon_root", "")
            parts = [root] if root else []
            for k, v in self._modified_data.items():
                parts.append(f"{k}={v}")
            return ";".join(parts) + ";\n"
        lines = []
        for k, v in self._modified_data.items():
            lines.append(f"{k}={v}")
        return "\n".join(lines) + "\n"


    def backup(self) -> Optional[Path]:
        bak_path = self.path.with_name(f"{self.path.name}.bak.{format_timestamp()}")
        try:
            shutil.copy2(str(self.path), str(bak_path))
            return bak_path
        except OSError:
            return None

    def save(self) -> Tuple[bool, str]:
        if not self.parsed_ok:
            return False, "File not parsed."
        if not self.modified:
            return False, "No changes to save."
        bak = self.backup()
        content = self.serialize()
        if content is None:
            return False, "Serialization error."
        try:
            self.path.write_text(content, encoding="utf-8")
        except OSError as e:
            return False, "Write error: " + str(e)
        msg = "Saved."
        if bak:
            msg += " Backup: " + bak.name
        self.modified = False
        return True, msg

    def raw_content(self) -> str:
        if self._original_raw is not None:
            return self._original_raw
        return self.path.read_text(encoding="utf-8", errors="replace")

    def set_raw_content(self, text: str) -> None:
        self._modified_data = text
        self.modified = True


class ModGroup:
    def __init__(self, key: str) -> None:
        self.key = key
        self.display_name = mod_key_to_display(key)
        self.files: List[ConfigFile] = []

    def add_file(self, cf: ConfigFile) -> None:
        self.files.append(cf)


class ConfigScanner:
    FORMAT_MAP: Dict[str, str] = {
        ".toml": "toml", ".json": "json", ".json5": "json5",
        ".yaml": "yaml", ".yml": "yaml", ".cfg": "cfg",
        ".properties": "properties", ".txt": "txt",
        ".snbt": "snbt", ".ini": "ini",
    }

    def __init__(self, config_dir: Path) -> None:
        self.config_dir = config_dir.resolve()
        self.groups: Dict[str, ModGroup] = {}
        self._scanned = False

    def scan(self) -> List[ModGroup]:
        if self._scanned:
            return list(self.groups.values())
        self._scanned = True
        log.info("Scanner: iniciando scan em %s", self.config_dir)
        root_files = 0
        for entry in sorted(self.config_dir.iterdir()):
            if entry.is_file():
                self._process_file(entry)
                root_files += 1
        log.info("Scanner: %d arquivos na raiz", root_files)
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
        return sorted(self.groups.values(), key=lambda g: g.display_name.lower())

    def _scan_dir_recursive(self, directory: Path, mod_key: str) -> None:
        for entry in sorted(directory.iterdir()):
            if entry.name.startswith("."):
                continue
            if entry.is_file():
                self._process_file(entry, parent_mod=mod_key)
            elif entry.is_dir():
                self._scan_dir_recursive(entry, mod_key)

    def _process_file(self, path: Path, parent_mod: Optional[str] = None) -> None:
        if path.name.startswith("."):
            return
        if path.suffix == ".bak" or ".bak." in path.name or path.suffix in (".backup",):
            return
        if path.suffix not in self.FORMAT_MAP:
            return
        fmt = self.FORMAT_MAP[path.suffix]
        mod_key = parent_mod or extract_mod_key(path.name)
        if mod_key not in self.groups:
            self.groups[mod_key] = ModGroup(mod_key)
        self.groups[mod_key].add_file(ConfigFile(path, fmt))


# ── PyQt6 GUI ──────────────────────────────────────────────────────────


class ModTreeWidget(QTreeWidget):
    """QTreeWidget com suporte a drag-and-drop e menu de contexto (copiar/colar/excluir)."""

    drop_requested = pyqtSignal(object, object)
    delete_requested = pyqtSignal(object)
    copy_requested = pyqtSignal(object)
    paste_requested = pyqtSignal(object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setDropIndicatorShown(True)
        self.setDragDropMode(QAbstractItemView.DragDropMode.DragDrop)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)
        self._drag_source_item = None
        self.clipboard_file = None  # ConfigFile or None, set by MainWindow

    def startDrag(self, supportedActions):
        item = self.currentItem()
        if item is not None:
            self._drag_source_item = item
        super().startDrag(supportedActions)

    def dropEvent(self, event):
        if self._drag_source_item is None:
            event.ignore()
            return
        src_item = self._drag_source_item
        self._drag_source_item = None

        src_cf = src_item.data(0, Qt.ItemDataRole.UserRole)
        if not isinstance(src_cf, ConfigFile):
            event.ignore()
            return

        target_item = self.itemAt(event.position().toPoint())
        if target_item is None:
            event.ignore()
            return

        tgt_data = target_item.data(0, Qt.ItemDataRole.UserRole)
        if tgt_data is None:
            target_mod_item = target_item
        elif isinstance(tgt_data, ConfigFile):
            target_mod_item = target_item.parent()
            if target_mod_item is None:
                event.ignore()
                return
        else:
            target_mod_item = target_item

        src_mod_item = src_item.parent()
        if src_mod_item is target_mod_item:
            event.ignore()
            return

        self.drop_requested.emit(src_cf, target_mod_item)
        event.accept()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Delete:
            item = self.currentItem()
            if item is not None:
                data = item.data(0, Qt.ItemDataRole.UserRole)
                if isinstance(data, ConfigFile) or isinstance(data, ModGroup):
                    self.delete_requested.emit(item)
                return
        super().keyPressEvent(event)

    def _show_context_menu(self, pos):
        item = self.itemAt(pos)
        if item is None:
            return
        data = item.data(0, Qt.ItemDataRole.UserRole)
        menu = QMenu(self)

        if isinstance(data, ConfigFile):
            act_copy = menu.addAction(self.tr("Copiar"))
            act_copy.triggered.connect(lambda: self.copy_requested.emit(item))
            menu.addSeparator()
            act_delete = menu.addAction(self.tr("Excluir"))
            act_delete.triggered.connect(lambda: self.delete_requested.emit(item))
        elif isinstance(data, ModGroup):
            act_paste = menu.addAction(self.tr("Colar"))
            act_paste.setEnabled(self.clipboard_file is not None)
            act_paste.triggered.connect(lambda: self.paste_requested.emit(item))
            menu.addSeparator()
            act_delete = menu.addAction(self.tr("Excluir pasta"))
            act_delete.triggered.connect(lambda: self.delete_requested.emit(item))

        menu.exec(self.viewport().mapToGlobal(pos))


class ToggleSwitch(QWidget):
    """Toggle switch customizado (substitui QCheckBox para booleanos)."""
    toggled = None  # type: ignore

    def __init__(self, checked=False, parent=None):
        super().__init__(parent)
        self._checked = checked
        self.setFixedSize(44, 24)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setObjectName("toggleSwitch")
        self._track = QWidget(self)
        self._track.setObjectName("toggleTrack")
        self._track.setGeometry(0, 4, 44, 16)
        self._knob = QWidget(self)
        self._knob.setObjectName("toggleKnob")
        self._update_knob()

    def _update_knob(self):
        x = 22 if self._checked else 2
        self._knob.setGeometry(x, 0, 20, 24)
        self._track.setProperty("checked", self._checked)
        self._track.style().unpolish(self._track)
        self._track.style().polish(self._track)
        self._knob.setProperty("checked", self._checked)
        self._knob.style().unpolish(self._knob)
        self._knob.style().polish(self._knob)

    def isChecked(self):
        return self._checked

    def setChecked(self, checked):
        self._checked = checked
        self._update_knob()

    def mouseReleaseEvent(self, event):
        self._checked = not self._checked
        self._update_knob()
        if hasattr(self, "_callback"):
            self._callback()

    def set_callback(self, fn):
        self._callback = fn


class ParameterWidget(QFrame):
    """Widget que representa um parametro unico no editor."""

    def __init__(self, key: str, value: Any, key_path: List[str],
                 on_change: callable, on_delete: Optional[callable] = None,
                 parent=None):
        super().__init__(parent)
        self.key = key
        self.key_path = key_path
        self._on_change = on_change
        self._on_delete = on_delete
        self._old_value = value

        self.setObjectName("paramCard")
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        header = QHBoxLayout()
        header.setSpacing(8)

        name_lbl = QLabel(key)
        name_lbl.setObjectName("paramName")
        header.addWidget(name_lbl)

        type_hint = ""
        if isinstance(value, bool):
            type_hint = self.tr("bool")
        elif isinstance(value, int):
            type_hint = self.tr("int")
        elif isinstance(value, float):
            type_hint = self.tr("float")
        elif isinstance(value, str):
            type_hint = self.tr("text")
        elif isinstance(value, list):
            type_hint = self.tr("list (%n item(s))", "", len(value))

        if type_hint:
            type_lbl = QLabel(self.tr("[%1]").replace("%1", str(type_hint)))
            type_lbl.setObjectName("paramType")
            header.addWidget(type_lbl)

        header.addStretch()

        if self._on_delete is not None:
            self._btn_del = QPushButton("✕")
            self._btn_del.setObjectName("btnDeleteParam")
            icon_button(self._btn_del, "delete")
            self._btn_del.setFixedSize(24, 24)
            self._btn_del.setToolTip(self.tr("Remover '%1'").replace("%1", str(self.key)))
            self._btn_del.clicked.connect(lambda: self._on_delete(self.key_path))
            header.addWidget(self._btn_del)

        layout.addLayout(header)

        input_row = QHBoxLayout()
        input_row.setSpacing(8)

        if isinstance(value, bool):
            self._widget = ToggleSwitch(checked=bool(value))
            self._widget.set_callback(self._emit_change)
            input_row.addWidget(self._widget)
            input_row.addStretch()
        elif isinstance(value, int):
            self._widget = self._make_spin_box(int(value), is_float=False)
            input_row.addWidget(self._widget)
            input_row.addStretch()
        elif isinstance(value, float):
            self._widget = self._make_spin_box(float(value), is_float=True)
            input_row.addWidget(self._widget)
            input_row.addStretch()
        elif isinstance(value, str):
            if len(value) > 60:
                self._widget = QTextEdit()
                self._widget.setPlainText(str(value))
                self._widget.setObjectName("paramTextArea")
                self._widget.setFixedHeight(80)
                self._widget.setStyleSheet("color: #e0ddd8;")
                self._widget.textChanged.connect(lambda: self._emit_change())
            else:
                self._widget = QLineEdit(str(value))
                self._widget.setObjectName("paramInput")
                self._widget.setMinimumHeight(40)
                self._widget.setStyleSheet("color: #e0ddd8;")
                self._widget.textChanged.connect(lambda txt: self._emit_change())
            input_row.addWidget(self._widget)
        elif isinstance(value, list):
            self._widget = QTextEdit()
            self._widget.setPlainText("\n".join(str(v) for v in value))
            self._widget.setObjectName("paramTextArea")
            self._widget.setFixedHeight(80)
            self._widget.setStyleSheet("color: #e0ddd8;")
            self._widget.textChanged.connect(lambda: self._emit_change())
            input_row.addWidget(self._widget)
        else:
            self._widget = QLineEdit(str(value) if value is not None else "")
            self._widget.setObjectName("paramInput")
            self._widget.setMinimumHeight(32)
            self._widget.setStyleSheet("color: #e0ddd8;")
            self._widget.textChanged.connect(lambda txt: self._emit_change())
            input_row.addWidget(self._widget)

        layout.addLayout(input_row)

    def _make_spin_box(self, value, is_float=False):
        """Cria widget numerico com botoes +/- visiveis."""
        w = QWidget()
        layout = QHBoxLayout(w)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)

        entry = QLineEdit(str(value))
        entry.setObjectName("spinValue")
        entry.setStyleSheet("color: #e0ddd8;")
        entry.setMinimumHeight(40)
        entry.setMaximumHeight(40)
        entry.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        entry.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        entry.setMinimumHeight(28)
        entry.setMaximumHeight(28)
        layout.addWidget(entry, 1)

        delta = 0.01 if is_float else 1

        def _adjust(d):
            try:
                cur = float(entry.text()) if is_float else int(entry.text())
            except ValueError:
                cur = 0
            new = cur + d
            entry.setText(str(int(new) if not is_float else round(new, 4)))
            self._emit_change()

        for label, d in [("−", -delta), ("+", delta)]:
            btn = QPushButton(label)
            btn.setObjectName("spinBtn")
            btn.setFixedSize(26, 26)
            btn.clicked.connect(lambda checked, step=d: _adjust(step))
            layout.addWidget(btn)

        entry.textChanged.connect(lambda: self._emit_change())
        w.value = lambda: (float(entry.text()) if is_float else int(entry.text()))
        w.setValue = lambda v: entry.setText(str(v))
        w._is_spin_widget = True
        return w

    def _emit_change(self) -> None:
        if isinstance(self._widget, ToggleSwitch):
            new_val = self._widget.isChecked()
        elif hasattr(self._widget, "_is_spin_widget"):
            new_val = self._widget.value()
        elif isinstance(self._widget, QTextEdit):
            new_val = self._widget.toPlainText()
        elif isinstance(self._widget, QLineEdit):
            new_val = self._widget.text()
        else:
            return
        self._on_change(self.key_path, new_val, isinstance(self._old_value, list))


class EditorPanel(QWidget):
    """Painel central que mostra e edita os parametros de um arquivo."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_file: Optional[ConfigFile] = None
        self._param_widgets: List[ParameterWidget] = []
        self._modified = False
        self.on_modified: Optional[callable] = None

        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)

        self._tabs = QTabWidget()
        self._tabs.setObjectName("editorTabs")
        self._layout.addWidget(self._tabs)

        self._visual_tab = QWidget()
        visual_layout = QVBoxLayout(self._visual_tab)
        visual_layout.setContentsMargins(0, 0, 0, 0)
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll_widget = QWidget()
        self._scroll_layout = QVBoxLayout(self._scroll_widget)
        self._scroll_layout.setContentsMargins(12, 12, 12, 12)
        self._scroll_layout.setSpacing(10)
        self._scroll_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self._scroll.setWidget(self._scroll_widget)
        visual_layout.addWidget(self._scroll)
        self._tabs.addTab(self._visual_tab, self.tr("\U0001f4cb Visual"))

        self._raw_tab = QWidget()
        raw_layout = QVBoxLayout(self._raw_tab)
        raw_layout.setContentsMargins(0, 0, 0, 0)
        self._raw_editor = QTextEdit()
        self._raw_editor.setObjectName("rawEditor")
        self._raw_editor.textChanged.connect(self._on_raw_changed)
        raw_layout.addWidget(self._raw_editor)
        self._tabs.addTab(self._raw_tab, self.tr("\U0001f4c4 Raw"))

        # Placeholder
        self._placeholder = QLabel(icon_text("wrench") + self.tr("Selecione um arquivo de configuracao na arvore ao lado"))
        self._placeholder.setObjectName("editorPlaceholder")
        self._placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._layout.addWidget(self._placeholder)

    def load_file(self, cf: ConfigFile) -> None:
        self.current_file = cf
        self._modified = False
        self._clear_widgets()

        if not cf.parsed_ok:
            cf.parse()

        if cf.parse_error and cf.fmt in ("snbt", "cfg", "txt"):
            self._placeholder.setVisible(False)
            self._tabs.setVisible(True)
            self._raw_editor.blockSignals(True)
            self._raw_editor.setPlainText(cf.raw_content())
            self._raw_editor.blockSignals(False)
            self._show_raw_in_visual(cf.raw_content())
            self._tabs.setCurrentIndex(0)
            return

        if cf.parse_error:
            self._show_error(cf)
            return

        self._placeholder.setVisible(False)
        self._tabs.setVisible(True)

        if cf.is_structured:
            self._raw_editor.blockSignals(True)
            self._raw_editor.setPlainText(cf.raw_content())
            self._raw_editor.blockSignals(False)
            self._tabs.setCurrentIndex(0)
            self._build_structured(cf)
        else:
            self._raw_editor.setPlainText(cf.raw_content())
            self._tabs.setCurrentIndex(1)

    def _show_raw_in_visual(self, content: str) -> None:
        editor = QTextEdit()
        editor.setObjectName("rawVisualEditor")
        editor.setPlainText(content)
        editor.setStyleSheet("color: #e0ddd8; background-color: #1e1c1a;")
        editor.setMinimumHeight(200)
        editor.textChanged.connect(lambda: self._on_raw_visual_changed(editor))
        self._scroll_layout.addWidget(editor)

    def _on_raw_visual_changed(self, editor: QTextEdit) -> None:
        if self.current_file and self.current_file.fmt in ("snbt", "cfg", "txt"):
            self.current_file.set_raw_content(editor.toPlainText())
            self._modified = True
            if self.on_modified:
                self.on_modified()

    def _clear_widgets(self) -> None:
        for pw in self._param_widgets:
            pw.deleteLater()
        self._param_widgets.clear()
        # Clear scroll content
        while self._scroll_layout.count():
            item = self._scroll_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def _show_error(self, cf: ConfigFile) -> None:
        self._tabs.setVisible(False)
        self._placeholder.setText(icon_text("error") + self.tr(" Erro: %1").replace("%1", str(cf.parse_error)))
        self._placeholder.setObjectName("editorError")
        self._placeholder.setVisible(True)

    def _build_structured(self, cf: ConfigFile) -> None:
        data = cf._modified_data
        if isinstance(data, dict):
            self._render_dict(cf, data, [])
        elif isinstance(data, list):
            pw = ParameterWidget(self.tr("(root)"), data, ["_root"], self._on_param_change, None, self)
            self._scroll_layout.addWidget(pw)
            self._param_widgets.append(pw)
        else:
            pw = ParameterWidget(self.tr("(value)"), data, ["_root"], self._on_param_change, None, self)
            self._scroll_layout.addWidget(pw)
            self._param_widgets.append(pw)

        # ADD button for dict-based configs
        if isinstance(data, dict):
            self._add_btn_row = QWidget()
            add_layout = QHBoxLayout(self._add_btn_row)
            add_layout.setContentsMargins(12, 8, 12, 8)
            add_layout.addStretch()
            btn_add = QPushButton(self.tr(" Adicionar Parametro"))
            btn_add.setObjectName("btnAddParam")
            btn_add.setFixedWidth(200)
            icon_button(btn_add, "add")
            btn_add.clicked.connect(lambda: self._add_param(data))
            add_layout.addWidget(btn_add)
            self._scroll_layout.addWidget(self._add_btn_row)

    def _render_dict(self, cf: ConfigFile, d: dict, prefix: List[str]) -> None:
        for key, value in d.items():
            key_path = prefix + [key]
            if isinstance(value, dict):
                self._add_collapsible_section(key, cf, value, key_path)
            elif isinstance(value, list):
                pw = ParameterWidget(key, value, key_path, self._on_param_change,
                                     self._delete_param, self)
                self._scroll_layout.addWidget(pw)
                self._param_widgets.append(pw)
            else:
                pw = ParameterWidget(key, value, key_path, self._on_param_change,
                                     self._delete_param, self)
                self._scroll_layout.addWidget(pw)
                self._param_widgets.append(pw)

    def _add_collapsible_section(self, name: str, cf, nested_dict: dict,
                                  key_path: List[str]) -> None:
        container = QWidget()
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(2)

        hint_expand = self.tr(" [Clique para expandir]")
        hint_collapse = self.tr(" [Clique para recolher]")
        btn = QPushButton(self.tr("  \u25b6 %1%2").replace("%1", str(name)).replace("%2", str(hint_expand)))
        btn.setObjectName("sectionToggle")
        btn.setProperty("mc_name", name)
        btn.setProperty("mc_hint_expand", hint_expand)
        btn.setProperty("mc_hint_collapse", hint_collapse)
        container_layout.addWidget(btn)

        content = QWidget()
        content.setVisible(False)  # default collapsed
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(20, 2, 0, 2)
        content_layout.setSpacing(2)

        old_layout = self._scroll_layout
        self._scroll_layout = content_layout
        self._render_dict(cf, nested_dict, key_path)
        self._scroll_layout = old_layout

        btn.clicked.connect(lambda: self._toggle_section(btn, content))
        container_layout.addWidget(content)
        self._scroll_layout.addWidget(container)

    def _toggle_section(self, btn: QPushButton, content: QWidget) -> None:
        visible = content.isVisible()
        content.setVisible(not visible)
        name = btn.property("mc_name")
        if visible:
            hint = btn.property("mc_hint_expand")
            btn.setText(self.tr("  \u25b6 %1%2").replace("%1", str(name)).replace("%2", str(hint)))
        else:
            hint = btn.property("mc_hint_collapse")
            btn.setText(self.tr("  \u25bc %1%2").replace("%1", str(name)).replace("%2", str(hint)))

    def _delete_param(self, key_path: List[str]) -> None:
        if not self.current_file or not self.current_file.is_structured:
            return
        if len(key_path) == 0:
            return
        data = self.current_file._modified_data
        for k in key_path[:-1]:
            if isinstance(data, dict) and k in data:
                data = data[k]
            else:
                return
        key_to_remove = key_path[-1]
        if isinstance(data, dict) and key_to_remove in data:
            del data[key_to_remove]
            self.current_file.modified = True
            self._modified = True
            self.load_file(self.current_file)
            if self.on_modified:
                self.on_modified()

    def _add_param(self, data: dict) -> None:
        if not self.current_file:
            return
        from PyQt6.QtWidgets import QDialog, QFormLayout, QDialogButtonBox, QComboBox

        dlg = QDialog(self)
        dlg.setObjectName("addParamDialog")
        dlg.setWindowTitle(self.tr("Adicionar Parametro"))
        dlg.setMinimumWidth(360)
        form = QFormLayout(dlg)

        name_edit = QLineEdit()
        name_edit.setPlaceholderText(self.tr("nome_do_parametro"))
        form.addRow(self.tr("Nome:"), name_edit)

        type_combo = QComboBox()
        type_combo.addItems([self.tr("texto"), self.tr("numero inteiro"), self.tr("numero decimal"), self.tr("booleano (true/false)")])
        form.addRow(self.tr("Tipo:"), type_combo)

        value_edit = QLineEdit()
        value_edit.setPlaceholderText(self.tr("valor"))
        form.addRow(self.tr("Valor:"), value_edit)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok |
                                    QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(dlg.accept)
        buttons.rejected.connect(dlg.reject)
        form.addRow(buttons)

        if dlg.exec() != QDialog.DialogCode.Accepted:
            return

        key = name_edit.text().strip()
        if not key:
            return

        val_str = value_edit.text().strip()
        val_type = type_combo.currentIndex()
        if val_type == 0:
            value = val_str
        elif val_type == 1:
            try:
                value = int(val_str) if val_str else 0
            except ValueError:
                QMessageBox.warning(self, self.tr("Erro"), self.tr("Valor invalido para inteiro: %1").replace("%1", str(val_str)))
                return
        elif val_type == 2:
            try:
                value = float(val_str) if val_str else 0.0
            except ValueError:
                QMessageBox.warning(self, self.tr("Erro"), self.tr("Valor invalido para decimal: %1").replace("%1", str(val_str)))
                return
        elif val_type == 3:
            low = val_str.lower()
            value = low in ("true", "1", "yes", "sim", "s")
        else:
            value = val_str

        data[key] = value
        self.current_file.modified = True
        self._modified = True
        self.load_file(self.current_file)
        if self.on_modified:
            self.on_modified()

    def _on_param_change(self, key_path: List[str], new_value: Any,
                         was_list: bool = False) -> None:
        if not self.current_file or not self.current_file.is_structured:
            return
        if was_list and isinstance(new_value, str):
            items = [line.strip() for line in new_value.split("\n") if line.strip()]
            typed = []
            for item in items:
                try:
                    typed.append(int(item))
                except ValueError:
                    try:
                        typed.append(float(item))
                    except ValueError:
                        typed.append(item)
            self.current_file.set_value(key_path, typed)
        else:
            self.current_file.set_value(key_path, new_value)
        self._modified = True
        if self.on_modified:
            self.on_modified()

    def _on_raw_changed(self) -> None:
        if self.current_file and not self.current_file.is_structured:
            self.current_file.set_raw_content(self._raw_editor.toPlainText())
            self._modified = True
            if self.on_modified:
                self.on_modified()

    def is_modified(self) -> bool:
        return self._modified

    def reload(self) -> None:
        if self.current_file:
            self.current_file.parsed_ok = False
            self.current_file._modified_data = None
            self.current_file.modified = False
            self.current_file.parse()
            self.load_file(self.current_file)
            self._modified = False


class TutorialDialog(QDialog):
    """Dialogo de tutorial com navegacao por paginas."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(self.tr("Tutorial — Minecraft Mod Config Editor"))
        self.setMinimumSize(580, 420)
        self.resize(600, 440)

        layout = QVBoxLayout(self)

        self.stack = QStackedWidget()
        self._pages = self._build_pages()
        for page in self._pages:
            self.stack.addWidget(page)
        layout.addWidget(self.stack)

        nav_layout = QHBoxLayout()
        nav_layout.setContentsMargins(0, 8, 0, 0)

        self.btn_prev = QPushButton(self.tr("← Anterior"))
        self.btn_prev.clicked.connect(self._prev_page)

        self.page_label = QLabel()
        self.page_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.page_label.setStyleSheet("font-weight: bold; font-size: 13px;")

        self.btn_next = QPushButton(self.tr("Proximo →"))
        self.btn_next.clicked.connect(self._next_page)

        self.btn_close = QPushButton(self.tr("Fechar"))
        self.btn_close.clicked.connect(self.close)

        nav_layout.addWidget(self.btn_prev)
        nav_layout.addWidget(self.page_label)
        nav_layout.addWidget(self.btn_next)
        nav_layout.addWidget(self.btn_close)
        layout.addLayout(nav_layout)

        self._update_nav()

    def _build_pages(self):
        pages = []
        titles = [
            self.tr("Bem-vindo ao MC Mod Config Editor"),
            self.tr("Abrindo uma Instância"),
            self.tr("Árvore de Mods"),
            self.tr("Editor Visual"),
            self.tr("Editor Raw"),
            self.tr("Salvar, Desfazer e Backup"),
            self.tr("Exportar e Importar"),
            self.tr("Arrastar e Soltar (Drag & Drop)"),
            self.tr("Copiar, Colar e Excluir"),
            self.tr("Personalização CSS"),
            self.tr("Idiomas e Atualizações"),
        ]
        bodies = [
            self.tr("Este editor permite modificar arquivos de configuração "
                     "dos mods do Minecraft de forma visual e intuitiva.\n\n"
                     "Funciona com qualquer instância Minecraft:\n"
                     "vanilla, Forge, Fabric, Neoforge, Quilt,\n"
                     "PrismLauncher, ElyPrismLauncher e outros launchers.\n\n"
                     "Multiplataforma: Windows, Linux e macOS.\n\n"
                     "Formatos suportados: TOML, JSON, JSON5, YAML, CFG, Properties, SNBT, INI.\n\n"
                     "Desenvolvido por Makalove — github.com/Adiog0/mc-mod-config"),

            self.tr("Use o menu Arquivo → Abrir Instância para selecionar a\n"
                     "pasta de qualquer instância Minecraft.\n\n"
                     "O app detecta automaticamente o diretório de configs\n"
                     "(minecraft/config ou config/).\n\n"
                     "A última instância usada é salva e reaberta automaticamente\n"
                     "na próxima execução do app."),

            self.tr("O painel esquerdo mostra a árvore de mods encontrados.\n\n"
                     "Cada mod (ícone de bloco) agrupa seus arquivos de config.\n"
                     "O número ao lado indica quantos arquivos o mod possui.\n\n"
                     "Use o campo de busca no topo para filtrar mods ou\n"
                     "arquivos por nome parcial (ex: \"opt\" encontra \"OptiFine\").\n\n"
                     "Clique em um arquivo para abri-lo no editor."),

            self.tr("O editor Visual exibe cada parâmetro como um card individual.\n\n"
                     "Tipos de campo:\n"
                     "• Toggle Switch — para valores booleanos (ligado/desligado)\n"
                     "• Campo de texto — para strings e números\n"
                     "• Botões +/− — para ajuste fino de valores numéricos\n\n"
                     "Seções recolhíveis mostram ▶/▼ e podem ser expandidas\n"
                     "clicando no cabeçalho.\n\n"
                     "Você pode adicionar ou remover parâmetros via os botões\n"
                     "+ Adicionar e − Remover."),

            self.tr("A aba Raw permite editar o arquivo diretamente em texto,\n"
                     "mantendo a formatação original (TOML, JSON, YAML, etc).\n\n"
                     "Útil para ajustes rápidos ou quando o formato não é\n"
                     "totalmente suportado pelo editor visual.\n\n"
                     "Alterações no Raw também acionam os botões Salvar/Desfazer."),

            self.tr("Barra inferior de ações:\n\n"
                     "• Salvar — Salva as alterações no arquivo (backup automático)\n"
                     "• Desfazer — Descarta alterações e recarrega o arquivo original\n"
                     "• Backup — Cria uma cópia de segurança com timestamp\n\n"
                     "Sempre que você salva, um backup é criado automaticamente\n"
                     "com a extensão .bak."),

            self.tr("• Exportar — Salva o arquivo selecionado em uma pasta\n"
                     "  de sua escolha (diálogo \"Salvar como\")\n\n"
                     "• Importar — Abre um ou mais arquivos de config e os\n"
                     "  copia para config/imports/ dentro da instância.\n"
                     "  Use o campo de busca para encontrá-los.\n\n"
                     "• Exportar ZIP — Cria um arquivo .zip com TODAS as\n"
                     "  configurações da instância, salvo na pasta exports/\n"
                     "  ao lado do executável. O popup permite abrir a pasta."),

            self.tr("Arraste um arquivo de config de um mod para outro\n"
                     "diretamente na árvore de mods.\n\n"
                     "Ao soltar, você pode escolher entre:\n"
                     "• Copiar — mantém o original e duplica no destino\n"
                     "• Mover — transfere o arquivo para o novo mod\n\n"
                     "Se o destino já tiver um arquivo com o mesmo nome:\n"
                     "• Substituir — sobrescreve o existente\n"
                     "• Renomear — adiciona (1), (2), etc. ao nome\n"
                     "• Cancelar — cancela a operação"),

            self.tr("Menu de contexto (botão direito) e atalhos de teclado:\n\n"
                     "Clique com o botão direito em um arquivo:\n"
                     "• Copiar — guarda o arquivo na área de transferência\n"
                     "• Excluir — remove o arquivo permanentemente\n\n"
                     "Clique com o botão direito em um mod (pasta):\n"
                     "• Colar — cola o arquivo copiado da área de transferência\n"
                     "• Excluir pasta — remove a pasta e todos os seus arquivos\n\n"
                     "Tecla Delete — atalho rápido para excluir o item selecionado.\n\n"
                     "A exclusão sempre pede confirmação com Sim/Não/Cancelar\n"
                     "e avisa que a ação não pode ser desfeita."),

            self.tr("Menu Visual → Carregar CSS Customizado:\n"
                     "Carregue um arquivo .css para personalizar totalmente\n"
                     "a aparência do app (cores, fontes, bordas, etc).\n\n"
                     "Menu Visual → Resetar CSS Padrão:\n"
                     "Restaura o tema original pastel Minecraft.\n\n"
                     "Arquivos de tema inclusos:\n"
                     "default.css, dracula.css, neon.css, high_contrast.css,\n"
                     "mine.css, example.css (template comentado).\n\n"
                     "Crie seu próprio style/custom.css — ele será\n"
                     "carregado automaticamente ao iniciar."),

            self.tr("Menu Idioma:\n"
                     "Escolha entre Português (Brasil), English e Espanhol.\n\n"
                     "Menu Ajuda:\n"
                     "• Sobre — Informações do app e créditos\n"
                     "• Tutorial — Este guia interativo\n\n"
                     "Rodapé:\n"
                     "O canto inferior direito mostra a versão atual do app.\n\n"
                     "Verificação de atualização:\n"
                     "Ao abrir uma instância, o app verifica se há\n"
                     "uma nova versão disponível no GitHub."),
        ]
        for i, (title, body) in enumerate(zip(titles, bodies)):
            page = QWidget()
            page_layout = QVBoxLayout(page)
            page_layout.setContentsMargins(16, 16, 16, 8)
            title_lbl = QLabel(title)
            title_lbl.setStyleSheet("font-size: 16px; font-weight: bold; color: #7a9a6a; padding-bottom: 8px;")
            title_lbl.setWordWrap(True)
            page_layout.addWidget(title_lbl)
            body_lbl = QLabel(body)
            body_lbl.setWordWrap(True)
            body_lbl.setStyleSheet("font-size: 13px; line-height: 1.4;")
            page_layout.addWidget(body_lbl)
            page_layout.addStretch()
            pages.append(page)
        return pages

    def _prev_page(self):
        idx = self.stack.currentIndex()
        if idx > 0:
            self.stack.setCurrentIndex(idx - 1)
        self._update_nav()

    def _next_page(self):
        idx = self.stack.currentIndex()
        if idx < self.stack.count() - 1:
            self.stack.setCurrentIndex(idx + 1)
        self._update_nav()

    def _update_nav(self):
        idx = self.stack.currentIndex()
        total = self.stack.count()
        self.page_label.setText(f"{idx + 1}/{total}")
        self.btn_prev.setEnabled(idx > 0)
        self.btn_next.setEnabled(idx < total - 1)


class MainWindow(QMainWindow):
    """Janela principal do editor."""

    def __init__(self, config_dir: Optional[str] = None):
        super().__init__()
        self.setWindowTitle(self.tr("Minecraft Mod Config Editor \u2014 by Makalove"))
        self.setMinimumSize(1000, 650)
        self.resize(1300, 800)
        app_icon = load_icon("pickaxe")
        if not app_icon.isNull():
            self.setWindowIcon(app_icon)

        # Restore geometry
        settings = load_settings()
        if "geometry" in settings:
            try:
                self.restoreGeometry(bytes.fromhex(settings["geometry"]))
            except Exception:
                pass

        self._groups: List[ModGroup] = []
        self._current_file: Optional[ConfigFile] = None
        self._instance_path: Optional[str] = None
        self._instance_name: Optional[str] = None
        self._clipboard_cf: Optional[ConfigFile] = None
        self._translator: Optional[QTranslator] = None

        self._build_menubar()
        self._build_ui()
        self._build_statusbar()

        if config_dir:
            log.info("Carregando via --instance: %s", config_dir)
            self._load_configs(config_dir, save=True)
        else:
            last = get_last_instance()
            log.info("Verificando ultima instancia: %s", last)
            if last and Path(last).is_dir():
                log.info("Auto-carregando ultima instancia: %s", last)
                self._load_configs(last, save=False)
            else:
                log.info("Nenhuma instancia salva ou caminho invalido")
                QTimer.singleShot(300, self._open_instance)

        QTimer.singleShot(3000, self._check_for_updates)

    def _build_menubar(self) -> None:
        menu = self.menuBar()

        file_menu = menu.addMenu(self.tr("&Arquivo"))
        act_open = QAction(self.tr("Abrir Instancia..."), self)
        act_open.setShortcut("Ctrl+O")
        act_open.setIcon(load_icon("folder"))
        act_open.triggered.connect(self._open_instance)
        file_menu.addAction(act_open)

        act_reload = QAction(self.tr("Recarregar"), self)
        act_reload.setShortcut("Ctrl+R")
        act_reload.setIcon(load_icon("refresh"))
        act_reload.triggered.connect(self._reload_all)
        file_menu.addAction(act_reload)

        file_menu.addSeparator()
        act_exit = QAction(self.tr("Sair"), self)
        act_exit.setShortcut("Ctrl+Q")
        act_exit.triggered.connect(self.close)
        file_menu.addAction(act_exit)

        view_menu = menu.addMenu(self.tr("&Visual"))
        act_css = QAction(self.tr("Carregar CSS Customizado..."), self)
        act_css.setIcon(load_icon("palette"))
        act_css.triggered.connect(self._load_custom_css)
        view_menu.addAction(act_css)

        act_reset_css = QAction(self.tr("Resetar CSS Padrao"), self)
        act_reset_css.setIcon(load_icon("refresh"))
        act_reset_css.triggered.connect(self._reset_css)
        view_menu.addAction(act_reset_css)

        # Language menu
        lang_menu = menu.addMenu(self.tr("&Idioma"))
        current_lang = detect_language()

        act_pt = QAction(self.tr("Portugues"), self)
        act_pt.setCheckable(True)
        act_pt.setChecked(current_lang == "pt_BR")
        act_pt.triggered.connect(lambda: self._set_language("pt_BR"))
        lang_menu.addAction(act_pt)

        act_en = QAction(self.tr("English"), self)
        act_en.setCheckable(True)
        act_en.setChecked(current_lang == "en")
        act_en.triggered.connect(lambda: self._set_language("en"))
        lang_menu.addAction(act_en)

        act_es = QAction(self.tr("Espanol"), self)
        act_es.setCheckable(True)
        act_es.setChecked(current_lang == "es")
        act_es.triggered.connect(lambda: self._set_language("es"))
        lang_menu.addAction(act_es)

        help_menu = menu.addMenu(self.tr("&Ajuda"))
        act_tutorial = QAction(self.tr("Tutorial"), self)
        act_tutorial.triggered.connect(self._show_tutorial)
        help_menu.addAction(act_tutorial)
        help_menu.addSeparator()
        act_about = QAction(self.tr("Sobre"), self)
        act_about.triggered.connect(self._show_about)
        help_menu.addAction(act_about)

    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        layout = QHBoxLayout(central)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(0)

        # Splitter: tree | editor
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setObjectName("mainSplitter")
        layout.addWidget(splitter)

        # ── Tree panel ──
        tree_container = QWidget()
        tree_container.setObjectName("treePanel")
        tree_layout = QVBoxLayout(tree_container)
        tree_layout.setContentsMargins(0, 0, 0, 0)

        tree_header_container = labeled_icon("pickaxe", self.tr("Mods"))
        tree_header_container.setObjectName("treeHeader")
        tree_layout.addWidget(tree_header_container)

        # Search field
        self.search_field = QLineEdit()
        self.search_field.setObjectName("searchField")
        self.search_field.setPlaceholderText(self.tr("🔍 Buscar mod ou arquivo de config..."))
        self.search_field.setClearButtonEnabled(True)
        self.search_field.textChanged.connect(self._on_search)
        tree_layout.addWidget(self.search_field)

        self.tree = ModTreeWidget()
        self.tree.setObjectName("modTree")
        self.tree.setHeaderLabels([self.tr("Nome"), self.tr("Tipo")])
        self.tree.header().setStretchLastSection(False)
        self.tree.header().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.tree.header().setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        self.tree.setColumnWidth(1, 80)
        self.tree.setIndentation(16)
        self.tree.itemClicked.connect(self._on_tree_clicked)
        self.tree.itemExpanded.connect(self._on_tree_expand)
        self.tree.drop_requested.connect(self._on_config_dropped)
        self.tree.delete_requested.connect(self._on_item_delete)
        self.tree.copy_requested.connect(self._on_item_copy)
        self.tree.paste_requested.connect(self._on_item_paste)
        tree_layout.addWidget(self.tree)

        splitter.addWidget(tree_container)
        splitter.setStretchFactor(0, 1)

        # ── Editor panel ──
        editor_container = QWidget()
        editor_container.setObjectName("editorPanel")
        editor_layout = QVBoxLayout(editor_container)
        editor_layout.setContentsMargins(0, 0, 0, 0)

        # Instance info bar
        self.instance_label = QLabel("")
        self.instance_label.setObjectName("instanceLabel")
        self.instance_label.setVisible(False)
        editor_layout.addWidget(self.instance_label)

        self.editor_header = QLabel("")
        self.editor_header.setObjectName("editorHeader")
        self.editor_header.setVisible(False)
        editor_layout.addWidget(self.editor_header)

        self.editor = EditorPanel()
        self.editor.on_modified = self._update_buttons
        editor_layout.addWidget(self.editor)

        # Action buttons
        btn_layout = QHBoxLayout()
        btn_layout.setContentsMargins(12, 8, 12, 10)
        btn_layout.setSpacing(8)

        btn_layout.addStretch()
        self.btn_backup = QPushButton(self.tr(" Backup"))
        self.btn_backup.setObjectName("btnBackup")
        self.btn_backup.setEnabled(False)
        self.btn_backup.setToolTip(self.tr("Cria uma copia de seguranca apenas deste arquivo (nao de todos os mods)"))
        self.btn_backup.clicked.connect(self._backup_current)
        icon_button(self.btn_backup, "save")
        btn_layout.addWidget(self.btn_backup)

        # ── Export / Import / ZIP ──
        self.btn_export = QPushButton(self.tr(" Exportar"))
        self.btn_export.setObjectName("btnExport")
        self.btn_export.setEnabled(False)
        self.btn_export.setToolTip(self.tr("Exporta o arquivo de config selecionado para uma pasta de sua escolha"))
        self.btn_export.clicked.connect(self._export_config)
        icon_button(self.btn_export, "file")
        btn_layout.addWidget(self.btn_export)

        self.btn_import = QPushButton(self.tr(" Importar"))
        self.btn_import.setObjectName("btnImport")
        self.btn_import.setToolTip(self.tr("Importa um arquivo de config para a instancia atual (pasta imports/)"))
        self.btn_import.clicked.connect(self._import_config)
        icon_button(self.btn_import, "folder")
        btn_layout.addWidget(self.btn_import)

        self.btn_export_zip = QPushButton(self.tr(" Exportar ZIP"))
        self.btn_export_zip.setObjectName("btnExportZip")
        self.btn_export_zip.setToolTip(self.tr("Exporta todas as configuracoes da instancia em um arquivo ZIP"))
        self.btn_export_zip.clicked.connect(self._export_all_zip)
        icon_button(self.btn_export_zip, "save")
        btn_layout.addWidget(self.btn_export_zip)

        self.btn_cancel = QPushButton(self.tr(" Desfazer"))
        self.btn_cancel.setObjectName("btnCancelar")
        self.btn_cancel.setEnabled(False)
        self.btn_cancel.setToolTip(self.tr("Desfaz a ultima alteracao e recarrega o arquivo original"))
        self.btn_cancel.clicked.connect(self._cancel_changes)
        icon_button(self.btn_cancel, "undo")
        btn_layout.addWidget(self.btn_cancel)

        self.btn_save = QPushButton(self.tr(" Salvar"))
        self.btn_save.setObjectName("btnSalvar")
        self.btn_save.setEnabled(False)
        self.btn_save.setToolTip(self.tr("Salva as alteracoes no arquivo de configuracao (backup automatico antes)"))
        self.btn_save.clicked.connect(self._save_current)
        icon_button(self.btn_save, "save")
        btn_layout.addWidget(self.btn_save)

        editor_layout.addLayout(btn_layout)

        splitter.addWidget(editor_container)
        splitter.setStretchFactor(1, 2)
        splitter.setSizes([400, 800])

    def _build_statusbar(self) -> None:
        self.status = QStatusBar()
        self.status.setObjectName("appStatusBar")
        self.setStatusBar(self.status)
        self.status.showMessage(icon_text("check") + " " + self.tr("Pronto. Selecione um arquivo para editar."))
        version_label = QLabel(f"v{VERSION}")
        version_label.setObjectName("versionLabel")
        self.status.addPermanentWidget(version_label)

    # ── CSS ─────────────────────────────────────────────────────────

    def _load_custom_css(self) -> None:
        initial = str(STYLE_DIR) if STYLE_DIR.is_dir() else ""
        path, _ = QFileDialog.getOpenFileName(
            self, self.tr("Selecionar arquivo CSS"), initial,
            "CSS Files (*.css *.qss);;All Files (*)",
            options=QFileDialog.Option.DontUseNativeDialog,
        )
        if path:
            save_custom_css_path(path)
            app = QApplication.instance()
            if app:
                try:
                    css = Path(path).read_text(encoding="utf-8")
                    app.setStyleSheet(css)
                except Exception:
                    pass
            self.status.showMessage(icon_text("check") + " " + self.tr("CSS carregado: %1").replace("%1", Path(path).name))

    def _reset_css(self) -> None:
        data = load_settings()
        if "custom_css_path" in data:
            del data["custom_css_path"]
            save_settings(data)
        app = QApplication.instance()
        if app:
            app.setStyleSheet(DEFAULT_CSS)
        self.status.showMessage(icon_text("check") + " " + self.tr("CSS padrao restaurado"))

    def _set_language(self, lang: str) -> None:
        if not self._confirm_discard_unsaved():
            return
        data = load_settings()
        data["language"] = lang
        save_settings(data)
        QMessageBox.information(
            self,
            self.tr("Idioma alterado"),
            self.tr("O idioma foi alterado para %1.\n"
               "O aplicativo sera reiniciado automaticamente.").replace("%1",
                {"pt_BR": self.tr("Portugues"), "en": "English", "es": self.tr("Espanol")}[lang]
            ),
        )
        if hasattr(os, "execv"):
            os.execv(sys.executable, [sys.executable] + sys.argv[1:])
        else:
            subprocess.Popen([sys.executable] + sys.argv[1:])
            QApplication.quit()

    def _check_for_updates(self) -> None:
        self._nam = QNetworkAccessManager(self)
        self._nam.finished.connect(self._on_update_check)
        req = QNetworkRequest(QUrl(GITHUB_RELEASES_API))
        req.setTransferTimeout(8000)
        req.setRawHeader(b"Accept", b"application/vnd.github+json")
        self._nam.get(req)

    def _on_update_check(self, reply: QNetworkReply) -> None:
        if reply.error() != QNetworkReply.NetworkError.NoError:
            log.info("Update check: network error or offline")
            reply.deleteLater()
            return
        try:
            data = json.loads(bytes(reply.readAll()).decode())
            latest = data.get("tag_name", "").lstrip("v")
            if not latest:
                reply.deleteLater()
                return
            current_parts = [int(x) for x in VERSION.split(".")]
            latest_parts = [int(x) for x in latest.split(".")]
            if latest_parts > current_parts:
                answer = QMessageBox.question(
                    self,
                    self.tr("Nova versao disponivel"),
                    self.tr("Ha uma nova versao disponivel: v%1\n\n"
                           "Deseja abrir a pagina de downloads?").replace("%1", latest),
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.Yes,
                )
                if answer == QMessageBox.StandardButton.Yes:
                    QDesktopServices.openUrl(QUrl(GITHUB_RELEASES_URL))
            else:
                log.info("Update check: running latest version")
        except Exception as e:
            log.info("Update check: failed to parse response (%s)", e)
        finally:
            reply.deleteLater()

    # ── Instance loading ─────────────────────────────────────────────

    def _open_instance(self) -> None:
        if not self._confirm_discard_unsaved():
            return
        initial_dir = str(Path.home())
        settings = load_settings()
        if "last_instance" in settings:
            initial_dir = str(Path(settings["last_instance"]).parent)

        path = QFileDialog.getExistingDirectory(
            self, self.tr("Selecione a pasta da instancia Minecraft"), initial_dir,
            options=QFileDialog.Option.DontUseNativeDialog,
        )
        if path:
            self._load_configs(path)

    def _load_configs(self, path_str: str, save: bool = True) -> None:
        inst_path = Path(path_str)
        if (inst_path / "minecraft" / "config").is_dir():
            config_dir = inst_path / "minecraft" / "config"
        elif (inst_path / "config").is_dir():
            config_dir = inst_path / "config"
        else:
            config_dir = inst_path

        if not config_dir.is_dir():
            QMessageBox.critical(self, self.tr("Erro"),
                                 self.tr("Diretorio de config nao encontrado:\n%1").replace("%1", str(config_dir)))
            return

        self._instance_path = str(config_dir)
        self._current_file = None

        # Deriva nome da instancia
        if config_dir.parent.name == "minecraft":
            inst_name = config_dir.parent.parent.name
        else:
            inst_name = config_dir.parent.name
        self._instance_name = inst_name

        # Limpa editor da instancia anterior
        self.editor._clear_widgets()
        self.editor._tabs.setVisible(False)
        self.editor._placeholder.setText(icon_text("wrench") + self.tr("Selecione um arquivo de configuracao na arvore ao lado"))
        self.editor._placeholder.setObjectName("editorPlaceholder")
        self.editor._placeholder.setVisible(True)
        self.editor_header.setVisible(False)

        # Mostra label da instancia atual
        self.instance_label.setText(icon_text("castle") + self.tr("Voce esta editando a instância: %1").replace("%1", str(inst_name)))
        self.instance_label.setVisible(True)

        # Desabilita botoes
        self.btn_backup.setEnabled(False)
        self.btn_save.setEnabled(False)
        self.btn_cancel.setEnabled(False)

        try:
            scanner = ConfigScanner(config_dir)
            self._groups = scanner.scan()
        except Exception as e:
            QMessageBox.critical(self, self.tr("Erro"), self.tr("Erro ao carregar configs:\n%1").replace("%1", str(e)))
            return

        self._populate_tree()
        total = sum(len(g.files) for g in self._groups)
        self.setWindowTitle(self.tr("Minecraft Mod Config Editor \u2014 %1 \u2014 by Makalove").replace("%1", str(inst_name)))
        self.status.showMessage(icon_text("check") + " " + self.tr("%1 mods, %2 arquivos carregados").replace("%1", str(len(self._groups))).replace("%2", str(total)))
        self._update_buttons()

        if save:
            set_last_instance(str(config_dir))
            log.info("Ultima instancia salva: %s", config_dir)

    def _reload_all(self) -> None:
        if not self._confirm_discard_unsaved():
            return
        if self._instance_path:
            self._load_configs(self._instance_path, save=False)
            self.editor._clear_widgets()
            self.editor._tabs.setVisible(False)
            self.editor._placeholder.setVisible(True)

    # ── Tree ─────────────────────────────────────────────────────────

    def _populate_tree(self) -> None:
        self.tree.clear()
        icon_mod = load_icon("block")
        for group in self._groups:
            mod_item = QTreeWidgetItem(self.tree)
            mod_item.setText(0, group.display_name)
            mod_item.setIcon(0, icon_mod)
            mod_item.setText(1, f"{len(group.files)}")
            mod_item.setData(0, Qt.ItemDataRole.UserRole, group)
            mod_item.setToolTip(0, self.tr("%1 config files").replace("%1", str(len(group.files))))

            font = mod_item.font(0)
            font.setBold(True)
            mod_item.setFont(0, font)

            for cf in group.files:
                file_item = QTreeWidgetItem(mod_item)
                file_item.setText(0, cf.display_name)
                file_item.setText(1, cf.fmt.upper())
                file_item.setData(0, Qt.ItemDataRole.UserRole, cf)
                fmt_icon = _file_format_icon(cf.fmt)
                if not fmt_icon.isNull():
                    file_item.setIcon(0, fmt_icon)

        if self._groups and len(self._groups) <= 15:
            self.tree.expandAll()

    def _on_search(self, text: str) -> None:
        """Filter mod tree by mod name or config file name (case-insensitive substring)."""
        search = text.strip().lower()
        for i in range(self.tree.topLevelItemCount()):
            group_item = self.tree.topLevelItem(i)
            if group_item is None:
                continue
            group_name = group_item.text(0).lower()
            group_match = search in group_name
            any_child_visible = False
            for j in range(group_item.childCount()):
                child = group_item.child(j)
                if child is None:
                    continue
                if search == "" or group_match or search in child.text(0).lower():
                    child.setHidden(False)
                    any_child_visible = True
                else:
                    child.setHidden(True)
            group_item.setHidden(search != "" and not any_child_visible)

    def _on_tree_clicked(self, item: QTreeWidgetItem, _col: int) -> None:
        cf = item.data(0, Qt.ItemDataRole.UserRole)
        if cf is None:
            return
        if not isinstance(cf, ConfigFile):
            return

        if self._current_file and self._current_file is not cf:
            if not self._confirm_discard_unsaved():
                return

        self._current_file = cf
        self._load_file_into_editor(cf)

    def _confirm_discard_unsaved(self) -> bool:
        """Returns True if safe to proceed (saved/discarded), False if cancelled."""
        if not self._current_file or not self.editor.is_modified():
            return True
        answer = QMessageBox.question(
            self,
            self.tr("Arquivo nao salvo"),
            self.tr("Voce nao salvou o arquivo %1.\nDeseja salvar antes de continuar?").replace("%1", self._current_file.display_name),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No | QMessageBox.StandardButton.Cancel,
        )
        if answer == QMessageBox.StandardButton.Yes:
            self._save_current()
            return not self.editor.is_modified()
        if answer == QMessageBox.StandardButton.No:
            self._cancel_changes()
            return True
        return False

    def _on_tree_expand(self, item: QTreeWidgetItem) -> None:
        if item.childCount() == 0:
            return
        font = item.font(0)
        font.setBold(True)
        item.setFont(0, font)

    def _on_config_dropped(self, src_cf: ConfigFile, target_mod_item: QTreeWidgetItem) -> None:
        target_group = target_mod_item.data(0, Qt.ItemDataRole.UserRole)
        if not isinstance(target_group, ModGroup):
            return
        config_dir = Path(self._instance_path)
        target_dir = config_dir / target_group.key
        target_dir.mkdir(parents=True, exist_ok=True)
        src_group = None
        for g in self._groups:
            if src_cf in g.files:
                src_group = g
                break
        # Protect unsaved changes in editor
        if src_cf is self._current_file:
            if not self._confirm_discard_unsaved():
                return
            self._current_file = None
            self.editor._clear_widgets()
            self.editor._tabs.setVisible(False)
            self.editor._placeholder.setVisible(True)
            self.editor_header.setVisible(False)
            self._update_buttons()
        action = self._ask_copy_or_move(src_cf.display_name, target_group.display_name)
        if action is None:
            return
        dest_path = target_dir / src_cf.path.name
        if dest_path.exists():
            conflict_action = self._ask_file_conflict(dest_path.name)
            if conflict_action is None:
                return
            if conflict_action == "rename":
                dest_path = self._find_available_name(target_dir, Path(src_cf.path.stem), src_cf.path.suffix)
        try:
            if action == "move":
                shutil.move(str(src_cf.path), str(dest_path))
                src_cf.path = dest_path
                if src_group is not None and src_cf in src_group.files:
                    src_group.files.remove(src_cf)
                if src_cf not in target_group.files:
                    target_group.add_file(src_cf)
                self._populate_tree()
                self.status.showMessage(icon_text("check") + " " + self.tr("%1 movido para %2").replace("%1", src_cf.display_name).replace("%2", target_group.display_name))
            else:
                shutil.copy2(str(src_cf.path), str(dest_path))
                new_cf = ConfigFile(dest_path, src_cf.fmt)
                target_group.add_file(new_cf)
                self._populate_tree()
                self.status.showMessage(icon_text("check") + " " + self.tr("%1 copiado para %2").replace("%1", src_cf.display_name).replace("%2", target_group.display_name))
        except OSError as e:
            self.status.showMessage(icon_text("error") + " " + self.tr("Erro: %1").replace("%1", str(e)))

    def _ask_copy_or_move(self, src_name: str, tgt_name: str) -> Optional[str]:
        msg = QMessageBox(self)
        msg.setWindowTitle(self.tr("Copiar ou Mover"))
        msg.setText(self.tr("Deseja copiar ou mover \"%1\" para \"%2\"?").replace("%1", src_name).replace("%2", tgt_name))
        msg.setIcon(QMessageBox.Icon.Question)
        btn_copy = msg.addButton(self.tr("Copiar"), QMessageBox.ButtonRole.AcceptRole)
        btn_move = msg.addButton(self.tr("Mover"), QMessageBox.ButtonRole.ActionRole)
        btn_cancel = msg.addButton(self.tr("Cancelar"), QMessageBox.ButtonRole.RejectRole)
        msg.setDefaultButton(btn_copy)
        msg.exec()
        clicked = msg.clickedButton()
        if clicked == btn_copy:
            return "copy"
        if clicked == btn_move:
            return "move"
        return None

    def _ask_file_conflict(self, filename: str) -> Optional[str]:
        msg = QMessageBox(self)
        msg.setWindowTitle(self.tr("Arquivo ja existe"))
        msg.setText(self.tr("\"%1\" ja existe no destino. O que deseja fazer?").replace("%1", filename))
        msg.setIcon(QMessageBox.Icon.Warning)
        btn_replace = msg.addButton(self.tr("Substituir"), QMessageBox.ButtonRole.AcceptRole)
        btn_rename = msg.addButton(self.tr("Renomear"), QMessageBox.ButtonRole.ActionRole)
        btn_cancel = msg.addButton(self.tr("Cancelar"), QMessageBox.ButtonRole.RejectRole)
        msg.setDefaultButton(btn_rename)
        msg.exec()
        clicked = msg.clickedButton()
        if clicked == btn_replace:
            return "replace"
        if clicked == btn_rename:
            return "rename"
        return None

    def _find_available_name(self, directory: Path, stem: str, suffix: str) -> Path:
        counter = 1
        while True:
            candidate = directory / f"{stem} ({counter}){suffix}"
            if not candidate.exists():
                return candidate
            counter += 1

    def _on_item_delete(self, item: QTreeWidgetItem) -> None:
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if isinstance(data, ConfigFile):
            self._delete_file(data)
        elif isinstance(data, ModGroup):
            self._delete_folder(data)

    def _delete_file(self, cf: ConfigFile) -> None:
        msg = QMessageBox(self)
        msg.setWindowTitle(self.tr("Confirmar exclusao"))
        msg.setText(self.tr("Tem certeza que deseja excluir \"%1\"?\n\nEsta acao nao pode ser desfeita.").replace("%1", cf.display_name))
        msg.setIcon(QMessageBox.Icon.Warning)
        btn_yes = msg.addButton(self.tr("Sim"), QMessageBox.ButtonRole.YesRole)
        btn_no = msg.addButton(self.tr("Nao"), QMessageBox.ButtonRole.NoRole)
        btn_cancel = msg.addButton(self.tr("Cancelar"), QMessageBox.ButtonRole.RejectRole)
        msg.setDefaultButton(btn_cancel)
        msg.exec()
        if msg.clickedButton() != btn_yes:
            return
        if cf is self._current_file:
            self._current_file = None
            self.editor._clear_widgets()
            self.editor._tabs.setVisible(False)
            self.editor._placeholder.setVisible(True)
            self.editor_header.setVisible(False)
            self._update_buttons()
        try:
            cf.path.unlink(missing_ok=True)
        except OSError as e:
            self.status.showMessage(icon_text("error") + " " + self.tr("Erro ao excluir: %1").replace("%1", str(e)))
            return
        for g in self._groups:
            if cf in g.files:
                g.files.remove(cf)
                break
        self._populate_tree()
        self.status.showMessage(icon_text("check") + " " + self.tr("\"%1\" excluido").replace("%1", cf.display_name))

    def _delete_folder(self, group: ModGroup) -> None:
        msg = QMessageBox(self)
        msg.setWindowTitle(self.tr("Confirmar exclusao"))
        msg.setText(self.tr("Tem certeza que deseja excluir a pasta \"%1\"\ncom %2 arquivo(s)?\n\nEsta acao nao pode ser desfeita.").replace("%1", group.display_name).replace("%2", str(len(group.files))))
        msg.setIcon(QMessageBox.Icon.Warning)
        btn_yes = msg.addButton(self.tr("Sim"), QMessageBox.ButtonRole.YesRole)
        btn_no = msg.addButton(self.tr("Nao"), QMessageBox.ButtonRole.NoRole)
        btn_cancel = msg.addButton(self.tr("Cancelar"), QMessageBox.ButtonRole.RejectRole)
        msg.setDefaultButton(btn_cancel)
        msg.exec()
        if msg.clickedButton() != btn_yes:
            return
        config_dir = Path(self._instance_path)
        target_dir = config_dir / group.key
        if self._current_file and self._current_file in group.files:
            self._current_file = None
            self.editor._clear_widgets()
            self.editor._tabs.setVisible(False)
            self.editor._placeholder.setVisible(True)
            self.editor_header.setVisible(False)
            self._update_buttons()
        try:
            if target_dir.is_dir():
                shutil.rmtree(target_dir)
        except OSError as e:
            self.status.showMessage(icon_text("error") + " " + self.tr("Erro ao excluir: %1").replace("%1", str(e)))
            return
        self._groups = [g for g in self._groups if g is not group]
        self._populate_tree()
        self.status.showMessage(icon_text("check") + " " + self.tr("\"%1\" excluida").replace("%1", group.display_name))

    def _on_item_copy(self, item: QTreeWidgetItem) -> None:
        cf = item.data(0, Qt.ItemDataRole.UserRole)
        if not isinstance(cf, ConfigFile):
            return
        self._clipboard_cf = cf
        self.tree.clipboard_file = cf
        self.status.showMessage(icon_text("check") + " " + self.tr("\"%1\" copiado. Clique com botao direito no mod de destino e escolha Colar.").replace("%1", cf.display_name))

    def _on_item_paste(self, item: QTreeWidgetItem) -> None:
        if self._clipboard_cf is None:
            return
        target_group = item.data(0, Qt.ItemDataRole.UserRole)
        if not isinstance(target_group, ModGroup):
            return
        self._on_config_dropped(self._clipboard_cf, item)

    def _load_file_into_editor(self, cf: ConfigFile) -> None:
        log.info("Editor: carregando %s (%s)", cf.path.name, cf.fmt)
        self.editor_header.setText(icon_text("file") + cf.display_name)
        self.editor_header.setObjectName("fileSub" if cf.is_structured else "windowTitle")
        self.editor_header.setVisible(True)
        self.editor.load_file(cf)
        self._update_buttons()

    def _update_buttons(self) -> None:
        cf = self._current_file
        has_file = cf is not None and cf.parsed_ok
        has_instance = self._instance_path is not None
        self.btn_backup.setEnabled(has_file)
        self.btn_save.setEnabled(has_file and cf.modified if cf else False)
        self.btn_cancel.setEnabled(has_file and cf.modified if cf else False)
        self.btn_export.setEnabled(has_file)
        self.btn_import.setEnabled(has_instance)
        self.btn_export_zip.setEnabled(has_instance)

    # ── Actions ───────────────────────────────────────────────────────

    def _backup_current(self) -> None:
        if not self._current_file:
            return
        bak = self._current_file.backup()
        if bak:
            self.status.showMessage(icon_text("check") + " " + self.tr("Backup salvo em: %1").replace("%1", str(bak)))
        else:
            self.status.showMessage(icon_text("error") + " " + self.tr("Erro ao criar backup."))

    def _export_config(self) -> None:
        cf = self._current_file
        if not cf or not cf.path.exists():
            return
        dest, _ = QFileDialog.getSaveFileName(
            self,
            self.tr("Exportar arquivo de configuracao"),
            str(cf.path.name),
            "Config Files (*.toml *.json *.json5 *.yaml *.yml *.cfg *.properties *.txt *.snbt *.ini);;All Files (*)",
            options=QFileDialog.Option.DontUseNativeDialog,
        )
        if dest:
            try:
                shutil.copy2(cf.path, dest)
                self.status.showMessage(icon_text("check") + " " + self.tr("Arquivo exportado: %1").replace("%1", Path(dest).name))
            except OSError as e:
                self.status.showMessage(icon_text("error") + " " + self.tr("Erro ao exportar: %1").replace("%1", str(e)))

    def _import_config(self) -> None:
        if not self._instance_path:
            return
        files, _ = QFileDialog.getOpenFileNames(
            self,
            self.tr("Importar arquivo(s) de configuracao"),
            "",
            "Config Files (*.toml *.json *.json5 *.yaml *.yml *.cfg *.properties *.txt *.snbt *.ini);;All Files (*)",
            options=QFileDialog.Option.DontUseNativeDialog,
        )
        if not files:
            return
        imports_dir = Path(self._instance_path) / "imports"
        imports_dir.mkdir(exist_ok=True)
        imported = 0
        for src in files:
            src_path = Path(src)
            dest = imports_dir / src_path.name
            try:
                shutil.copy2(src_path, dest)
                imported += 1
            except OSError as e:
                log.warning("Import: erro ao copiar %s: %s", src, e)
        if imported:
            self._reload_all()
            QMessageBox.information(
                self,
                self.tr("Importacao concluida"),
                self.tr("%1 arquivo(s) importado(s) para:\n%2\n\nUse o campo de busca \U0001f50d para encontra-lo(s).").replace("%1", str(imported)).replace("%2", str(imports_dir)),
            )
        else:
            self.status.showMessage(icon_text("error") + " " + self.tr("Nenhum arquivo importado. Verifique as permissoes."))

    def _export_all_zip(self) -> None:
        if not self._instance_path or not self._instance_name:
            return
        config_dir = Path(self._instance_path)
        if not config_dir.is_dir():
            return
        exports_dir = SCRIPT_DIR / "exports"
        exports_dir.mkdir(exist_ok=True)
        date_str = datetime.datetime.now().strftime("%Y-%m-%d")
        safe_name = re.sub(r'[\\/*?:"<>|]', "_", self._instance_name)
        zip_path = exports_dir / f"{safe_name}_{date_str}.zip"
        try:
            with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
                for file_path in config_dir.rglob("*"):
                    if file_path.is_file():
                        arcname = file_path.relative_to(config_dir)
                        zf.write(file_path, arcname)
            export_msg = QMessageBox(self)
            export_msg.setWindowTitle(self.tr("Exportacao ZIP concluida"))
            export_msg.setText(self.tr("ZIP exportado com sucesso:\n%1").replace("%1", str(zip_path)))
            export_msg.setIcon(QMessageBox.Icon.Information)
            btn_ok = export_msg.addButton(self.tr("OK"), QMessageBox.ButtonRole.AcceptRole)
            btn_open = export_msg.addButton(self.tr("Abrir pasta"), QMessageBox.ButtonRole.ActionRole)
            export_msg.setDefaultButton(btn_ok)
            export_msg.exec()
            if export_msg.clickedButton() == btn_open:
                QDesktopServices.openUrl(QUrl.fromLocalFile(str(exports_dir)))
        except OSError as e:
            self.status.showMessage(icon_text("error") + " " + self.tr("Erro ao criar ZIP: %1").replace("%1", str(e)))

    def _cancel_changes(self) -> None:
        if not self._current_file or not self._current_file.modified:
            return
        self._current_file.parsed_ok = False
        self._current_file._modified_data = None
        self._current_file.modified = False
        self._current_file.parse()
        self.editor.reload()
        self._update_buttons()
        self.status.showMessage(icon_text("undo") + " " + self.tr("Alteracoes desfeitas. Arquivo original recarregado."))

    def _save_current(self) -> None:
        if not self._current_file:
            return
        ok, msg = self._current_file.save()
        if ok:
            self.status.showMessage(icon_text("check") + " " + msg)
            self._update_buttons()
            self.editor._modified = False
        else:
            self.status.showMessage(icon_text("error") + " " + msg)

    def _show_tutorial(self) -> None:
        dlg = TutorialDialog(self)
        dlg.exec()

    def _show_about(self) -> None:
        QMessageBox.about(
            self,
            self.tr("Sobre \u2014 Minecraft Mod Config Editor"),
            self.tr("Minecraft Mod Config Editor \u2014 by Makalove\n\n"
               "Edita arquivos de configuracao de mods Minecraft\n"
               "(TOML, JSON, JSON5, YAML e formatos raw).\n\n"
               "Multiplataforma: Windows, Linux, macOS\n"
               "Temas customizaveis via CSS (QSS)\n"
               "Icones PNG com fallback para emoji\n\n"
               "github.com/Adiog0/mc-config-editor")
        )

    def closeEvent(self, event) -> None:
        if not self._confirm_discard_unsaved():
            event.ignore()
            return
        # Save geometry
        settings = load_settings()
        settings["geometry"] = bytes(self.saveGeometry()).hex()
        save_settings(settings)
        event.accept()


# ── Entry point ────────────────────────────────────────────────────────


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(
        description="Minecraft Mod Config Editor (PyQt6)"
    )
    parser.add_argument("--instance", "-i", type=str, default=None,
                        help="Caminho para a pasta da instancia")
    args = parser.parse_args()

    log.info("Args: %s", sys.argv)
    log.info("OS: %s | platform: %s", platform.system(), sys.platform)

    # Create application
    app = QApplication(sys.argv)

    # Load i18n translator
    current_lang = detect_language()
    _ = load_translator(app, current_lang)

    # Apply CSS
    custom_css = get_custom_css()
    if custom_css:
        log.info("Usando CSS customizado")
        app.setStyleSheet(custom_css)
    else:
        log.info("Usando CSS padrao Minecraft")
        app.setStyleSheet(DEFAULT_CSS)

    # Resolve instance
    config_dir: Optional[str] = None
    if args.instance:
        config_dir = str(Path(args.instance).expanduser().resolve())
        log.info("Instancia via arg: %s", config_dir)

    window = MainWindow(config_dir)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()

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
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# PyQt6
from PyQt6.QtCore import Qt, QSettings, QSize, QTimer
from PyQt6.QtGui import QAction, QFont, QIcon, QPixmap
from PyQt6.QtWidgets import (
    QAbstractSpinBox, QApplication, QCheckBox, QFileDialog, QFrame, QHBoxLayout,
    QHeaderView, QLabel, QLineEdit, QMainWindow, QMenu, QMenuBar,
    QMessageBox, QPushButton, QScrollArea, QSizePolicy,
    QSpinBox, QSplitter, QStatusBar, QTextEdit, QTreeWidget,
    QTreeWidgetItem, QVBoxLayout, QWidget, QDoubleSpinBox,
)

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
log.info("=== mc-config-editor (PyQt6) iniciando ===")
log.info("Python: %s", sys.version)
log.info("Executable: %s", sys.executable)
log.info("Script dir: %s", SCRIPT_DIR)

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

    @property
    def display_name(self) -> str:
        return self.path.name

    @property
    def is_structured(self) -> bool:
        return self.fmt in ("toml", "json", "json5", "yaml")

    def parse(self) -> None:
        if self.parsed_ok:
            return
        try:
            raw = self.path.read_text(encoding="utf-8", errors="replace")
            self._original_raw = raw
        except Exception as e:
            self.parsed_ok = False
            self.parse_error = f"Read error: {e}"
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
            self.parse_error = f"TOML error: {e}"

    def _parse_json(self, raw: str) -> None:
        try:
            self.parsed_data = json.loads(raw)
            self._modified_data = self.parsed_data
            self.parsed_ok = True
        except json.JSONDecodeError as e:
            self.parsed_ok = False
            self.parse_error = f"JSON error: {e}"

    def _parse_json5(self, raw: str) -> None:
        try:
            import pyjson5
            self.parsed_data = pyjson5.loads(raw)
            self._modified_data = self.parsed_data
            self.parsed_ok = True
        except (ImportError, Exception) as e:
            self.parsed_ok = False
            self.parse_error = f"JSON5 error: {e}"

    def _parse_yaml(self, raw: str) -> None:
        try:
            import yaml
            self.parsed_data = yaml.safe_load(raw)
            self._modified_data = self.parsed_data
            self.parsed_ok = True
        except (ImportError, Exception) as e:
            self.parsed_ok = False
            self.parse_error = f"YAML error: {e}"

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
            return False, f"Write error: {e}"
        msg = "Saved."
        if bak:
            msg += f" Backup: {bak.name}"
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


class ParameterWidget(QWidget):
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

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)

        # Type label
        type_hint = ""
        if isinstance(value, bool):
            type_hint = "[bool]"
        elif isinstance(value, int):
            type_hint = "[int]"
        elif isinstance(value, float):
            type_hint = "[float]"
        elif isinstance(value, str):
            type_hint = "[text]"
        elif isinstance(value, list):
            type_hint = f"[list ({len(value)})]"

        label_text = f"{key}  {type_hint}"
        self.label = QLabel(label_text)
        self.label.setObjectName("paramLabel")
        self.label.setMinimumWidth(240)
        layout.addWidget(self.label)

        # Input widget based on type
        if isinstance(value, bool):
            self._widget = QCheckBox()
            self._widget.setChecked(bool(value))
            self._widget.stateChanged.connect(self._emit_change)
            layout.addWidget(self._widget)
            layout.addStretch()
        elif isinstance(value, int):
            self._widget = QSpinBox()
            self._widget.setRange(-2147483648, 2147483647)
            self._widget.setValue(int(value))
            self._widget.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.PlusMinus)
            self._widget.setFixedWidth(180)
            self._widget.valueChanged.connect(self._emit_change)
            layout.addWidget(self._widget)
            layout.addStretch()
        elif isinstance(value, float):
            self._widget = QDoubleSpinBox()
            self._widget.setRange(-1e12, 1e12)
            self._widget.setDecimals(4)
            self._widget.setValue(float(value))
            self._widget.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.PlusMinus)
            self._widget.setFixedWidth(180)
            self._widget.valueChanged.connect(self._emit_change)
            layout.addWidget(self._widget)
            layout.addStretch()
        elif isinstance(value, str):
            if len(value) > 60:
                self._widget = QTextEdit()
                self._widget.setPlainText(str(value))
                self._widget.setFixedHeight(80)
                self._widget.setMinimumWidth(300)
                self._widget.textChanged.connect(lambda: self._emit_change())
                layout.addWidget(self._widget)
            else:
                self._widget = QLineEdit(str(value))
                self._widget.setMinimumWidth(200)
                self._widget.textChanged.connect(lambda txt: self._emit_change())
                layout.addWidget(self._widget)
        elif isinstance(value, list):
            self._widget = QTextEdit()
            self._widget.setPlainText("\n".join(str(v) for v in value))
            self._widget.setFixedHeight(80)
            self._widget.setMinimumWidth(300)
            self._widget.textChanged.connect(lambda: self._emit_change())
            layout.addWidget(self._widget)
        else:
            self._widget = QLineEdit(str(value) if value is not None else "")
            self._widget.setMinimumWidth(200)
            self._widget.textChanged.connect(lambda txt: self._emit_change())
            layout.addWidget(self._widget)

        if self._on_delete is not None:
            self._btn_del = QPushButton("✕")
            self._btn_del.setObjectName("btnDeleteParam")
            icon_button(self._btn_del, "delete")
            self._btn_del.setFixedSize(28, 28)
            self._btn_del.setToolTip(f"Remover '{self.key}'")
            self._btn_del.clicked.connect(lambda: self._on_delete(self.key_path))
            layout.addWidget(self._btn_del)

    def _emit_change(self) -> None:
        if isinstance(self._widget, QCheckBox):
            new_val = self._widget.isChecked()
        elif isinstance(self._widget, QSpinBox):
            new_val = self._widget.value()
        elif isinstance(self._widget, QDoubleSpinBox):
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

        # Scroll area
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll_widget = QWidget()
        self._scroll_layout = QVBoxLayout(self._scroll_widget)
        self._scroll_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self._scroll.setWidget(self._scroll_widget)
        self._layout.addWidget(self._scroll)

        # Raw text editor (for non-structured formats)
        self._raw_editor = QTextEdit()
        self._raw_editor.setObjectName("rawEditor")
        self._raw_editor.setVisible(False)
        self._raw_editor.textChanged.connect(self._on_raw_changed)
        self._layout.addWidget(self._raw_editor)

        # Placeholder
        self._placeholder = QLabel(f"{icon_text("wrench")}Selecione um arquivo de configuracao na arvore ao lado")
        self._placeholder.setObjectName("editorPlaceholder")
        self._placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._layout.addWidget(self._placeholder)

    def load_file(self, cf: ConfigFile) -> None:
        self.current_file = cf
        self._modified = False
        self._clear_widgets()

        if cf.parse_error:
            self._show_error(cf)
            return
        if not cf.parsed_ok:
            cf.parse()
            if cf.parse_error:
                self._show_error(cf)
                return

        if cf.is_structured:
            self._raw_editor.setVisible(False)
            self._scroll.setVisible(True)
            self._placeholder.setVisible(False)
            self._build_structured(cf)
        else:
            self._scroll.setVisible(False)
            self._placeholder.setVisible(False)
            self._raw_editor.setVisible(True)
            self._raw_editor.setPlainText(cf.raw_content())

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
        self._scroll.setVisible(False)
        self._raw_editor.setVisible(False)
        self._placeholder.setText(f"{icon_text('error')} Erro: {cf.parse_error}")
        self._placeholder.setObjectName("editorError")
        self._placeholder.setVisible(True)

    def _build_structured(self, cf: ConfigFile) -> None:
        data = cf._modified_data
        if isinstance(data, dict):
            self._render_dict(cf, data, [])
        elif isinstance(data, list):
            pw = ParameterWidget("(root)", data, ["_root"], self._on_param_change, None, self)
            self._scroll_layout.addWidget(pw)
            self._param_widgets.append(pw)
        else:
            pw = ParameterWidget("(value)", data, ["_root"], self._on_param_change, None, self)
            self._scroll_layout.addWidget(pw)
            self._param_widgets.append(pw)

        # ADD button for dict-based configs
        if isinstance(data, dict):
            self._add_btn_row = QWidget()
            add_layout = QHBoxLayout(self._add_btn_row)
            add_layout.setContentsMargins(12, 8, 12, 8)
            add_layout.addStretch()
            btn_add = QPushButton(" Adicionar Parametro")
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

        hint_expand = " [Clique para expandir]"
        hint_collapse = " [Clique para recolher]"
        btn = QPushButton(f"  ▶ {name}{hint_expand}")
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

    @staticmethod
    def _toggle_section(btn: QPushButton, content: QWidget) -> None:
        visible = content.isVisible()
        content.setVisible(not visible)
        name = btn.property("mc_name")
        if visible:
            hint = btn.property("mc_hint_expand")
            btn.setText(f"  ▶ {name}{hint}")
        else:
            hint = btn.property("mc_hint_collapse")
            btn.setText(f"  ▼ {name}{hint}")

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
        dlg.setWindowTitle("Adicionar Parametro")
        dlg.setMinimumWidth(360)
        form = QFormLayout(dlg)

        name_edit = QLineEdit()
        name_edit.setPlaceholderText("nome_do_parametro")
        form.addRow("Nome:", name_edit)

        type_combo = QComboBox()
        type_combo.addItems(["texto", "numero inteiro", "numero decimal", "booleano (true/false)"])
        form.addRow("Tipo:", type_combo)

        value_edit = QLineEdit()
        value_edit.setPlaceholderText("valor")
        form.addRow("Valor:", value_edit)

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
                QMessageBox.warning(self, "Erro", f"Valor invalido para inteiro: {val_str}")
                return
        elif val_type == 2:
            try:
                value = float(val_str) if val_str else 0.0
            except ValueError:
                QMessageBox.warning(self, "Erro", f"Valor invalido para decimal: {val_str}")
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


class MainWindow(QMainWindow):
    """Janela principal do editor."""

    def __init__(self, config_dir: Optional[str] = None):
        super().__init__()
        self.setWindowTitle("Minecraft Mod Config Editor — by Makalove")
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

    def _build_menubar(self) -> None:
        menu = self.menuBar()

        file_menu = menu.addMenu("&Arquivo")
        act_open = QAction("Abrir Instancia...", self)
        act_open.setShortcut("Ctrl+O")
        act_open.setIcon(load_icon("folder"))
        act_open.triggered.connect(self._open_instance)
        file_menu.addAction(act_open)

        act_reload = QAction("Recarregar", self)
        act_reload.setShortcut("Ctrl+R")
        act_reload.setIcon(load_icon("refresh"))
        act_reload.triggered.connect(self._reload_all)
        file_menu.addAction(act_reload)

        file_menu.addSeparator()
        act_exit = QAction("Sair", self)
        act_exit.setShortcut("Ctrl+Q")
        act_exit.triggered.connect(self.close)
        file_menu.addAction(act_exit)

        view_menu = menu.addMenu("&Visual")
        act_css = QAction("Carregar CSS Customizado...", self)
        act_css.setIcon(load_icon("palette"))
        act_css.triggered.connect(self._load_custom_css)
        view_menu.addAction(act_css)

        act_reset_css = QAction("Resetar CSS Padrao", self)
        act_reset_css.setIcon(load_icon("refresh"))
        act_reset_css.triggered.connect(self._reset_css)
        view_menu.addAction(act_reset_css)

        help_menu = menu.addMenu("&Ajuda")
        act_about = QAction("Sobre", self)
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

        tree_header_container = labeled_icon("pickaxe", "Mods")
        tree_header_container.setObjectName("treeHeader")
        tree_layout.addWidget(tree_header_container)

        self.tree = QTreeWidget()
        self.tree.setObjectName("modTree")
        self.tree.setHeaderLabels(["Nome", "Tipo"])
        self.tree.header().setStretchLastSection(False)
        self.tree.header().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.tree.header().setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        self.tree.setColumnWidth(1, 80)
        self.tree.setIndentation(16)
        self.tree.itemClicked.connect(self._on_tree_clicked)
        self.tree.itemExpanded.connect(self._on_tree_expand)
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
        self.btn_backup = QPushButton(" Backup")
        self.btn_backup.setObjectName("btnBackup")
        self.btn_backup.setEnabled(False)
        self.btn_backup.clicked.connect(self._backup_current)
        icon_button(self.btn_backup, "save")
        btn_layout.addWidget(self.btn_backup)

        self.btn_cancel = QPushButton(" Cancelar")
        self.btn_cancel.setObjectName("btnCancelar")
        self.btn_cancel.setEnabled(False)
        self.btn_cancel.clicked.connect(self._cancel_changes)
        icon_button(self.btn_cancel, "undo")
        btn_layout.addWidget(self.btn_cancel)

        self.btn_save = QPushButton(" Salvar")
        self.btn_save.setObjectName("btnSalvar")
        self.btn_save.setEnabled(False)
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
        self.status.showMessage(f"{icon_text('check')} Pronto. Selecione um arquivo para editar.")

    # ── CSS ─────────────────────────────────────────────────────────

    def _load_custom_css(self) -> None:
        initial = str(STYLE_DIR) if STYLE_DIR.is_dir() else ""
        path, _ = QFileDialog.getOpenFileName(
            self, "Selecionar arquivo CSS", initial,
            "CSS Files (*.css *.qss);;All Files (*)"
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
            self.status.showMessage(f"{icon_text('check')} CSS carregado: {Path(path).name}")

    def _reset_css(self) -> None:
        data = load_settings()
        if "custom_css_path" in data:
            del data["custom_css_path"]
            save_settings(data)
        app = QApplication.instance()
        if app:
            app.setStyleSheet(DEFAULT_CSS)
        self.status.showMessage(f"{icon_text('check')} CSS padrao restaurado")

    # ── Instance loading ─────────────────────────────────────────────

    def _open_instance(self) -> None:
        initial_dir = str(Path.home())
        settings = load_settings()
        if "last_instance" in settings:
            initial_dir = str(Path(settings["last_instance"]).parent)

        path = QFileDialog.getExistingDirectory(
            self, "Selecione a pasta da instancia Minecraft", initial_dir
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
            QMessageBox.critical(self, "Erro",
                                 f"Diretorio de config nao encontrado:\n{config_dir}")
            return

        self._instance_path = str(config_dir)
        self._current_file = None

        # Deriva nome da instancia
        if config_dir.parent.name == "minecraft":
            inst_name = config_dir.parent.parent.name
        else:
            inst_name = config_dir.parent.name

        # Limpa editor da instancia anterior
        self.editor._clear_widgets()
        self.editor._raw_editor.setVisible(False)
        self.editor._scroll.setVisible(False)
        self.editor._placeholder.setText(f"{icon_text("wrench")}Selecione um arquivo de configuracao na arvore ao lado")
        self.editor._placeholder.setObjectName("editorPlaceholder")
        self.editor._placeholder.setVisible(True)
        self.editor_header.setVisible(False)

        # Mostra label da instancia atual
        self.instance_label.setText(f"{icon_text("castle")}Voce esta editando: {inst_name}")
        self.instance_label.setVisible(True)

        # Desabilita botoes
        self.btn_backup.setEnabled(False)
        self.btn_save.setEnabled(False)
        self.btn_cancel.setEnabled(False)

        try:
            scanner = ConfigScanner(config_dir)
            self._groups = scanner.scan()
        except Exception as e:
            QMessageBox.critical(self, "Erro", f"Erro ao carregar configs:\n{e}")
            return

        self._populate_tree()
        total = sum(len(g.files) for g in self._groups)
        self.setWindowTitle(f"Minecraft Mod Config Editor — {inst_name} — by Makalove")
        self.status.showMessage(f"{icon_text('check')} {len(self._groups)} mods, {total} arquivos carregados")

        if save:
            set_last_instance(str(config_dir))
            log.info("Ultima instancia salva: %s", config_dir)

    def _reload_all(self) -> None:
        if self._instance_path:
            self._load_configs(self._instance_path, save=False)
            self.editor._clear_widgets()
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
            mod_item.setData(0, Qt.ItemDataRole.UserRole, None)
            mod_item.setToolTip(0, f"{len(group.files)} config files")

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

    def _on_tree_clicked(self, item: QTreeWidgetItem, _col: int) -> None:
        cf = item.data(0, Qt.ItemDataRole.UserRole)
        if cf is None:
            return
        if not isinstance(cf, ConfigFile):
            return

        self._current_file = cf
        self._load_file_into_editor(cf)

    def _on_tree_expand(self, item: QTreeWidgetItem) -> None:
        if item.childCount() == 0:
            return
        font = item.font(0)
        font.setBold(True)
        item.setFont(0, font)

    def _load_file_into_editor(self, cf: ConfigFile) -> None:
        log.info("Editor: carregando %s (%s)", cf.path.name, cf.fmt)
        self.editor_header.setText(f"{icon_text("file")}{cf.display_name}")
        self.editor_header.setObjectName("fileSub" if cf.is_structured else "windowTitle")
        self.editor_header.setVisible(True)
        self.editor.load_file(cf)
        self._update_buttons()

    def _update_buttons(self) -> None:
        cf = self._current_file
        has_file = cf is not None and cf.parsed_ok
        self.btn_backup.setEnabled(has_file)
        self.btn_save.setEnabled(has_file and cf.modified if cf else False)
        self.btn_cancel.setEnabled(has_file and cf.modified if cf else False)

    # ── Actions ───────────────────────────────────────────────────────

    def _backup_current(self) -> None:
        if not self._current_file:
            return
        bak = self._current_file.backup()
        if bak:
            self.status.showMessage(f"{icon_text('check')} Backup: {bak.name}")
        else:
            self.status.showMessage(f"{icon_text('error')} Erro ao criar backup.")

    def _cancel_changes(self) -> None:
        if not self._current_file or not self._current_file.modified:
            return
        self._current_file.parsed_ok = False
        self._current_file._modified_data = None
        self._current_file.modified = False
        self._current_file.parse()
        self.editor.reload()
        self._update_buttons()
        self.status.showMessage(f"{icon_text('undo')} Alteracoes descartadas.")

    def _save_current(self) -> None:
        if not self._current_file:
            return
        ok, msg = self._current_file.save()
        if ok:
            self.status.showMessage(f"{icon_text('check')} {msg}")
            self._update_buttons()
            self.editor._modified = False
        else:
            self.status.showMessage(f"{icon_text('error')} {msg}")

    def _show_about(self) -> None:
        QMessageBox.about(
            self,
            "Sobre — Minecraft Mod Config Editor",
            "Minecraft Mod Config Editor — by Makalove\n\n"
            "Edita arquivos de configuracao de mods Minecraft\n"
            "(TOML, JSON, JSON5, YAML e formatos raw).\n\n"
            "Multiplataforma: Windows, Linux, macOS\n"
            "Temas customizaveis via CSS (QSS)\n"
            "Icones PNG com fallback para emoji\n\n"
            "github.com/makalove/mc-mod-config"
        )

    def closeEvent(self, event) -> None:
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

    # Apply CSS
    app = QApplication(sys.argv)
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

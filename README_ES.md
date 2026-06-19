# ⛏ Minecraft Mod Config Editor — by Makalove

Editor visual multiplataforma para archivos de configuración de mods de Minecraft.  
Funciona con cualquier instancia de Minecraft (vanilla, Forge, Fabric, PrismLauncher, ElyPrismLauncher y otros launchers).

![License: MIT](https://img.shields.io/badge/license-MIT-green)
![Platform: Cross-platform](https://img.shields.io/badge/platform-Windows%20%7C%20Linux%20%7C%20macOS-blue)
![Python: 3.10+](https://img.shields.io/badge/python-3.10%2B-blue)
![UI: PyQt6](https://img.shields.io/badge/UI-PyQt6-green)

---

## 📸 Capturas de pantalla

<details open>
<summary><b>Haga clic para expandir/colapsar</b></summary>
<br>
<img src="Screenshots/interface_1.png" alt="Pantalla principal" width="800"><br>
<img src="Screenshots/interface_2.png" alt="Editor de parámetros" width="800"><br>
<img src="Screenshots/interface_3.png" alt="Selección de mods" width="800"><br>
<img src="Screenshots/interface_4.png" alt="Editor raw y visual" width="800">
</details>

---

## 📋 Funcionalidades

- **Editor visual** con tarjetas estilizadas para cada parámetro (TOML, JSON, JSON5, YAML)
- **Editor Raw** con pestañas `Visual | Raw` para formatos heredados (CFG, Properties, TXT, SNBT, INI)
- **Toggle Switch** personalizado para booleanos (reemplaza checkbox)
- **Campos numéricos** con botones +/− visibles
- **Árbol expansible** de mods → archivos con selección resaltada
- **Secciones colapsables** con indicador ▶/▼ y sugerencia `[Haga clic para expandir]`
- **Agregar/quitar parámetros** vía la interfaz
- **Respaldo automático** con timestamp antes de cada guardado
- **Última instancia recordada** — reabre donde lo dejó
- **100% personalizable vía CSS** — edite `style/default.css` o cree `style/custom.css`
- **Íconos PNG** (30×30) con respaldo automático a emoji
- **Instalación automática de dependencias** al abrir la app

---

## 🚀 Cómo usar

### Linux / macOS
```bash
cd mc-mod-config
./mc-config-editor                        # selector de instancia
./mc-config-editor -i "ruta/instancia"    # directo
```

### Windows
```cmd
cd mc-mod-config
mc-config-editor.bat                      # selector de instancia
python mc-config-editor.py -i "C:\ruta\instancia"
```

### Python directo (cualquier SO)
```bash
pip install PyQt6 tomlkit pyjson5 pyyaml
python mc-config-editor.py
```

> Si alguna dependencia falta, la app pregunta si desea instalarla automáticamente.

---

## 📦 Dependencias

| Paquete | Uso |
|---|---|
| **PyQt6** >= 6.0 | Interfaz gráfica |
| **tomlkit** | Lectura/escritura de TOML preservando comentarios |
| **pyjson5** | Lectura/escritura de JSON5 |
| **pyyaml** | Lectura/escritura de YAML |

Instalación única:
```bash
pip install PyQt6 tomlkit pyjson5 pyyaml
```

---

## 🎨 Temas y CSS

La app está **100% controlada por CSS** (QSS — Qt Style Sheets).  
Cero colores hardcodeados en el código Python.

### Cambiando el tema
```bash
cp style/example.css style/custom.css   # crear desde plantilla
# Editar style/custom.css con sus colores
```

### Paletas listas (en `style/example.css`)
- **Azul Nocturno** — tonos de azul oscuro
- **Verde Bosque** — verde musgo
- **Gris Minimalista** — limpio y neutro

### Menú Ver
- `Ver → Cargar CSS Personalizado` — selecciona cualquier archivo `.css`
- `Ver → Restablecer CSS Predeterminado` — vuelve al tema original

---

## 🖼️ Íconos

Los íconos se cargan desde la carpeta `icons/` como archivos **PNG** (fondo transparente).  
Si un ícono no existe, la app usa el emoji correspondiente como respaldo.

| Archivo | Tamaño | Descripción |
|---|---|---|
| `pickaxe.png` | 30×30 | Ícono de la app |
| `castle.png` | 30×30 | Instancia actual |
| `folder.png` | 22×22 | Abrir instancia |
| `refresh.png` | 22×22 | Recargar |
| `palette.png` | 22×22 | Cargar CSS |
| `save.png` | 22×22 | Guardar / Respaldo |
| `undo.png` | 22×22 | Cancelar |
| `block.png` | 16×16 | Mods en el árbol |
| `settings.png` | 16×16 | Archivos TOML |
| `crafting.png` | 16×16 | Archivos JSON |
| `scroll.png` | 16×16 | Archivos YAML |
| `file.png` | 16×16 | Otros formatos |
| `add.png` | 22×22 | Agregar parámetro |
| `delete.png` | 22×22 | Eliminar parámetro |

---

## 🗂️ Estructura del proyecto

```
mc-mod-config/
├── mc-config-editor          ← lanzador Linux/macOS
├── mc-config-editor-qt       ← lanzador alternativo
├── mc-config-editor.bat      ← lanzador Windows
├── mc-config-editor.py       ← punto de entrada
├── mc-config-editor-qt.py    ← aplicación principal (PyQt6)
├── i18n/                     ← archivos de traducción (.ts / .qm)
├── icons/                    ← íconos PNG
├── style/                    ← temas CSS
└── Screenshots/              ← capturas de pantalla
```

---

## 🔒 Seguridad

- **Cero llamadas de red** — la app nunca accede a internet
- **Cero recolección de datos** — sin telemetría ni analytics
- Archivos de configuración leídos/escritos **solo localmente**

---

## 🧪 Formatos soportados

| Formato | Editor | Preserva comentarios |
|---|---|---|
| `.toml` | Visual (campos tipados) | ✅ Sí (vía tomlkit) |
| `.json` | Visual (campos tipados) | ❌ |
| `.json5` | Visual (campos tipados) | ❌ |
| `.yaml` / `.yml` | Visual (campos tipados) | ✅ Sí |
| `.cfg` | Raw (editor de texto) | ✅ Sí |
| `.properties` | Raw (editor de texto) | ✅ Sí |
| `.txt` | Raw (editor de texto) | ✅ Sí |
| `.snbt` | Raw (editor de texto) | ✅ Sí |
| `.ini` | Raw (editor de texto) | ✅ Sí |

---

## 📝 Notas

- La app ha sido probada con Minecraft vanilla, Forge, Fabric, **PrismLauncher** y **ElyPrismLauncher**
- La estructura de directorios esperada es: `instancia/minecraft/config/`
- Los respaldos se crean como `archivo.bak.YYYYMMDD_HHMMSS` en el mismo directorio
- Para desarrollo, use la rama `hml` (homologación). La rama `main` es producción

---

**Hecho con 💛 por Makalove**

> 📖 También disponible en: [Português](README.md) | [English](README_EN.md)

#!/usr/bin/env bash
# build.sh — Build standalone executable for Linux/macOS
# Usage: ./build/build.sh

set -euo pipefail
cd "$(dirname "$0")/.."

echo "==> mc-config-editor build (PyInstaller)"
echo "    Platform: $(uname -s)"
echo "    Python: $(python3 --version)"

# ── Install dependencies ───────────────────────────────────────────────
echo "==> Installing build dependencies..."
pip install pyinstaller PyQt6 tomlkit pyjson5 pyyaml 2>&1 | tail -3

# ── Clean previous build ────────────────────────────────────────────────
rm -rf build/mc-config-editor dist/mc-config-editor

# ── Build ───────────────────────────────────────────────────────────────
echo "==> Building with PyInstaller..."
pyinstaller \
    --noconfirm \
    --log-level=WARN \
    build/build.spec

# ── Verify output ───────────────────────────────────────────────────────
if [ -f "dist/mc-config-editor" ]; then
    size=$(du -h "dist/mc-config-editor" | cut -f1)
    echo "==> Done! dist/mc-config-editor ($size)"
elif [ -f "dist/mc-config-editor.exe" ]; then
    size=$(du -h "dist/mc-config-editor.exe" | cut -f1)
    echo "==> Done! dist/mc-config-editor.exe ($size)"
else
    echo "ERROR: Build output not found"
    exit 1
fi

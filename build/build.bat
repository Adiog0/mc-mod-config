@echo off
REM build.bat — Build standalone executable for Windows
REM Usage: build\build.bat

setlocal

echo ==^> mc-config-editor build (PyInstaller)
echo     Platform: Windows

REM ── Install dependencies ──────────────────────────────────────────────
echo ==^> Installing build dependencies...
pip install pyinstaller PyQt6 tomlkit pyjson5 pyyaml

REM ── Clean previous build ───────────────────────────────────────────────
if exist "build\mc-config-editor" rmdir /s /q "build\mc-config-editor"
if exist "dist\mc-config-editor.exe" del /q "dist\mc-config-editor.exe"

REM ── Build ──────────────────────────────────────────────────────────────
echo ==^> Building with PyInstaller...
pyinstaller --noconfirm --log-level=WARN build\build.spec

REM ── Verify output ──────────────────────────────────────────────────────
if exist "dist\mc-config-editor.exe" (
    echo ==^> Done! dist\mc-config-editor.exe
) else (
    echo ERROR: Build output not found
    exit /b 1
)

endlocal

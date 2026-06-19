@echo off
REM mc-config-editor.bat — Windows launcher
setlocal

set "SCRIPT_DIR=%~dp0"

REM Try project-local venv first, then user cache, then system python
set "VENV_PYTHON=%SCRIPT_DIR%venv\Scripts\python.exe"
if exist "%VENV_PYTHON%" goto :run
set "VENV_PYTHON=%USERPROFILE%\.cache\mc-config-editor-venv\Scripts\python.exe"
if exist "%VENV_PYTHON%" goto :run
set "VENV_PYTHON=python"

:run
echo 🚀 Minecraft Mod Config Editor
echo    Python: %VENV_PYTHON%
echo.
"%VENV_PYTHON%" "%SCRIPT_DIR%mc-config-editor.py" %*
endlocal

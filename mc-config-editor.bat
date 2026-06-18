@echo off
REM mc-config-editor.bat — Windows launcher for Minecraft Mod Config Editor
setlocal

set "SCRIPT_DIR=%~dp0"
set "VENV_PYTHON=%SCRIPT_DIR%venv\Scripts\python.exe"

if exist "%VENV_PYTHON%" goto :found_venv
REM Try user cache venv
set "VENV_PYTHON=%USERPROFILE%\.cache\mc-config-editor-venv\Scripts\python.exe"
if exist "%VENV_PYTHON%" goto :found_venv

REM No venv found - try system python
echo 🚀 Iniciando Minecraft Mod Config Editor...
echo    Python: system
echo.
python "%SCRIPT_DIR%mc-config-editor.py" %*
if errorlevel 1 (
    echo.
    echo ❌ Erro. Instale as dependencias:
    echo    pip install customtkinter tomlkit pyjson5 pyyaml
)
goto :end

:found_venv
echo 🚀 Iniciando Minecraft Mod Config Editor...
echo    Python: %VENV_PYTHON%
echo    Logs:   %SCRIPT_DIR%logs\
echo.
"%VENV_PYTHON%" "%SCRIPT_DIR%mc-config-editor.py" %*
goto :end

:end
endlocal

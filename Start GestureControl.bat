@echo off
setlocal
title GestureControl
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
    echo Python environment missing. Follow README.md installation instructions.
    pause
    exit /b 1
)
echo GestureControl - REAL CONTROL
echo Click the preview and press G to enable. Esc pauses. F12 exits.
".venv\Scripts\python.exe" "main.py" --use-defaults
if errorlevel 1 (
    echo.
    echo GestureControl could not start. See the error above.
    pause
)
endlocal

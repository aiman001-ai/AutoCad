@echo off
title AutoCAD 2026 Engine
echo ===================================================
echo Starting AutoCAD 2026 Engine (Qt6 + OpenGL + DXF)
echo ===================================================
python "%~dp0main.py"
if %errorlevel% neq 0 (
    echo.
    echo An error occurred while running AutoCAD software.
    pause
)


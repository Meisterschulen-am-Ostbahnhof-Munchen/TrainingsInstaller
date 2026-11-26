@echo off
rem Neues eigenes 4diac-Projekt (KONZEPT.md 2.5). Fragt nur nach dem Namen - geprueft wird
rem im Installer, der Name wird hier in cmd nie verarbeitet.
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0install.ps1" --new-project
echo.
pause

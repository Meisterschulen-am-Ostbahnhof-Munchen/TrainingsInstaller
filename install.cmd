@echo off
rem 4diac Trainings-Installer - Starter (siehe KONZEPT.md 3.1)
rem Ohne Argumente: GUI. Mit Argumenten (z. B. --headless, --check): Konsole.
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0install.ps1" %*
if errorlevel 1 (
    echo.
    echo Der Installer wurde mit einem Fehler beendet. Details im Log unter C:\ms\sl\logs
    pause
    exit /b 1
)

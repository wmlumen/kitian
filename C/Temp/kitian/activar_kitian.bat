@echo off
title Kitian HUD
cd /d C:\Temp\kitian

echo Iniciando HUD Tkinter...
tasklist /FI "IMAGENAME eq pythonw.exe" 2>NUL | find /I /N "pythonw.exe">NUL
if "%ERRORLEVEL%"=="0" (
  echo Hermes already running, opening HUD widget...
  start "" "%~f0" /B
  timeout /t 3 /nobreak >nul
  tasklist /FI "IMAGENAME eq pythonw.exe" 2>NUL | find /I /N "pythonw.exe">NUL
  if "%ERRORLEVEL%"=="0" (
    start "" "%CD%\kitian_hud.py"
  ) else (
    start "" "%CD%\kitian_http_standalone_real.py"
  )
) else (
  start "" "%CD%\kitian_http_standalone_real.py"
)
exit

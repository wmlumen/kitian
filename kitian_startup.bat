set KITIAN_CFG=C:\Temp\kitian
set KITIAN_SVC=kitian_http_standalone_real.py
@echo off
setlocal
set LOG=E:\Temp\kitian\kitian_startup.log
set PROJ=C:\Temp\kitian
mkdir "%PROJ%" >nul 2>&1
mkdir "E:\Temp\kitian" >nul 2>&1

echo === KITIAN BOOT %date% %time% === >> "%LOG%"

wsl bash -lc "cd %PROJ% && nohup python3 kitian_http_standalone_real.py > /tmp/kitian_wsl.log 2>&1 &"

timeout /t 4 /nobreak >nul
start "" "C:\Program Files\Google\Chrome\Application\chrome.exe" --app="http://localhost:8080/nebula"

echo DONE >> "%LOG%"

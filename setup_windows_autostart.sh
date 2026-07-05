#!/usr/bin/env bash
set -euo pipefail

CFG_HOME="${KITIAN_CFG:-/mnt/c/Temp/kitian}"
SERVICE="${KITIAN_SVC:-kitian_http_standalone_real.py}"
STARTUP="${CFG_HOME}/kitian_startup.bat"
PYTHON_BIN="$(command -v python3 || command -v python)"

mkdir -p "${CFG_HOME}" "${HOME}/.local/share/applications" "${HOME}/.config/autostart" ~/voice-memos

python3 - <<'PY'
from pathlib import Path, PureWindowsPath
text = Path('/mnt/c/Temp/kitian/kitian_startup.bat').read_text(encoding='utf-8') if Path('/mnt/c/Temp/kitian/kitian_startup.bat').exists() else ''
if 'KITIAN_CFG=' not in text:
    text = 'set KITIAN_CFG=C:\\Temp\\kitian\nset KITIAN_SVC=kitian_http_standalone_real.py\n' + text
if 'python3' not in text.lower() and 'python ' not in text.lower():
    text += '\npython3 "%KITIAN_CFG%\\%KITIAN_SVC%"\npause\n'
Path('/mnt/c/Temp/kitian/kitian_startup.bat').write_text(text, encoding='utf-8')
print('setup ok')
PY

chmod +x "${CFG_HOME}/kitian_startup.bat"

python3 - <<'PY'
from pathlib import Path
import os
home = Path.home()
linux_desktop = home / '.config/autostart' / 'kitian.desktop'
linux_target = '/mnt/c/Temp/kitian/kitian_startup.bat'
windows_target = 'C:\\Temp\\kitian\\kitian_startup.bat'
linux_desktop.write_text(f"""[Desktop Entry]
Type=Application
Name=Kitian
Exec=cmd.exe /c start "" "{windows_target}"
Path={home}/mnt/c/Temp/kitian
Icon=utilities-terminal
Terminal=true
StartupNotify=false
""", encoding='utf-8')
print('linux desktop ok')
PY

python3 - <<'PY'
from pathlib import Path
import os
task_name='KitianStandalone'
xml=f"""<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.2" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <Triggers>
    <LogonTrigger>
      <Enabled>true</Enabled>
    </LogonTrigger>
  </Triggers>
  <Principals>
    <Principal id="Author">
      <LogonType>InteractiveToken</LogonType>
      <RunLevel>LeastPrivilege</RunLevel>
    </Principal>
  </Principals>
  <Settings>
    <MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy>
    <DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries>
    <StopIfGoingOnBatteries>false</StopIfGoingOnBatteries>
    <AllowHardTerminate>true</AllowHardTerminate>
    <StartWhenAvailable>true</StartWhenAvailable>
    <RunOnlyIfNetworkAvailable>false</RunOnlyIfNetworkAvailable>
    <IdleSettings>
      <StopOnIdleEnd>false</StopOnIdleEnd>
      <RestartOnIdle>false</RestartOnIdle>
    </IdleSettings>
    <AllowStartOnDemand>true</AllowStartOnDemand>
    <Enabled>true</Enabled>
    <Hidden>false</Hidden>
    <RunOnlyIfIdle>false</RunOnlyIfIdle>
    <WakeToRun>false</WakeToRun>
    <ExecutionTimeLimit>PT0S</ExecutionTimeLimit>
    <Priority>7</Priority>
    <RestartOnFailure>
      <Interval>PT1M</Interval>
      <Count>3</Count>
    </RestartOnFailure>
  </Settings>
  <Actions Context="Author">
    <Exec>
      <Command>cmd.exe</Command>
      <Arguments>/c start "" "C:\\Temp\\kitian\\kitian_startup.bat"</Arguments>
      <WorkingDirectory>C:\\Temp\\kitian</WorkingDirectory>
    </Exec>
  </Actions>
</Task>
"""
Path('/tmp/kitian_task.xml').write_text(xml, encoding='utf-8')
print('xml prepared at /tmp/kitian_task.xml. Import it manually with: schtasks /Create /TN "KitianStandalone" /XML "C:\\Users\\<USER>\\AppData\\Local\\Temp\\kitian_task.xml" /F')
PY

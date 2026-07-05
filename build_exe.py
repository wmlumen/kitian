import PyInstaller.__main__
import os, sys
from pathlib import Path

BASE = Path(__file__).parent

PyInstaller.__main__.run([
    str(BASE / "kitian_full.py"),
    "--name=Kitian",
    "--onefile",
    "--noconsole",
    "--add-data", f"{BASE / 'kitian_hud.py'};.",
    "--add-data", f"{BASE / 'kitian_tts.py'};.",
    "--add-data", f"{BASE / 'kitian_stt.py'};.",
    "--add-data", f"{BASE / 'kitian_core.py'};.",
    "--add-data", f"{BASE / 'kitian_db.py'};.",
    "--add-data", f"{BASE / 'kitian_plugins.py'};.",
    "--add-data", f"{BASE / 'manifest.json'};.",
    "--add-data", f"{BASE / 'piper_models'};piper_models",
    "--add-data", f"{BASE / 'plugins'};plugins",
    "--hidden-import=tkinter",
    "--hidden-import=numpy",
    "--hidden-import=sounddevice",
    "--hidden-import=speech_recognition",
    "--hidden-import=psutil",
    "--hidden-import=pyttsx3",
    "--hidden-import=PIL",
    "--hidden-import=piper",
    "--clean",
])
print("Kitian.exe generado en dist/")

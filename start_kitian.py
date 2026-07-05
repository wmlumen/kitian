import importlib
import os
import subprocess
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
ENTRY = BASE_DIR / "kitian_full.py"


def check_python():
    version = sys.version_info
    if version.major < 3 or version.minor < 10:
        print(f"[start] Python 3.10+ requerido. Actual: {version.major}.{version.minor}.{version.micro}")
        return False
    print(f"[start] Python {version.major}.{version.minor}.{version.micro}")
    return True


def check_dependency(module_name, import_name=None, pip_name=None, required=False):
    import_name = import_name or module_name
    pip_name = pip_name or module_name
    try:
        importlib.import_module(import_name)
        print(f"[deps] OK {module_name}")
        return True
    except Exception as e:
        msg = f"[deps] MISSING {module_name} (pip install {pip_name}) -> {e.__class__.__name__}: {e}"
        print(msg)
        return False


def check_core_deps():
    required = [
        ("openai", "openai", "openai", True),
        ("psutil", "psutil", "psutil", True),
        ("SpeechRecognition", "speech_recognition", "SpeechRecognition", False),
        ("pyttsx3", "pyttsx3", "pyttsx3", False),
        ("sounddevice", "sounddevice", "sounddevice", False),
        ("numpy", "numpy", "numpy", True),
        ("keyboard", "keyboard", "keyboard", False),
        ("dotenv", "dotenv", "python-dotenv", True),
        ("faster_whisper", "faster_whisper", "faster-whisper", False),
        ("piper", "piper", "piper-tts", False),
        ("telegram", "telegram", "python-telegram-bot", False),
    ]
    missing_required = []
    missing_optional = []
    for module_name, import_name, pip_name, required_flag in required:
        ok = check_dependency(module_name, import_name, pip_name, required_flag)
        if not ok:
            if required_flag:
                missing_required.append(pip_name)
            else:
                missing_optional.append(pip_name)
    return missing_required, missing_optional


def run_health_quick():
    probe = BASE_DIR / "kitian_health_probe.py"
    if not probe.exists():
        print("[health] kitian_health_probe.py no encontrado; se omite health-check.")
        return True
    print("[health] Ejecutando health-check rapido...")
    try:
        result = subprocess.run(
            [sys.executable, str(probe)],
            cwd=str(BASE_DIR),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=30,
        )
        output = result.stdout.strip()
        print(output)
        if result.returncode != 0:
            print("[health] Health-check finalizo con codigo distinto de 0.")
            return False
        return True
    except subprocess.TimeoutExpired:
        print("[health] Timeout en health-check (>30s).")
        return False
    except Exception as e:
        print(f"[health] Error ejecutando health-check: {e}")
        return False


def launch():
    if not check_python():
        return 2
    missing_required, missing_optional = check_core_deps()
    if missing_required:
        print(f"[start] Faltan dependencias requeridas: {', '.join(missing_required)}")
        print(f"[start] Instalalas con: pip install {' '.join(missing_required)}")
        return 3
    if missing_optional:
        print(f"[start] Dependencias opcionales faltantes: {', '.join(missing_optional)}")
        print("[start] Podés instalarlas, pero Kitian arrancará en modo reducido.")

    if not run_health_quick():
        proceed = input("[start] El health-check reportó problemas. Igual arrancar? (s/N): ").strip().lower()
        if proceed != "s":
            print("[start] abortado.")
            return 4

    if not ENTRY.exists():
        print(f"[start] No se encontró {ENTRY}")
        return 5

    print(f"[start] Arrancando Kitian...")
    os.chdir(str(BASE_DIR))
    sys.exit(subprocess.run([sys.executable, str(ENTRY)]).returncode)


if __name__ == "__main__":
    sys.exit(launch())

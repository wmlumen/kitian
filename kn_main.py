import sys
import logging
import threading
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from kitian.state import state
from kitian.audio import hablar, load_whisper


def init_keyboard():
    listening_flag = False
    try:
        import keyboard
        def activar():
            nonlocal listening_flag
            listening_flag = True
        keyboard.add_hotkey("ctrl+space", activar)
        logging.getLogger("kitian").info("Hotkey Ctrl+Space registrada")
        return True
    except ImportError:
        logging.getLogger("kitian").info("Libreria keyboard no instalada (pip install keyboard)")
        return False


def dispatcher_local(comando):
    cl = comando.lower().strip()
    # Placeholder simplificado: delegar a lógica existente o futuros comandos
    return None


def procesar(comando):
    # Placeholder simple para entrypoint delgado
    respuesta = dispatcher_local(comando)
    if respuesta:
        hablar(respuesta)
        return
    hablar("Comando recibido, pero el dispatcher completo todavia esta en migracion.")


def main():
    log = logging.getLogger("kitian")
    logging.basicConfig(level=logging.INFO)
    try:
        load_whisper()
    except Exception:
        pass
    try:
        state.start_session()
    except Exception as e:
        log.warning("No pude iniciar sesion core: %s", e)
    worker = threading.Thread(target=lambda: None, daemon=True)
    worker.start()
    try:
        from kitian_hud import run_hud
        run_hud(state)
    except Exception as e:
        log.warning("HUD no disponible: %s", e)


if __name__ == "__main__":
    main()

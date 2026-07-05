import logging
import signal
import sys
import threading
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from kitian.config import config, current_model
from kitian.state import state
from kitian.audio import hablar, load_whisper, escuchar_comando, escuchar_continuo
from kitian.dispatcher import dispatcher_local, procesar


log = logging.getLogger("kitian")
BASE_DIR = Path(__file__).resolve().parent.parent


def main():
    logging.basicConfig(level=logging.INFO)
    log.info("Iniciando Kitian | backend=%s | modelo=%s", config.get("backend"), current_model)
    try:
        load_whisper()
    except Exception as e:
        log.warning("No pude cargar Whisper: %s", e)

    state.start_session()
    try:
        hablar("Sistema Kitian operativo.", blocking=True)
    except Exception as e:
        log.warning("Error voz inicial: %s", e)
    state.set("Activo", state.COLORES["activo"])

    try:
        while True:
            resultado = escuchar_continuo()
            if resultado:
                tipo, comando = resultado
                if comando:
                    procesar(comando)
    except KeyboardInterrupt:
        pass
    finally:
        try:
            state.end_session()
        except Exception as e:
            log.warning("Error al cerrar sesion: %s", e)
        log.info("Kitian detenido")


if __name__ == "__main__":
    main()

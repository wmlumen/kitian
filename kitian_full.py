from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))

import logging
import threading
import time

from kitian.config import config, current_model
from kitian.state import state
from kitian.audio import load_whisper, escuchar_comando, escuchar_continuo
try:
    from kitian.audio import hablar
except Exception:
    try:
        from kitian.audio import hablar as _fallback_hablar
        hablar = _fallback_hablar
    except Exception:
        hablar = None
from kitian.dispatcher import dispatcher_local, procesar

try:
    from kitian.http import start_http_server as _start_http_server
    _HAS_HTTP = True
except Exception:
    _HAS_HTTP = False

try:
    import subprocess as _subprocess
    _HAVE_SUBPROCESS = True
except Exception:
    _HAVE_SUBPROCESS = False

log = logging.getLogger("kitian")


def init_keyboard():
    listening_flag = False
    try:
        import keyboard

        def activar():
            nonlocal listening_flag
            listening_flag = True

        keyboard.add_hotkey("ctrl+space", activar)
        log.info("Hotkey Ctrl+Space registrada")
        return True
    except ImportError:
        log.info("Libreria keyboard no instalada")
        return False


def main():
    logging.basicConfig(level=logging.INFO)
    log.info("Iniciando Kitian | backend=%s | modelo=%s", config.get("backend"), current_model)
    try:
        load_whisper()
        log.info("Whisper listo")
    except Exception as e:
        log.warning("Whisper no disponible: %s", e)

    try:
        state.start_session()
        log.info("Sesion iniciada")
    except Exception as e:
        log.debug("start_session omitido: %s", e)

    try:
        hablar("Sistema Kitian operativo.", blocking=True)
    except Exception as e:
        log.warning("Error voz inicial: %s", e)

    estado = state.COLORES.get("activo", "#00ffff")
    try:
        state.set("Activo", estado)
        log.info("Estado: %s", estado)
    except Exception:
        pass

    kb_ok = init_keyboard()
    http_server = None
    if _HAS_HTTP:
        try:
            http_server = _start_http_server()
            if http_server is not None:
                log.info("HTTP hubbed listo en http://%s:%s", http_server[0], http_server[1])
            else:
                log.info("HTTP hubbed listo")
        except Exception as e:
            log.error("HTTP bind failed: %s", e)

    log.info("Kitian activo, esperando interaccion...")
    try:
        while True:
            activated = False
            if kb_ok:
                try:
                    import keyboard
                    if getattr(keyboard, "_kitian_flag", False):
                        keyboard._kitian_flag = False
                        activated = True
                except Exception:
                    pass
            if not activated:
                resultado = None
                try:
                    resultado = escuchar_continuo("wakeword")
                except Exception as e:
                    log.debug("wakeword: %s", e)
                if not resultado:
                    try:
                        time.sleep(0.5)
                        resultado = escuchar_continuo()
                    except Exception as e:
                        log.debug("escucha_continuo: %s", e)
                if resultado:
                    tipo, comando = resultado
                    if comando:
                        try:
                            procesar(comando)
                        except Exception as e:
                            log.error("procesar: %s", e)
    except KeyboardInterrupt:
        log.info("Interrumpido por usuario")
    finally:
        try:
            state.end_session()
        except Exception as e:
            log.warning("Error al cerrar sesion: %s", e)
    log.info("Kitian detenido")


if __name__ == "__main__":
    main()

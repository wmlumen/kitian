"""
KITIAN — Lanzador principal unificado
Arranca todo: HUD visual, voz, escucha por micrófono,
servidor HTTP y dispatcher completo.
"""
from pathlib import Path
import sys
import logging
import threading
import time

# Asegurar que el directorio raíz esté en el PATH
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("kitian")

# ─── 1. Importaciones del núcleo ─────────────────────────────────────────────
from kitian.config import config, current_model
from kitian.state import state
from kitian.audio import load_whisper, hablar, escuchar_continuo
from kitian.dispatcher import procesar


# ─── 2. Inicialización del estado ────────────────────────────────────────────
def _init_state():
    try:
        state.start_session()
    except AttributeError:
        pass  # start_session es opcional
    state.set("Activo", state.COLORES.get("activo", "#00ffff"))
    log.info("Estado inicializado: Activo")


# ─── 3. Hilo de voz y escucha ────────────────────────────────────────────────
def _worker_voz():
    """Hilo que escucha continuamente y despacha comandos."""
    log.info("Hilo de voz arrancado — esperando comandos...")
    state.set("Escuchando", state.COLORES.get("escuchando", "#00cc66"))
    while True:
        try:
            texto = escuchar_continuo()
            if texto:
                if isinstance(texto, tuple):
                    _, texto = texto
                if texto:
                    log.info("Comando recibido: %s", texto)
                    state.set("Pensando", state.COLORES.get("pensando", "#ffcc00"))
                    try:
                        procesar(texto)
                    except Exception as e:
                        log.error("Error al procesar comando: %s", e)
                    state.set("Escuchando", state.COLORES.get("escuchando", "#00cc66"))
        except Exception as e:
            log.debug("escuchar_continuo: %s", e)
            time.sleep(0.5)


# ─── 4. Hilo del servidor HTTP ───────────────────────────────────────────────
def _worker_http():
    """Inicia el servidor HTTP standalone en segundo plano."""
    try:
        import kitian_http_standalone_real as _srv
        import socket as _socket
        from http.server import HTTPServer

        bind_host = "0.0.0.0"
        port = int(__import__("os").environ.get("KITIAN_PORT", "8080"))
        try:
            server = HTTPServer((bind_host, port), _srv.Handler)
            server.socket.setsockopt(_socket.SOL_SOCKET, _socket.SO_REUSEADDR, 1)
            log.info("Servidor HTTP activo → http://localhost:%s/", port)
            server.serve_forever()
        except OSError as e:
            log.warning("Puerto %s ocupado, HTTP no iniciado: %s", port, e)
    except Exception as e:
        log.warning("HTTP standalone no pudo iniciarse: %s", e)


# ─── 5. Hotkey Ctrl+Space ────────────────────────────────────────────────────
def _init_hotkey():
    try:
        import keyboard

        def _activar():
            log.info("Ctrl+Space activado")
            state.set("Escuchando", state.COLORES.get("escuchando", "#00cc66"))

        keyboard.add_hotkey("ctrl+space", _activar)
        log.info("Hotkey Ctrl+Space registrada")
    except Exception:
        log.info("Libreria keyboard no disponible (pip install keyboard)")


# ─── 6. Main ─────────────────────────────────────────────────────────────────
def main():
    log.info("=" * 55)
    log.info("  KI-TIAN X20 — Arranque completo")
    log.info("  Backend: %-10s  Modelo: %s", config.get("backend"), current_model)
    log.info("=" * 55)

    # Cargar Whisper en segundo plano (no bloquea el HUD)
    threading.Thread(target=load_whisper, daemon=True, name="whisper-load").start()

    # Inicializar estado
    _init_state()

    # Hotkey
    _init_hotkey()

    # Servidor HTTP en segundo plano
    threading.Thread(target=_worker_http, daemon=True, name="http-server").start()

    # Voz inicial (no bloquea el HUD — en hilo separado)
    threading.Thread(
        target=lambda: hablar("Sistema Kitian operativo.", blocking=True),
        daemon=True,
        name="voz-inicio",
    ).start()

    # Worker de escucha en segundo plano
    threading.Thread(target=_worker_voz, daemon=True, name="voz-worker").start()

    # HUD — debe correr en el hilo principal (Tkinter)
    log.info("Iniciando HUD visual...")
    try:
        from kitian_hud import run_hud
        run_hud(state)
    except Exception as e:
        log.error("HUD no pudo iniciarse: %s", e)
        log.info("Kitian corriendo en modo texto. Presiona Ctrl+C para salir.")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            pass

    log.info("Kitian detenido.")


if __name__ == "__main__":
    main()

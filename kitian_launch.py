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


# ─── 3. Hilo de voz y escucha (Desactivado por sobrecalentamiento) ──────────────
# La escucha ahora se activa únicamente mediante la tecla de acceso rápido.


# ─── 4. Hilo del servidor HTTP ───────────────────────────────────────────────
def _worker_http():
    """Inicia el servidor HTTP standalone en segundo plano."""
    try:
        import kitian_http_standalone_real as _srv
        import socket as _socket
        from http.server import HTTPServer, ThreadingHTTPServer

        bind_host = "0.0.0.0"
        port = int(__import__("os").environ.get("KITIAN_PORT", "8080"))
        try:
            server = ThreadingHTTPServer((bind_host, port), _srv.Handler)
            server.socket.setsockopt(_socket.SOL_SOCKET, _socket.SO_REUSEADDR, 1)
            log.info("Servidor HTTP activo → http://localhost:%s/", port)
            server.serve_forever()
        except OSError as e:
            log.warning("Puerto %s ocupado, HTTP no iniciado: %s", port, e)
    except Exception as e:
        log.warning("HTTP standalone no pudo iniciarse: %s", e)


# ─── 5. Hotkey Espacio (Push-to-Talk) ─────────────────────────────────────────
def _init_hotkey():
    try:
        import keyboard
        import threading
        from kitian.audio import escuchar_comando
        from kitian.dispatcher import procesar

        def _listen_task():
            log.info("Escuchando comando (activado por Espacio)...")
            try:
                texto = escuchar_comando(timeout=8)
                if isinstance(texto, tuple):
                    _, texto = texto
                if texto:
                    log.info("Comando recibido: %s", texto)
                    state.set("Pensando", state.COLORES.get("pensando", "#ffcc00"))
                    procesar(texto)
                state.set("Activo", state.COLORES.get("activo", "#00ffff"))
            except Exception as e:
                log.error("Error al procesar comando por voz: %s", e)
                state.set("Activo", state.COLORES.get("activo", "#00ffff"))

        def _activar():
            # Evitar lanzar multiples hilos si ya esta escuchando
            if state.get("Escuchando") == state.COLORES.get("escuchando", "#00cc66"):
                return
            state.set("Escuchando", state.COLORES.get("escuchando", "#00cc66"))
            threading.Thread(target=_listen_task, daemon=True).start()

        keyboard.add_hotkey("ctrl+space", _activar)
        log.info("Hotkey 'Ctrl+Espacio' registrada para escuchar comandos")
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
        target=lambda: hablar("Sistema Kitian operativo. Presiona Control más Espacio para hablar.", blocking=True),
        daemon=True,
        name="voz-inicio",
    ).start()

    # Worker de escucha continuo desactivado (usar espacio para hablar)
    # threading.Thread(target=_worker_voz, daemon=True, name="voz-worker").start()

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

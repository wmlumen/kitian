import threading
import socket
import json
import time
import os
import platform
import subprocess
from http.server import HTTPServer, BaseHTTPRequestHandler

HOST_CANDIDATE = "192.168.243.129"
PORT = 8080


def _bind_address(preferred):
    if preferred:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.bind((preferred, 0))
            s.close()
            return preferred
        except OSError:
            pass
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "0.0.0.0"


BIND_HOST = _bind_address(HOST_CANDIDATE)


def _get_system_metrics():
    """Collect system metrics for the API."""
    try:
        import psutil
        cpu = psutil.cpu_percent(interval=0.1)
        ram = psutil.virtual_memory().percent
        disk = psutil.disk_usage('C:\\' if platform.system() == 'Windows' else '/').percent
        net = psutil.net_io_counters()
        fps = 30  # Default, actualizado por el HUD si está corriendo
        return {
            "cpu": round(cpu, 1),
            "ram": round(ram, 1),
            "disk": round(disk, 1),
            "net_up": "0 KB/s",
            "net_down": "0 KB/s",
            "fps": fps,
            "ip": socket.gethostbyname(socket.gethostname()),
            "os": platform.system(),
            "uptime": int(time.time()),
        }
    except ImportError:
        return {
            "cpu": 0,
            "ram": 0,
            "disk": 0,
            "net_up": "N/A",
            "net_down": "N/A",
            "fps": 0,
            "ip": socket.gethostbyname(socket.gethostname()),
            "os": platform.system(),
            "uptime": int(time.time()),
        }


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass

    def _send(self, status, body):
        payload = json.dumps(body, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Cache-Control", "no-store")
        self._cors_headers()
        self.end_headers()
        self.wfile.write(payload)
        return True

    def do_GET(self):
        if self.path == "/api/status":
            return self._send(200, {
                "status": "ok",
                "service": "kitian-http",
                "binding": f"http://{BIND_HOST}:{PORT}/"
            })
        
        if self.path == "/api/system":
            return self._send(200, _get_system_metrics())
        
        if self.path in ("/", "/index.html", "/nebula"):
            try:
                html_path = os.path.join(os.path.dirname(__file__), "nebula_web.html")
                with open(html_path, "r", encoding="utf-8") as f:
                    html = f.read()
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(html.encode('utf-8'))))
                self.end_headers()
                self.wfile.write(html.encode('utf-8'))
                return
            except FileNotFoundError:
                return self._send(404, {"error": "nebula_web.html not found"})

        if self.path == "/api/hermes/chat":
            length = int(self.headers.get("Content-Length", "0") or "0")
            body = self.rfile.read(length).decode("utf-8", errors="replace") if length else "{}"
            try:
                data = json.loads(body)
            except json.JSONDecodeError:
                return self._send(400, {"error": "json invalido"})
            mensaje = (data.get("mensaje") or "").strip()
            if not mensaje:
                return self._send(400, {"error": "mensaje vacio"})
            respuesta = _ejecutar_hermes_chat(mensaje)
            return self._send(200, {"mensaje": mensaje, "respuesta": respuesta})

        if self.path == "/api/hermes/status":
            hermes_ok = _check_hermes_available()
            return self._send(200, {
                "hermes_available": hermes_ok,
                "service": "kitian-http",
                "binding": f"http://{BIND_HOST}:{PORT}/"
            })

        return self._send(404, {"error": "not found"})

    def do_POST(self):
        length = int(self.headers.get("Content-Length", "0") or "0")
        body = self.rfile.read(length).decode("utf-8", errors="replace") if length else "{}"
        try:
            data = json.loads(body)
        except json.JSONDecodeError:
            return self._send(400, {"error": "json invalido"})
        comando = (data.get("comando") or "").strip()
        if not comando:
            return self._send(400, {"error": "comando vacio"})

        respuesta = None
        try:
            import sys
            sys.path.insert(0, os.path.dirname(__file__))
            from kitian.dispatcher import dispatcher_local
            respuesta = dispatcher_local(comando)
        except Exception:
            pass

        if not respuesta:
            respuesta = _ejecutar_hermes_chat(comando)

        return self._send(200, {
            "comando": comando,
            "respuesta": respuesta or "No pude procesar ese comando.",
            "via": "kitian" if respuesta and not respuesta.startswith("[") else "hermes",
        })


def start_server():
    server = HTTPServer((BIND_HOST, PORT), Handler)
    server.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    thread = threading.Thread(target=server.serve_forever, name="kitian-http", daemon=True)
    thread.start()
    print(f"NEBULA HTTP activo en http://{BIND_HOST}:{PORT}/")
    print("Panel nebulosa: /nebula")
    print("API sistema: /api/system")
    print("Presiona Ctrl+C o cierra esta ventana para detener.")
    return server


def _check_hermes_available():
    try:
        result = subprocess.run(
            ["hermes", "chat", "-q", "hola", "--quiet"],
            capture_output=True, text=True, timeout=15,
            env={**os.environ, "TERM": "dumb"}
        )
        return result.returncode == 0 and any(
            x in result.stdout.lower() for x in ["hola", "ayudar", "ayuda", "en qué puedo"]
        )
    except Exception:
        return False


def _ejecutar_hermes_chat(mensaje):
    try:
        safe_msg = mensaje.replace('"', '\\"').replace("`", "\\`")
        cmd = ["hermes", "chat", "-q", safe_msg, "--quiet"]
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=60,
            env={**os.environ, "TERM": "dumb", "PYTHONUNBUFFERED": "1"}
        )
        stdout = result.stdout.strip()
        if stdout.startswith("session_id:"):
            stdout = stdout.split("\n", 1)[1].strip()
        if not stdout and result.stderr:
            stderr = result.stderr.strip()
            if stderr:
                stdout = f"[Hermes stderr] {stderr[:300]}"
        if not stdout:
            return "[Hermes no devolvio respuesta visible]"
        return stdout[:2000]
    except subprocess.TimeoutExpired:
        return "[Timeout: Hermes tardo mas de 60s en responder]"
    except FileNotFoundError:
        return "[Error: comando 'hermes' no encontrado en PATH]"
    except Exception as e:
        return f"[Error ejecutando Hermes: {e}]"


if __name__ == "__main__":
    server = start_server()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nDeteniendo servidor...")
        server.shutdown()
        print("Servidor detenido.")
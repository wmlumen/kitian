"""KI-TIAN HTTP Standalone Server — Auto-detect IP, métricas de red, CORS, health."""
import threading
import socket
import json
import time
import os
import platform
import subprocess
import shlex
from http.server import HTTPServer, BaseHTTPRequestHandler
import http.client

# ---------- Auto-detect best local IP ----------
def _detect_local_ip():
    """Detecta la IP local más accesible de la máquina."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        try:
            return socket.gethostbyname(socket.gethostname())
        except Exception:
            return "0.0.0.0"


HOST = _detect_local_ip()
PORT = int(os.environ.get("KITIAN_PORT", "8080"))

_voice_bridge = None

# ---------- Métricas del sistema ----------
_last_net = {"recv": 0, "sent": 0, "time": 0.0}
_start_time = time.time()


def _get_system_metrics():
    try:
        import psutil
        cpu = psutil.cpu_percent(interval=0.1)
        ram = psutil.virtual_memory()
        disk = psutil.disk_usage('C:\\' if platform.system() == 'Windows' else '/').percent

        # Métricas de red en vivo
        now = time.time()
        net = psutil.net_io_counters()
        dt = max(now - _last_net["time"], 0.01) if _last_net["time"] > 0 else 1.0
        dr = max(0, net.bytes_recv - _last_net["recv"]) if _last_net["recv"] > 0 else 0
        ds = max(0, net.bytes_sent - _last_net["sent"]) if _last_net["sent"] > 0 else 0
        _last_net["recv"] = net.bytes_recv
        _last_net["sent"] = net.bytes_sent
        _last_net["time"] = now

        def fmt_rate(bps):
            rate = bps / dt
            if rate >= 1024 * 1024:
                return f"{rate / (1024 * 1024):.1f} MB/s"
            return f"{rate / 1024:.1f} KB/s"

        # Batería
        bat = psutil.sensors_battery()
        bat_info = {"percent": bat.percent, "plugged": bat.power_plugged} if bat else None

        return {
            "cpu": round(cpu, 1),
            "ram": round(ram.percent, 1),
            "ram_used_gb": round(ram.used / (1024**3), 1),
            "ram_total_gb": round(ram.total / (1024**3), 1),
            "disk": round(disk, 1),
            "net_down": fmt_rate(dr),
            "net_up": fmt_rate(ds),
            "net_recv_bytes": net.bytes_recv,
            "net_sent_bytes": net.bytes_sent,
            "fps": 30,
            "ip": HOST,
            "os": platform.system(),
            "hostname": socket.gethostname(),
            "cpu_count": psutil.cpu_count(logical=True),
            "uptime": int(time.time() - _start_time),
            "battery": bat_info,
            "timestamp": time.time(),
        }
    except ImportError:
        return {
            "cpu": 0, "ram": 0, "disk": 0,
            "net_down": "N/A", "net_up": "N/A",
            "fps": 0, "ip": HOST,
            "os": platform.system(),
            "uptime": int(time.time() - _start_time),
            "timestamp": time.time(),
        }


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        # Solo loguear errores, no cada request
        if args and str(args[1]).startswith(("4", "5")):
            print(f"[HTTP] {args[0]} {args[1]}")

    def _cors_headers(self):
        """Agrega headers CORS para acceso desde cualquier origen."""
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def _send_json(self, status, body):
        payload = json.dumps(body, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Cache-Control", "no-store")
        self._cors_headers()
        self.end_headers()
        self.wfile.write(payload)

    def _send_html(self, html_bytes, status=200):
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(html_bytes)))
        self.send_header("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0")
        self.send_header("Pragma", "no-cache")
        self.send_header("Expires", "0")
        self._cors_headers()
        self.end_headers()
        self.wfile.write(html_bytes)

    def _voice_target_url(self):
        return f"http://localhost:8082{self.path}"

    def _handle_voice_proxy(self):
        try:
            from urllib.parse import urlparse
            parsed = urlparse(self._voice_target_url())
            host = parsed.hostname or "localhost"
            port = parsed.port or 8082
            conn = http.client.HTTPConnection(host, port, timeout=20)
            length = int(self.headers.get("Content-Length", "0") or "0")
            body = self.rfile.read(length) if length else b""
            headers = {k: v for k, v in self.headers.items() if k.lower() not in {"host", "content-length"}}
            conn.request(self.command, parsed.path, body, headers)
            resp = conn.getresponse()
            payload = resp.read() or b"{}"
            return self._send_json(resp.status, json.loads(payload.decode("utf-8", errors="replace")))
        except Exception as e:
            return self._send_json(502, {"error": f"voice proxy error: {e}"})

    def do_OPTIONS(self):
        self.send_response(204)
        self._cors_headers()
        self.end_headers()

    def do_GET(self):
        if self.path == "/api/status":
            return self._send_json(200, {
                "status": "ok",
                "service": "kitian-http-standalone",
                "binding": f"http://{HOST}:{PORT}/",
                "uptime": int(time.time() - _start_time),
            })

        if self.path == "/api/emotional":
            try:
                from kitian.state import state as _state
                emo = _state.get_emotional_state()
                payload = {
                    "claridad": float(emo.get("claridad", 85) or 85),
                    "carga": float(emo.get("carga", 15) or 15),
                    "riesgo": str(emo.get("riesgo", "Bajo") or "Bajo"),
                    "entropia": float(emo.get("entropia", 20) or 20),
                }
            except Exception:
                payload = {"claridad": 85.0, "carga": 15.0, "riesgo": "Bajo", "entropia": 20.0}
            return self._send_json(200, payload)

        if self.path == "/api/profile":
            try:
                from kitian.state import state as _state
                session = getattr(_state, "get_session_stats", lambda: {})()
                payload = {
                    "profile": {
                        "interactions": session.get("interactions", 0),
                        "top_keywords": session.get("keywords", [])[:5],
                        "active_goal": session.get("activeGoal"),
                    }
                }
            except Exception:
                payload = {"profile": {"interactions": 0, "top_keywords": [], "active_goal": None}}
            return self._send_json(200, payload)

        if self.path == "/api/ai-status":
            try:
                items = []
                import psutil
                keywords = ["llamado", "python", "whisper", "openai", "ollama", "vllm", "telegram", "node", "server", "model"]
                for p in psutil.process_iter(["pid", "name", "cpu_percent", "cmdline"]):
                    try:
                        cmd = " ".join((p.info.get("cmdline") or [])).lower()
                        name = (p.info.get("name") or "").lower()
                        if any(k in name or k in cmd for k in keywords):
                            items.append({
                                "pid": p.info.get("pid"),
                                "name": p.info.get("name"),
                                "cpu": p.info.get("cpu_percent") or 0.0,
                                "command": " ".join((p.info.get("cmdline") or [])),
                                "matched_keyword": next((k for k in keywords if k in name or k in cmd), "other"),
                            })
                    except Exception:
                        pass
                payload = {"ai_processes": items[:20]}
            except Exception as e:
                payload = {"ai_processes": []}
            return self._send_json(200, payload)

        if self.path == "/api/system":
            return self._send_json(200, _get_system_metrics())

        if self.path == "/api/health":
            metrics = _get_system_metrics()
            health = "ok"
            issues = []
            if metrics.get("cpu", 0) > 90:
                health = "degraded"
                issues.append(f"CPU alto: {metrics['cpu']}%")
            if metrics.get("ram", 0) > 92:
                health = "degraded"
                issues.append(f"RAM alta: {metrics['ram']}%")
            if metrics.get("disk", 0) > 95:
                health = "critical"
                issues.append(f"Disco lleno: {metrics['disk']}%")
            return self._send_json(200, {
                "health": health,
                "issues": issues,
                "metrics_summary": {
                    "cpu": metrics.get("cpu"),
                    "ram": metrics.get("ram"),
                    "disk": metrics.get("disk"),
                },
            })

        if self.path == "/api/hermes/status":
            hermes_ok = _check_hermes_available()
            return self._send_json(200, {
                "hermes_available": hermes_ok,
                "service": "kitian-http-standalone",
                "binding": f"http://{HOST}:{PORT}/",
            })

        if self.path == "/api/hermes/chat":
            length = int(self.headers.get("Content-Length", "0") or "0")
            body = self.rfile.read(length).decode("utf-8", errors="replace") if length else "{}"
            try:
                data = json.loads(body)
            except json.JSONDecodeError:
                return self._send_json(400, {"error": "json invalido"})
            mensaje = (data.get("mensaje") or "").strip()
            if not mensaje:
                return self._send_json(400, {"error": "mensaje vacio"})
            worker = (data.get("worker") or "").strip().lower() or None
            try:
                from kitian.multiagent import handle, call
                payload = handle(mensaje) if worker is None else call(mensaje, worker=worker)
            except Exception as e:
                payload = {"ok": False, "error": str(e)}
            return self._send_json(200 if payload.get("ok") else 500, {
                "mensaje": mensaje,
                "respuesta": payload.get("text", ""),
                "worker": payload.get("worker"),
                "model": payload.get("model"),
                "backend": payload.get("backend"),
                "error": payload.get("error"),
            })

        if self.path in ("/api/voice/status", "/api/voice/status/"):
            try:
                import http.client
                from urllib.parse import urlparse
                parsed = urlparse(f"http://localhost:8082{self.path}")
                conn = http.client.HTTPConnection("localhost", 8082, timeout=5)
                conn.request("GET", parsed.path)
                resp = conn.getresponse()
                payload = resp.read() or b"{}"
                return self._send_json(resp.status, json.loads(payload.decode("utf-8", errors="replace")))
            except Exception as e:
                return self._send_json(200, {"voice": {}, "inputs": {}, "error": str(e)})

        if self.path in ("/", "/index.html", "/nebula"):
            try:
                base_dir = os.path.dirname(os.path.abspath(__file__))
                html_path = os.path.join(base_dir, "nebula_web.html")
                with open(html_path, "r", encoding="utf-8") as f:
                    html = f.read()
                return self._send_html(html.encode("utf-8"))
            except FileNotFoundError:
                return self._send_json(404, {"error": "nebula_web.html not found"})

        if self.path in ("/dashboard", "/health-dashboard", "/reports"):
            try:
                base_dir = os.path.dirname(os.path.abspath(__file__))
                html_path = os.path.join(base_dir, "kitian_health_dashboard.html")
                with open(html_path, "r", encoding="utf-8") as f:
                    html = f.read()
                return self._send_html(html.encode("utf-8"))
            except FileNotFoundError:
                return self._send_json(404, {"error": "kitian_health_dashboard.html not found"})

        if self.path in ("/kitian_health.json", "/nebula/kitian_health.json"):
            try:
                base_dir = os.path.dirname(os.path.abspath(__file__))
                json_path = os.path.join(base_dir, "kitian_health.json")
                with open(json_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                return self._send_json(200, data)
            except FileNotFoundError:
                return self._send_json(404, {"error": "kitian_health.json not found"})
            except Exception as e:
                return self._send_json(500, {"error": f"Failed to load health json: {e}"})

        return self._send_json(404, {"error": "not found", "available": ["/", "/nebula", "/dashboard", "/reports", "/api/system", "/api/status", "/api/health"]})

    def do_POST(self):
        if self.path == "/api/command":
            length = int(self.headers.get("Content-Length", "0") or "0")
            body = self.rfile.read(length).decode("utf-8", errors="replace") if length else "{}"
            try:
                data = json.loads(body)
            except json.JSONDecodeError:
                return self._send_json(400, {"error": "json invalido"})
            comando = (data.get("comando") or "").strip()
            if not comando:
                return self._send_json(400, {"error": "comando vacio"})
            try:
                import sys
                sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
                from kitian.dispatcher import dispatcher_local
                respuesta = dispatcher_local(comando)
            except Exception as e:
                respuesta = f"Error: {e}"
            return self._send_json(200, {"comando": comando, "respuesta": respuesta})

        if self.path in ("/api/voice/interact", "/api/voice/interact/",
                        "/api/voice/push-to-talk", "/api/voice/push-to-talk/",
                        "/api/voice/wakeword-toggle", "/api/voice/wakeword-toggle/",
                        "/api/voice/speak", "/api/voice/speak/"):
            return self._handle_voice_proxy()

        if self.path == "/api/backend/status":
            try:
                from kitian.multiagent import backend_status
                return self._send_json(200, backend_status())
            except Exception as e:
                return self._send_json(500, {"error": str(e)})

        if self.path == "/api/multiagent/chat":
            length = int(self.headers.get("Content-Length", "0") or "0")
            body = self.rfile.read(length).decode("utf-8", errors="replace") if length else "{}"
            try:
                data = json.loads(body)
            except json.JSONDecodeError:
                return self._send_json(400, {"error": "json invalido"})
            mensaje = (data.get("mensaje") or "").strip()
            if not mensaje:
                return self._send_json(400, {"error": "mensaje vacio"})
            worker = (data.get("worker") or "").strip().lower() or None
            backend = (data.get("backend") or "").strip().lower() or None
            if backend == "auto":
                backend = None
            try:
                from kitian.multiagent import handle, call
                if backend or worker:
                    backend_out = backend or "gemini"
                    payload = call(mensaje, worker=worker or "chat", model=None, backend=backend_out)
                else:
                    payload = handle(mensaje, preferred_backend=backend)
            except Exception as e:
                payload = {"ok": False, "error": str(e)}
            return self._send_json(200 if payload.get("ok") else 500, {
                "ok": payload.get("ok"),
                "worker": payload.get("worker"),
                "model": payload.get("model"),
                "backend": payload.get("backend"),
                "text": payload.get("text", ""),
                "error": payload.get("error"),
            })

        if self.path == "/api/browser/start":
            try:
                from kitian.browser_nav import _browser
                resp = _browser.start()
                return self._send_json(200 if resp.get("ok") else 500, resp)
            except Exception as e:
                return self._send_json(500, {"error": str(e)})

        if self.path == "/api/browser/stop":
            try:
                from kitian.browser_nav import _browser
                _browser.stop()
                return self._send_json(200, {"ok": True})
            except Exception as e:
                return self._send_json(500, {"error": str(e)})

        if self.path == "/api/browser/navigate":
            length = int(self.headers.get("Content-Length", "0") or "0")
            body = self.rfile.read(length).decode("utf-8", errors="replace") if length else "{}"
            try:
                data = json.loads(body)
            except json.JSONDecodeError:
                return self._send_json(400, {"error": "json invalido"})
            url = (data.get("url") or "").strip()
            if not url:
                return self._send_json(400, {"error": "url vacia"})
            try:
                from kitian.browser_nav import _browser
                resp = _browser.navigate(url)
                return self._send_json(200 if resp.get("ok") else 500, resp)
            except Exception as e:
                return self._send_json(500, {"error": str(e)})

        if self.path == "/api/browser/snapshot":
            try:
                from kitian.browser_nav import _browser
                resp = _browser.snapshot()
                return self._send_json(200 if resp.get("ok") else 500, resp)
            except Exception as e:
                return self._send_json(500, {"error": str(e)})

        if self.path == "/api/browser/click":
            length = int(self.headers.get("Content-Length", "0") or "0")
            body = self.rfile.read(length).decode("utf-8", errors="replace") if length else "{}"
            try:
                data = json.loads(body)
            except json.JSONDecodeError:
                return self._send_json(400, {"error": "json invalido"})
            ref = (data.get("ref") or "").strip()
            if not ref:
                return self._send_json(400, {"error": "ref vacio"})
            try:
                from kitian.browser_nav import _browser
                resp = _browser.click(ref)
                return self._send_json(200 if resp.get("ok") else 500, resp)
            except Exception as e:
                return self._send_json(500, {"error": str(e)})

        if self.path == "/api/browser/type":
            length = int(self.headers.get("Content-Length", "0") or "0")
            body = self.rfile.read(length).decode("utf-8", errors="replace") if length else "{}"
            try:
                data = json.loads(body)
            except json.JSONDecodeError:
                return self._send_json(400, {"error": "json invalido"})
            ref = (data.get("ref") or "").strip()
            text = (data.get("text") or "").strip()
            if not ref or not text:
                return self._send_json(400, {"error": "ref o texto vacio"})
            try:
                from kitian.browser_nav import _browser
                resp = _browser.type(ref, text)
                return self._send_json(200 if resp.get("ok") else 500, resp)
            except Exception as e:
                return self._send_json(500, {"error": str(e)})

        if self.path == "/api/browser/press":
            length = int(self.headers.get("Content-Length", "0") or "0")
            body = self.rfile.read(length).decode("utf-8", errors="replace") if length else "{}"
            try:
                data = json.loads(body)
            except json.JSONDecodeError:
                return self._send_json(400, {"error": "json invalido"})
            key = (data.get("key") or "").strip()
            if not key:
                return self._send_json(400, {"error": "key vacia"})
            try:
                from kitian.browser_nav import _browser
                resp = _browser.press(key)
                return self._send_json(200 if resp.get("ok") else 500, resp)
            except Exception as e:
                return self._send_json(500, {"error": str(e)})

        if self.path == "/api/browser/back":
            try:
                from kitian.browser_nav import _browser
                resp = _browser.back()
                return self._send_json(200 if resp.get("ok") else 500, resp)
            except Exception as e:
                return self._send_json(500, {"error": str(e)})

        return self._send_json(404, {"error": "endpoint not found", "available": [
            "/", "/nebula", "/dashboard", "/reports", "/api/system", "/api/status", "/api/health",
            "/api/multiagent/chat", "/api/backend/status",
            "/api/browser/start", "/api/browser/navigate", "/api/browser/snapshot",
            "/api/browser/click", "/api/browser/type", "/api/browser/press", "/api/browser/back"
        ]})



# ---------- Soporte Hermes ----------
def _check_hermes_available():
    try:
        result = subprocess.run(
            ["hermes", "chat", "-q", "hola", "--quiet"],
            capture_output=True, text=True, timeout=15,
            env={**os.environ, "TERM": "dumb"}
        )
        return result.returncode == 0 and "hola" in result.stdout.lower() or "ayudar" in result.stdout.lower()
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


# ---------- Startup ----------
if __name__ == "__main__":
    # Siempre bindear en 0.0.0.0 para acceso local + LAN
    bind_host = "0.0.0.0"
    display_host = HOST  # IP detectada para mostrar al usuario
    try:
        server = HTTPServer((bind_host, PORT), Handler)
    except OSError as e:
        print(f"[HTTP] Error al iniciar servidor: {e}")
        raise

    server.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    print(f"")
    print(f"  +==================================================+")
    print(f"  |  KI-TIAN NEBULOSA HTTP Server                    |")
    print(f"  +==================================================+")
    print(f"  |  Local:      http://localhost:{PORT}/")
    print(f"  |  LAN:        http://{display_host}:{PORT}/")
    print(f"  |  Nebulosa:   http://localhost:{PORT}/nebula")
    print(f"  |  Dashboard:  http://localhost:{PORT}/dashboard")
    print(f"  |  API System: http://localhost:{PORT}/api/system")
    print(f"  |  API Health: http://localhost:{PORT}/api/health")
    print(f"  +==================================================+")
    print(f"  |  Ctrl+C para detener                             |")
    print(f"  +==================================================+")
    print(f"")

    try:
        from kitian.voice_gateway import start_background as _start_voice_gw
        _start_voice_gw()
    except Exception as e:
        print("[VoiceGW] No pude iniciar:", e)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[HTTP] Deteniendo servidor...")
        server.shutdown()
        print("[HTTP] Servidor detenido.")

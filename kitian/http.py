import asyncio
import json
import logging
import socket
import os
import sys
import time
import threading
import platform
from pathlib import Path
from urllib.parse import urlparse, parse_qs, urlencode
from urllib.request import Request, urlopen
from urllib.error import URLError

try:
    import psutil

    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False

log = logging.getLogger("kitian")
BASE_DIR = Path(__file__).resolve().parent.parent
_http_metrics_cache = {"ts": 0.0, "payload": None}
_net_state = {"recv": 0, "sent": 0, "time": 0.0}
_http_start_time = time.time()


def http_get(url: str, params: dict = None, headers: dict = None, timeout: float = 10) -> str:
    """Realiza una petición GET síncrona y devuelve el contenido de texto."""
    if params:
        url = f"{url}?{urlencode(params)}"
    req = Request(url)
    if headers:
        for k, v in headers.items():
            req.add_header(k, v)
    try:
        with urlopen(req, timeout=timeout) as response:
            return response.read().decode("utf-8", errors="replace")
    except URLError as e:
        log.warning("http_get error para %s: %s", url, e)
        raise


def http_get_json(url: str, params: dict = None, headers: dict = None, timeout: float = 10) -> dict:
    """Realiza una petición GET síncrona y devuelve el JSON decodificado."""
    # Asegurar cabecera Accept para JSON
    headers = headers or {}
    if "accept" not in {k.lower() for k in headers.keys()}:
        headers["Accept"] = "application/json"
    res_text = http_get(url, params=params, headers=headers, timeout=timeout)
    return json.loads(res_text)



def _metrics_cache_ttl() -> float:
    try:
        from kitian.config import config as _cfg

        ttl = _cfg.get("http_metrics_cache_ttl")
        return float(ttl or 0.3)
    except Exception:
        return 0.3


def _find_best_local_ip(preferred=None):
    if preferred:
        return preferred
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


def _get_system_metrics():
    now = time.time()
    cached = _http_metrics_cache
    if cached.get("payload") is not None and (now - cached.get("ts", 0.0) < _metrics_cache_ttl()):
        return cached["payload"]
    try:
        import getpass
        username = getpass.getuser()
        hostname = socket.gethostname()
        
        # Procesos y hilos
        procs_count = 0
        threads_count = 0
        if HAS_PSUTIL:
            cpu = psutil.cpu_percent(interval=0)
            ram = psutil.virtual_memory().percent
            disk = psutil.disk_usage("C:\\" if platform.system() == "Windows" else "/").percent
            # Métricas de red en vivo
            net = psutil.net_io_counters()
            dt = max(now - _net_state["time"], 0.01) if _net_state["time"] > 0 else 1.0
            dr = max(0, net.bytes_recv - _net_state["recv"]) if _net_state["recv"] > 0 else 0
            ds = max(0, net.bytes_sent - _net_state["sent"]) if _net_state["sent"] > 0 else 0
            _net_state["recv"] = net.bytes_recv
            _net_state["sent"] = net.bytes_sent
            _net_state["time"] = now
            def fmt(bps):
                r = bps / dt
                return f"{r/(1024*1024):.1f} MB/s" if r >= 1024*1024 else f"{r/1024:.1f} KB/s"
            net_down = fmt(dr)
            net_up = fmt(ds)
            try:
                procs_count = len(psutil.pids())
                threads_count = sum(p.num_threads() for p in psutil.process_iter(['num_threads']))
            except Exception:
                pass
        else:
            cpu, ram, disk = 0.0, 0.0, 0.0
            net_down, net_up = "N/A", "N/A"
            
        uptime_sec = int(now - _http_start_time)
        hrs = uptime_sec // 3600
        mins = (uptime_sec % 3600) // 60
        secs = uptime_sec % 60
        uptime_str = f"{hrs:02d}:{mins:02d}:{secs:02d}"

        payload = {
            "cpu": round(cpu, 1),
            "ram": round(ram, 1),
            "disk": round(disk, 1),
            "net_up": net_up,
            "net_down": net_down,
            "fps": 30,
            "ip": _find_best_local_ip(),
            "os": platform.system(),
            "hostname": hostname,
            "user": username,
            "processes": procs_count or "N/A",
            "threads": threads_count or "N/A",
            "uptime": uptime_str,
            "timestamp": now,
        }
        _http_metrics_cache["payload"] = payload
        _http_metrics_cache["ts"] = now
        return payload
    except Exception:
        uptime_sec = int(now - _http_start_time)
        hrs = uptime_sec // 3600
        mins = (uptime_sec % 3600) // 60
        secs = uptime_sec % 60
        uptime_str = f"{hrs:02d}:{mins:02d}:{secs:02d}"
        import getpass
        return _http_metrics_cache.get("payload") or {
            "cpu": 0, "ram": 0, "disk": 0,
            "net_up": "N/A", "net_down": "N/A",
            "fps": 0, "ip": "127.0.0.1",
            "os": platform.system(),
            "hostname": socket.gethostname(),
            "user": getpass.getuser(),
            "processes": "N/A",
            "threads": "N/A",
            "uptime": uptime_str,
        }


class _KitianHTTPRequest:
    __slots__ = ("reader", "writer", "method", "path", "version", "headers", "body")

    def __init__(self, reader, writer, method, path, version, headers, body=b""):
        self.reader = reader
        self.writer = writer
        self.method = method
        self.path = path
        self.version = version
        self.headers = headers
        self.body = body


class _KitianClient:
    __slots__ = ("reader", "writer", "views", "buffer", "closed")

    def __init__(self, reader, writer):
        self.reader = reader
        self.writer = writer
        self.buffer = bytearray()
        self.closed = False

    async def _send_ws(self, status, content_type, body: bytes, extra_headers=None):
        headers = [
            f"HTTP/1.1 {status} OK\r\n",
            f"Content-Type: {content_type}\r\n",
            f"Content-Length: {len(body)}\r\n",
            "Connection: keep-alive\r\n",
            "Cache-Control: no-store\r\n",
        ]
        if extra_headers:
            headers.extend(extra_headers)
        headers.append("\r\n")
        self.writer.write("".join(headers).encode("ascii") + body)

    async def _write_body_only(self, status, content_type, body: bytes):
        self.writer.write(
            f"HTTP/1.1 {status} OK\r\nContent-Type: {content_type}\r\nContent-Length: {len(body)}\r\nConnection: close\r\n\r\n".encode(
                "ascii"
            )
            + body
        )

    async def _send_json(self, status, payload):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        extra = [("Keep-Alive", "timeout=3, max=200")]
        await self._send_ws(status, "application/json; charset=utf-8", body, extra_headers=extra)

    async def _send_html(self, status, html):
        body = html.encode("utf-8")
        await self._send_ws(status, "text/html; charset=utf-8", body)

    async def handle_request(self, request: _KitianHTTPRequest):
        try:
            if request.path == "/api/system":
                return await self._send_json(200, _get_system_metrics())
            if request.path == "/api/health":
                try:
                    metrics = _get_system_metrics()
                    issues = []
                    cpu = float(metrics.get("cpu", 0) or 0)
                    ram = float(metrics.get("ram", 0) or 0)
                    if cpu > 95:
                        issues.append("CPU alta")
                    if ram > 95:
                        issues.append("RAM alta")
                    return await self._send_json(200, {
                        "health": "ok" if not issues else "degraded",
                        "issues": issues,
                        "metrics_summary": {
                            "cpu": cpu,
                            "ram": ram,
                            "disk": float(metrics.get("disk", 0) or 0),
                        },
                    })
                except Exception as e:
                    return await self._send_json(200, {"health": "degraded", "issues": [str(e)], "metrics_summary": {}})
            if request.path == "/api/status":
                payload = {
                    "status": "ok",
                    "service": "kitian-http-async",
                    "binding": f"http://0.0.0.0:8080/",
                }
                return await self._send_json(200, payload)
            if request.path == "/api/emotional":
                try:
                    from kitian.state import state as _state
                    emo = getattr(_state, "EMOCIONAL", {}) or {}
                    payload = {
                        "claridad": float(emo.get("claridad", 85) or 85),
                        "carga": float(emo.get("carga", 15) or 15),
                        "riesgo": str(emo.get("riesgo", "Bajo") or "Bajo"),
                        "entropia": float(emo.get("entropia", 20) or 20),
                    }
                except Exception:
                    payload = {"claridad": 85.0, "carga": 15.0, "riesgo": "Bajo", "entropia": 20.0}
                return await self._send_json(200, payload)
            if request.path == "/api/profile":
                try:
                    from kitian.state import state as _state
                    profile = getattr(_state, "PERFIL", {}) or {}
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
                return await self._send_json(200, payload)
            if request.path == "/api/ai-status":
                try:
                    items = []
                    try:
                        import psutil
                        keywords = ["llamado", "python", "whisper", "openai", "ollama", "vllm", "telegram", "node", "server", "model"]
                        for p in psutil.process_iter(["pid", "name", "cpu_percent", "cmdline"]):
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
                return await self._send_json(200, payload)
            if (request.method == "GET" and request.path in ("/api/voice/status", "/api/voice/status/")) or (request.method == "POST" and request.path in ("/api/voice/wakeword-toggle", "/api/voice/speak", "/api/voice/push-to-talk", "/api/voice/interact")):
                try:
                    return await self._proxy_voice(request)
                except Exception as e:
                    return await self._send_json(502, {"error": f"voice unavailable: {e}"})
            if request.method == "POST" and request.path == "/api/command":
                data = None
                try:
                    data = json.loads(request.body.decode("utf-8", errors="replace") or "{}")
                except json.JSONDecodeError:
                    return await self._send_json(400, {"error": "json invalido"})
                comando = ((data.get("comando") or "").strip() if isinstance(data, dict) else "").strip()
                if not comando:
                    return await self._send_json(400, {"error": "comando vacio"})
                respuesta = None
                try:
                    from kitian.dispatcher import _handler_http as _h
                    if _h is None:
                        raise RuntimeError("dispatcher http handler missing")
                    respuesta = _h(comando)
                except Exception as e:
                    log.debug("HTTP dispatch error: %s", e)
                    respuesta = f"Error: {e}"
                return await self._send_json(200, {"comando": comando, "respuesta": respuesta})
            html = _load_html("nebula_web.html")
            if request.path in ("/", "/index.html", "/nebula") and html:
                return await self._send_html(200, html)
            await self._send_json(404, {"error": "not found"})
        except Exception as e:
            log.debug("handle_request error: %s", e)
            try:
                await self._send_json(500, {"error": str(e)})
            except Exception:
                pass

    async def drain(self):
        try:
            await self.writer.drain()
        except Exception:
            pass

    async def close(self):
        if self.closed:
            return
        self.closed = True
        try:
            self.writer.close()
        except Exception:
            pass


def _load_html(path):
    try:
        p = BASE_DIR / path
        return p.read_text(encoding="utf-8")
    except Exception:
        return None


async def _accept_client(reader, writer):
    client = _KitianClient(reader=reader, writer=writer)
    try:
        raw = await reader.read(65536)
        if not raw:
            await client.close()
            return
        text = raw.decode("utf-8", errors="replace")
        lines = text.split("\r\n")
        first = lines[0].split(" ")
        method = first[0] if len(first) > 0 else "GET"
        target = first[1] if len(first) > 1 else "/"
        headers = {}
        body = b""
        idx = 1
        while idx < len(lines) and lines[idx]:
            parts = lines[idx].split(":", 1)
            if len(parts) == 2:
                headers[parts[0].strip().lower()] = parts[1].strip()
            idx += 1
        idx += 1
        body = ("\r\n".join(lines[idx:])).encode("utf-8")
        request = _KitianHTTPRequest(
            reader=reader,
            writer=writer,
            method=method,
            path=urlparse(target).path,
            version="HTTP/1.1",
            headers=headers,
            body=body,
        )
        await client.handle_request(request)
        await client.drain()
    except Exception as e:
        log.debug("client error: %s", e)
    finally:
        try:
            await client.close()
        except Exception:
            pass


async def _serve(host: str, port: int):
    server = await asyncio.start_server(_accept_client, host, port)
    addrs = ', '.join(str(s.getsockname()) for s in server.sockets)
    log.info("HTTP activo en async %s", addrs)
    async with server:
        await server.serve_forever()


def start_http_server(host=None, port=8080):
    """Inicia el servidor HTTP asíncrono en un hilo daemon."""
    bind = host or "0.0.0.0"
    _port = int(port)

    def _run():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(_serve(bind, _port))
        except Exception as e:
            log.error("HTTP server error: %s", e)

    t = threading.Thread(target=_run, name="kitian-http-async", daemon=True)
    t.start()
    log.info("HTTP thread iniciado en %s:%s", bind, _port)
    return (bind, _port)


def stop_http_server():
    pass

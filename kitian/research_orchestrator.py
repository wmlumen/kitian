"""Kitian Research Orchestrator — Hermes + Browser sessions (Gemini/GitHub)."""
from __future__ import annotations

import json
import os
import re
import subprocess
import time
import threading
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any


@dataclass
class Finding:
    source: str
    title: str
    body: str
    ts: float = field(default_factory=time.time)


@dataclass
class ResearchState:
    active: bool = False
    minimized: bool = False
    closed: bool = False
    sources: list[str] = field(default_factory=list)
    results: list[dict[str, Any]] = field(default_factory=list)
    query: str = ""
    task_id: str = ""
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "active": self.active,
            "minimized": self.minimized,
            "closed": self.closed,
            "sources": self.sources,
            "results": self.results[-50:],
            "query": self.query,
            "task_id": self.task_id,
            "error": self.error,
        }


class ResearchOrchestrator:
    def __init__(self, notify_cb=None) -> None:
        self.state = ResearchState()
        self._lock = threading.Lock()
        self._worker: threading.Thread | None = None
        self._notify = notify_cb or (lambda ev: None)
        self._history_file = Path("/tmp/kitian_research_history.jsonl")
        self._browser = None

    # ── lifecycle ──
    def start(self, query: str) -> dict[str, Any]:
        with self._lock:
            if self.state.active and not self.state.minimized and not self.state.closed:
                return {"ok": False, "reason": "Ya hay una investigación activa", "state": self.state.to_dict()}
            self.state = ResearchState(active=True, minimized=False, closed=False, query=query, sources=[], results=[], error=None)
            self._persist({"event": "start", "query": query, "ts": time.time()})
        self._ensure_browser()
        self._worker = threading.Thread(target=self._run, args=(query,), daemon=True)
        self._worker.start()
        self._notify({"type": "research:start", "state": self.state.to_dict()})
        return {"ok": True, "state": self.state.to_dict()}

    def pause(self) -> dict[str, Any]:
        with self._lock:
            if not self.state.active:
                return {"ok": False, "reason": "Sin investigación activa"}
            self.state.minimized = True
            self._notify({"type": "research:pause", "state": self.state.to_dict()})
            return {"ok": True, "state": self.state.to_dict()}

    def resume(self) -> dict[str, Any]:
        with self._lock:
            if not self.state.active:
                return {"ok": False, "reason": "Sin investigación activa"}
            if not self.state.minimized and not self.state.closed:
                return {"ok": False, "reason": "Ya está activa"}
            self.state.minimized = False
            self.state.closed = False
            self._notify({"type": "research:resume", "state": self.state.to_dict()})
            return {"ok": True, "state": self.state.to_dict()}

    def close(self) -> dict[str, Any]:
        with self._lock:
            if not self.state.active:
                return {"ok": False, "reason": "Sin investigación activa"}
            self.state.active = False
            self.state.closed = True
            self._notify({"type": "research:close", "state": self.state.to_dict()})
            return {"ok": True, "state": self.state.to_dict()}

    def status(self) -> dict[str, Any]:
        with self._lock:
            return {"ok": True, "state": self.state.to_dict()}

    # ── browser ──
    def _ensure_browser(self) -> None:
        try:
            from browser_use.dom.views import dom  # noqa: F401 (just checks availability)
            self._browser_ok = True
        except Exception:
            self._browser_ok = False
        # Always add hermes as first source
        with self._lock:
            if "hermes" not in self.state.sources:
                self.state.sources.append("hermes")

    def _open_browser(self) -> dict[str, Any]:
        """Try to reuse existing Chrome window with user profile."""
        try:
            chrome_paths = [
                r"C:\Program Files\Google\Chrome\Application\chrome.exe",
                r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
                os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
                "/usr/bin/google-chrome",
                "/usr/bin/chromium-browser",
                "/usr/bin/chromium",
            ]
            chrome = next((p for p in chrome_paths if os.path.exists(p)), None)
            if not chrome:
                # Try `which` fallback (Linux)
                try:
                    chrome = subprocess.check_output(["which", "google-chrome"], text=True, timeout=5).strip() or None
                except Exception:
                    chrome = None
                if not chrome:
                    try:
                        chrome = subprocess.check_output(["which", "chromium-browser"], text=True, timeout=5).strip() or None
                    except Exception:
                        chrome = None
            if not chrome:
                return {"ok": False, "error": "Chrome/Chromium no encontrado"}

            # Open with existing user data dir so sessions (Gemini, GitHub) are reused
            user_data = os.environ.get(
                "CHROME_USER_DATA_DIR",
                os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\User Data") if os.name == "nt"
                else os.path.expanduser("~/.config/google-chrome"),
            )
            args = [
                chrome,
                f"--user-data-dir={user_data}",
                "--profile-directory=Default",
                "--restore-last-session",
                "--no-first-run",
            ]
            # Try to detect remote debugging port
            subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, close_fds=True)
            time.sleep(2)
            return {"ok": True, "chrome": chrome, "profile": user_data}
        except Exception as e:
            return {"ok": False, "error": str(e)[:200]}

    def _fetch_url(self, url: str, timeout: int = 15) -> str:
        try:
            import urllib.request
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return (r.read() or b"").decode("utf-8", errors="replace")[:12000]
        except Exception as e:
            return f"[fetch error] {e}"

    # ── research ──
    def _run(self, query: str) -> None:
        finding_id = 0
        start_time = time.time()
        try:
            self._push_finding("hermes", "Plan inicial (Hermes)", self._ask_hermes_plan(query))
            sources_needed = self._plan_sources(query)
            for src in sources_needed:
                if not self.state.active:
                    break
                if src not in self.state.sources:
                    self.state.sources.append(src)
                try:
                    if src == "gemini":
                        body = self._query_gemini(query)
                    elif src == "github":
                        body = self._query_github(query)
                    else:
                        body = self._generic_web(query)
                    self._push_finding(src, f"Resultado: {src}", body)
                except Exception as e:
                    self._push_finding(src, f"Error consultando {src}", str(e)[:400])
            # Hermes consolidate
            consolidated = self._ask_hermes_consolidate(query, self.state.results)
            self._push_finding("hermes", "Consolidación final (Hermes)", consolidated)
        except Exception as e:
            with self._lock:
                self.state.error = str(e)[:500]
        finally:
            with self._lock:
                self.state.active = False
            self._notify({"type": "research:done", "elapsed": round(time.time() - start_time, 1), "state": self.state.to_dict()})
            self._persist({"event": "done", "elapsed": round(time.time() - start_time, 1), "ts": time.time()})

    def _push_finding(self, source: str, title: str, body: str) -> None:
        f = Finding(source=source, title=title, body=body)
        with self._lock:
            self.state.results.append(asdict(f))
            self._notify({"type": "research:finding", "finding": asdict(f), "state": self.state.to_dict()})

    def _ask_hermes_plan(self, query: str) -> str:
        prompt = (
            "Eres el planificador de Kitian. Dada esta consulta, responde en español una lista concisa de fuentes indicadas "
            "entre corchetes, de este conjunto: [gemini] [github] [web]. Ejemplo: consultar repos en GitHub y buscar en la web.\n\n"
            f"Consulta: {query}\n\nLista de fuentes:"
        )
        return self._hermes_chat(prompt, fallback="[gemini] [web]")

    def _ask_hermes_consolidate(self, query: str, results: list[dict[str, Any]]) -> str:
        snippets = []
        for r in results[-8:]:
            snippets.append(f"- [{r.get('source','?')}] {r.get('title','')}: {(r.get('body','') or '')[:500]}")
        if not snippets:
            return "Sin hallazgos."
        prompt = (
            "Consolida en español los siguientes hallazgos para responder la consulta del usuario. "
            "Sé concreto, enumera puntos clave, incluye fuente. Si hay conflicto, menciona las diferencias.\n\n"
            f"Consulta: {query}\n\nHallazgos:\n" + "\n".join(snippets) + "\n\nConsolidación:"
        )
        return self._hermes_chat(prompt, fallback="Consolidación pendiente.")

    def _hermes_chat(self, prompt: str, fallback: str, timeout: int = 25) -> str:
        try:
            safe = prompt.replace('"', '\\"').replace("`", "\\`")
            cmd = ["hermes", "chat", "-q", safe, "--quiet"]
            out = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, env={**os.environ, "TERM": "dumb", "PYTHONUNBUFFERED": "1"})
            stdout = (out.stdout or "").strip()
            if stdout.startswith("session_id:"):
                stdout = stdout.split("\n", 1)[1].strip()
            if stdout:
                return stdout[:4000]
            if out.stderr:
                return f"[Hermes stderr] {out.stderr.strip()[:500]}"
            return fallback
        except subprocess.TimeoutExpired:
            return "[Timeout] Hermes no respondió a tiempo."
        except FileNotFoundError:
            return "[Error] comando 'hermes' no encontrado en PATH."
        except Exception as e:
            return f"[Error] {e}"

    # ── source queries ──
    def _plan_sources(self, query: str) -> list[str]:
        # Simple heuristic fallback if hermes plan returns empty
        q = query.lower()
        if any(k in q for k in ["github", "repo", "código", "repositorio"]):
            return ["web", "github"]
        return ["web"]

    def _query_gemini(self, query: str) -> str:
        # Relies on browser-based Gemini: open a new tab and scrape the response.
        # If browser-use is installed, it'll leverage browser automation;
        # otherwise it falls back to web search proxy.
        try:
            br = self._open_browser()
            if br.get("ok"):
                return "[Gemini] Se abrió el navegador para usar la sesión activa. Revisa la pestaña y copia el resultado aquí."
        except Exception:
            pass
        return self._generic_web(query, label="Gemini")

    def _query_github(self, query: str) -> str:
        return self._generic_web(f"https://github.com/search?q={query.replace(' ', '+')}", label="GitHub")

    def _generic_web(self, query: str, label: str = "web") -> str:
        url = query if query.startswith("http") else f"https://duckduckgo.com/html/?q={query.replace(' ', '+')}"
        html = self._fetch_url(url)
        text = re.sub(r"<[^>]+>", " ", html)
        text = re.sub(r"\s+", " ", text).strip()
        return text[:4000] or f"[{label}] Sin contenido."

    # ── persistence ──
    def _persist(self, item: dict[str, Any]) -> None:
        try:
            with self._history_file.open("a", encoding="utf-8") as f:
                f.write(json.dumps(item, ensure_ascii=False) + "\n")
        except Exception:
            pass


orchestrator = ResearchOrchestrator()

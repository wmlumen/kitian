"""Kitian Browser — navegación headless sin MCP.

Uso local / endpoint HTTP:
- `navigate(url)` abre una página y guarda snapshot.
- `snapshot()` devuelve un árbol de accesibilidad compacto.
- `click(ref)` y `type(ref, text)` ejecutan acciones.
- `press(key)` para Enter/Escape/etc.
- `back()` vuelve a la página anterior.

Requisito en Windows:
    pip install playwright
    playwright install chromium

Si falta la librería, el módulo queda como stub y avisa por endpoint.
"""

from __future__ import annotations

import json
import logging
import urllib.request
from typing import Any

log = logging.getLogger("kitian.browser")

try:
    from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout  # type: ignore
    _PLAYWRIGHT_AVAILABLE = True
except Exception:  # pragma: no cover
    _PLAYWRIGHT_AVAILABLE = False


class KitianBrowser:
    def __init__(self) -> None:
        self._pw = None
        self._ctx = None
        self._page = None
        self._history: list[str] = []
        self._last_snapshot: dict[str, Any] = {"ok": False, "error": "not_started"}

    # ------------------------------------------------------------------
    # Ciclo de vida
    # ------------------------------------------------------------------
    def start(self) -> dict[str, Any]:
        if not _PLAYWRIGHT_AVAILABLE:
            return {"ok": False, "error": "playwright not installed. Run: pip install playwright && playwright install chromium"}
        try:
            self._pw = sync_playwright().start()
            self._ctx = self._pw.chromium.launch(headless=True)
            self._page = self._ctx.new_page(viewport={"width": 1280, "height": 720})
            self._last_snapshot = {"ok": True, "url": "", "title": "", "items": []}
            return {"ok": True, "url": "", "title": ""}
        except Exception as e:
            return {"ok": False, "error": f"{type(e).__name__}: {e}"}

    def stop(self) -> None:
        try:
            if self._page:
                self._page.close()
            if self._ctx:
                self._ctx.close()
            if self._pw:
                self._pw.stop()
        except Exception:
            pass
        finally:
            self._page = None
            self._ctx = None
            self._pw = None

    # ------------------------------------------------------------------
    # Navegación
    # ------------------------------------------------------------------
    def navigate(self, url: str, timeout_ms: int = 30000) -> dict[str, Any]:
        if not self._page:
            self.start()
        if not self._page:
            return {"ok": False, "error": "browser not started"}
        try:
            self._history.append(self._page.url)
            self._page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
            return self._capture("navigate")
        except PlaywrightTimeout:
            return {"ok": False, "error": "timeout", "url": url}
        except Exception as e:
            return {"ok": False, "error": f"{type(e).__name__}: {e}"}

    def back(self) -> dict[str, Any]:
        if not self._page or not self._history:
            return {"ok": False, "error": "no history"}
        try:
            self._page.go_back(wait_until="domcontentloaded")
            return self._capture("back")
        except Exception as e:
            return {"ok": False, "error": f"{type(e).__name__}: {e}"}

    # ------------------------------------------------------------------
    # Acciones
    # ------------------------------------------------------------------
    def click(self, ref: str) -> dict[str, Any]:
        try:
            target = self._resolve_ref(ref)
            if not target:
                return {"ok": False, "error": f"ref not found: {ref}"}
            target.click(timeout=5000)
            return self._capture("click", ref=ref)
        except PlaywrightTimeout:
            return {"ok": False, "error": "click timeout", "ref": ref}
        except Exception as e:
            return {"ok": False, "error": f"{type(e).__name__}: {e}"}

    def type(self, ref: str, text: str, clear: bool = True) -> dict[str, Any]:
        try:
            target = self._resolve_ref(ref)
            if not target:
                return {"ok": False, "error": f"ref not found: {ref}"}
            if clear:
                target.fill("")
            target.type(text, timeout=5000)
            return self._capture("type", ref=ref)
        except PlaywrightTimeout:
            return {"ok": False, "error": "type timeout", "ref": ref}
        except Exception as e:
            return {"ok": False, "error": f"{type(e).__name__}: {e}"}

    def press(self, key: str) -> dict[str, Any]:
        try:
            self._page.keyboard.press(key)
            return self._capture("press", key=key)
        except Exception as e:
            return {"ok": False, "error": f"{type(e).__name__}: {e}"}

    def snapshot(self) -> dict[str, Any]:
        if not self._page:
            return {"ok": False, "error": "browser not started"}
        return self._capture("snapshot")

    # ------------------------------------------------------------------
    # Internos
    # ------------------------------------------------------------------
    def _capture(self, action: str, **meta: Any) -> dict[str, Any]:
        if not self._page:
            return {"ok": False, "error": "browser not started"}
        try:
            url = self._page.url
            title = self._page.title()
            items = []
            for el in self._page.locator("a, button, input, textarea, select, [role='button'], [role='link']").all()[:40]:
                try:
                    txt = (el.inner_text() or el.get_attribute("aria-label") or "").strip()[:120]
                    if not txt:
                        continue
                    ref = f"@{items.__len__()+1}"
                    items.append({"ref": ref, "text": txt, "tag": el.evaluate("e => e.tagName.toLowerCase()")})
                except Exception:
                    pass
            self._last_snapshot = {"ok": True, "action": action, "url": url, "title": title, "items": items, **meta}
            return self._last_snapshot
        except Exception as e:
            return {"ok": False, "error": f"{type(e).__name__}: {e}"}

    def _resolve_ref(self, ref: str):
        if not self._page:
            return None
        try:
            idx = int(ref.replace("@", ""), 10) - 1
            items = self._last_snapshot.get("items", [])
            if 0 <= idx < len(items):
                target_ref = items[idx]["ref"]
                return self._page.locator(f"[data-ref='{target_ref}']")
        except Exception:
            pass
        return None


_browser = KitianBrowser()

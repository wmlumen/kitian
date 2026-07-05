"""Gestion de archivos del sistema para Kitian."""
import os
import shutil
import subprocess
import platform
from pathlib import Path
from typing import List, Dict, Any, Optional


SYSTEM = platform.system()
IS_WSL = "microsoft" in platform.uname().release.lower() if hasattr(platform, 'uname') else False


def _safe_path(raw: str) -> Optional[Path]:
    try:
        p = Path(raw)
        if not p.exists():
            return None
        return p.resolve()
    except Exception:
        return None


def _win_path(p: Path) -> str:
    if SYSTEM == "Windows" and IS_WSL:
        # Convertir /mnt/c/... a ruta Windows legible para explorer /start
        s = str(p)
        if s.startswith("/mnt/"):
            letter = s[5].upper()
            rest = s[6:].replace("/", "\\")
            return letter + ":\\" + rest
    return str(p)


def list_dir(path: str = ".") -> Dict[str, Any]:
    try:
        p = _safe_path(path) or Path(".").resolve()
        items: List[Dict[str, Any]] = []
        for child in sorted(p.iterdir(), key=lambda x: (x.is_file(), x.name.lower())):
            try:
                st = child.stat()
                items.append({
                    "name": child.name,
                    "is_dir": child.is_dir(),
                    "size": st.st_size if child.is_file() else 0,
                    "modified": int(st.st_mtime),
                    "path": str(child.resolve()),
                })
            except Exception:
                continue
        return {"ok": True, "path": str(p.resolve()), "items": items}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def open_path(path: str) -> Dict[str, Any]:
    try:
        p = _safe_path(path)
        if not p:
            return {"ok": False, "error": "Ruta no existe"}
        win = _win_path(p)
        if SYSTEM == "Windows":
            subprocess.Popen(["explorer.exe", win], shell=False)
        elif SYSTEM == "Darwin":
            subprocess.Popen(["open", str(p)])
        else:
            subprocess.Popen(["xdg-open", str(p)])
        return {"ok": True, "opened": win}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def search_files(base: str, query: str, limit: int = 50) -> Dict[str, Any]:
    try:
        p = _safe_path(base) or Path(".").resolve()
        q = query.strip()
        if not q:
            return {"ok": False, "error": "Consulta vacía"}
        results: List[Dict[str, Any]] = []
        try:
            for root, dirs, files in os.walk(str(p)):
                for name in files:
                    if q.lower() in name.lower():
                        full = Path(root) / name
                        try:
                            st = full.stat()
                            results.append({
                                "name": name,
                                "path": str(full.resolve()),
                                "size": st.st_size,
                                "modified": int(st.st_mtime),
                            })
                        except Exception:
                            continue
                        if len(results) >= limit:
                            break
                if len(results) >= limit:
                    break
        except Exception as e:
            return {"ok": False, "error": str(e)}
        return {"ok": True, "query": q, "results": results, "truncated": len(results) >= limit}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def move_file(src: str, dst: str) -> Dict[str, Any]:
    try:
        s = _safe_path(src)
        d = Path(dst)
        if not s:
            return {"ok": False, "error": "Origen no existe"}
        if not d.parent.exists():
            d.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(s), str(d))
        return {"ok": True, "from": str(s), "to": str(d.resolve())}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def delete_path(path: str, confirm: bool = False) -> Dict[str, Any]:
    if not confirm:
        return {"ok": False, "error": "Se requiere confirmación explícita (confirm=true)"}
    try:
        p = _safe_path(path)
        if not p:
            return {"ok": False, "error": "Ruta no existe"}
        if p.is_dir():
            shutil.rmtree(str(p))
        else:
            p.unlink()
        return {"ok": True, "deleted": str(p)}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def create_note(path: str, content: str = "") -> Dict[str, Any]:
    try:
        p = Path(path)
        if p.exists():
            return {"ok": False, "error": "Ya existe, no se sobrescribe sin confirmación"}
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        return {"ok": True, "path": str(p.resolve())}
    except Exception as e:
        return {"ok": False, "error": str(e)}

import copy
import json
import os
import threading
import time
from pathlib import Path

from kitian.kitian_db import init as db_init, guardar_conversacion, obtener_contexto, set_pref, get_pref, add_recordatorio, get_recordatorios_activos

BASE_DIR = Path(__file__).parent
MANIFEST_PATH = BASE_DIR / "manifest.json"
SESSION_LOG_PATH = BASE_DIR / "session_logs.json"
_manifest_lock = threading.Lock()

DEFAULT_MANIFEST = {
    "version": "v1.0-CORE-KITIAN",
    "HUD_VERSION": "1.0-CORE-KITIAN",
    "visuals": {
        "primary_color": "#00FFFF",
        "alert_color": "#FFD700",
        "animation_speed": 1.0,
        "particle_density": 100,
        "ring_count": 12,
        "notch_density": 24,
    },
    "kitian_assistant": {
        "status": "ONLINE",
        "active_project": "HUD Saturn Rite v1.0-CORE",
        "task_progress": 0,
        "last_update": "2026-05-29",
        "last_command": "",
        "uptime": "00:00:00",
        "stability_index": 98.5,
        "tasks": [],
    },
    "projects": [
        "Kitian",
        "HUD Saturn Rite v1.0-CORE",
        "Arquitecto de Conocimiento",
        "GITHUT",
        "SIGPRO",
    ],
}


def _default_manifest():
    return copy.deepcopy(DEFAULT_MANIFEST)


def _touch(data):
    data.setdefault("kitian_assistant", {})
    data["kitian_assistant"]["last_update"] = time.strftime("%Y-%m-%d %H:%M:%S")


def _load():
    if MANIFEST_PATH.exists():
        try:
            with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)

            if not isinstance(data, dict):
                return _default_manifest()

            data.setdefault("visuals", {})
            for key, value in DEFAULT_MANIFEST["visuals"].items():
                data["visuals"].setdefault(key, copy.deepcopy(value))

            data.setdefault("kitian_assistant", {})
            for key, value in DEFAULT_MANIFEST["kitian_assistant"].items():
                data["kitian_assistant"].setdefault(key, copy.deepcopy(value))

            data.setdefault("projects", copy.deepcopy(DEFAULT_MANIFEST["projects"]))
            data["kitian_assistant"].setdefault("tasks", [])
            return data
        except json.JSONDecodeError:
            backup = MANIFEST_PATH.with_suffix(".json.broken")
            MANIFEST_PATH.replace(backup)
            return _default_manifest()
        except Exception:
            return _default_manifest()

    return _default_manifest()


def _save(data):
    with _manifest_lock:
        tmp_path = MANIFEST_PATH.with_suffix(".json.tmp")
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        tmp_path.replace(MANIFEST_PATH)


class KitianCore:
    def __init__(self):
        db_init()
        if not MANIFEST_PATH.exists():
            _save(_default_manifest())
        # Inicialización de atributos de sesión para evitar AttributeError
        self._session_start = time.time()
        self._framerate_samples = []
        self._error_count = 0
        self._tasks_completed = 0

    # Memory / contexto inspirado en isair/jarvis (persistencia + resumen)
    def add_context(self, user_text, assistant_text, metadata=None):
        try:
            guardar_conversacion(
                usuario=user_text or "",
                kitian=assistant_text or "",
            )
        except Exception:
            pass

    def get_context(self, limit=4):
        try:
            return obtener_contexto(limit=limit)
        except Exception:
            return []

    def get_pref(self, clave, default=None):
        try:
            return get_pref(clave, default=default)
        except Exception:
            return default

    def set_pref(self, clave, valor):
        try:
            set_pref(clave, valor)
        except Exception:
            pass

    # Proyectos / tareas
    def set_project(self, project_name):
        data = _load()
        projects = data.setdefault("projects", [])
        if project_name not in projects:
            projects.append(project_name)
        data["kitian_assistant"]["active_project"] = project_name
        _touch(data)
        _save(data)
        return f"Proyecto activo: {project_name}"

    def update_progress(self, percentage):
        data = _load()
        value = max(0, min(100, int(percentage)))
        data["kitian_assistant"]["task_progress"] = value
        _touch(data)
        _save(data)
        return f"Progreso: {value}%"

    def get_active_project(self):
        data = _load()
        return data["kitian_assistant"].get("active_project", "Kitian")

    def get_progress(self):
        data = _load()
        return data["kitian_assistant"].get("task_progress", 0)

    def list_projects(self):
        data = _load()
        return data.get("projects", [])

    def set_status(self, status):
        data = _load()
        data["kitian_assistant"]["status"] = status
        _touch(data)
        _save(data)

    def set_last_command(self, command):
        data = _load()
        data["kitian_assistant"]["last_command"] = command
        _touch(data)
        _save(data)

    def add_task(self, descripcion, pasos=None):
        data = _load()
        if "tasks" not in data["kitian_assistant"]:
            data["kitian_assistant"]["tasks"] = []
        tarea = {
            "id": int(time.time() * 1000),
            "descripcion": descripcion,
            "pasos": pasos or [],
            "completado": False,
            "progreso": 0,
            "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "completed_at": None,
        }
        data["kitian_assistant"]["tasks"].append(tarea)
        _touch(data)
        _save(data)
        return tarea

    def complete_task(self, index=0):
        data = _load()
        tasks = data["kitian_assistant"].get("tasks", [])
        if 0 <= index < len(tasks):
            tasks[index]["completado"] = True
            tasks[index]["progreso"] = 100
            tasks[index]["completed_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
            _touch(data)
            _save(data)
            return f"Tarea completada: {tasks[index]['descripcion']}"
        return "Tarea no encontrada."

    def step_task(self, index=0, paso=0):
        data = _load()
        tasks = data["kitian_assistant"].get("tasks", [])
        if 0 <= index < len(tasks):
            t = tasks[index]
            if 0 <= paso < len(t.get("pasos", [])):
                total = len(t["pasos"])
                t["progreso"] = int((paso + 1) / total * 100)
                if paso == total - 1:
                    t["completado"] = True
                    t["completed_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
                _touch(data)
                _save(data)
                return f"Paso {paso+1}/{total}: {t['pasos'][paso]} ({t['progreso']}%)"
        return "Paso no encontrado."

    def get_tasks(self):
        data = _load()
        return data["kitian_assistant"].get("tasks", [])

    def get_stability(self):
        data = _load()
        return data["kitian_assistant"].get("stability_index", 98.5)

    def get_visuals(self):
        data = _load()
        return data.get("visuals", DEFAULT_MANIFEST["visuals"])

    def start_session(self):
        data = _load()
        data["kitian_assistant"]["session_started"] = time.strftime("%Y-%m-%d %H:%M:%S")
        data["kitian_assistant"]["uptime"] = "00:00:00"
        _touch(data)
        _save(data)
        self._session_start = time.time()
        self._framerate_samples = []
        self._error_count = 0
        self._tasks_completed = 0

    def log_framerate(self, fps):
        try:
            self._framerate_samples.append(float(fps))
            if len(self._framerate_samples) > 600:
                self._framerate_samples = self._framerate_samples[-600:]
        except Exception:
            self.log_error()

    def log_error(self):
        self._error_count += 1

    def log_task_done(self):
        self._tasks_completed += 1

    def end_session(self):
        avg_fps = sum(self._framerate_samples) / len(self._framerate_samples) if self._framerate_samples else 60
        duracion = time.time() - self._session_start if hasattr(self, '_session_start') else 0
        log_data = {
            "session_end": time.strftime("%Y-%m-%d %H:%M:%S"),
            "duration_seconds": round(duracion, 1),
            "framerate_avg": round(avg_fps, 1),
            "framerate_min": min(self._framerate_samples) if self._framerate_samples else 60,
            "framerate_max": max(self._framerate_samples) if self._framerate_samples else 60,
            "errors": self._error_count,
            "tasks_completed": self._tasks_completed,
            "status": "OK" if self._error_count == 0 else "DEGRADED",
        }
        if SESSION_LOG_PATH.exists():
            with open(SESSION_LOG_PATH, "r") as f:
                history = json.load(f)
        else:
            history = []
        history.append(log_data)
        if len(history) > 50:
            history = history[-50:]
        with open(SESSION_LOG_PATH, "w") as f:
            json.dump(history, f, indent=2, ensure_ascii=False)
        return log_data


_core_instance = None


def get_core():
    global _core_instance
    if _core_instance is None:
        _core_instance = KitianCore()
    return _core_instance

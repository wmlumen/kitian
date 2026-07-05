import argparse
import hashlib
import json
import socket
import sys
import time
import urllib.request
from pathlib import Path

import psutil
import platform as py_platform

BASE_DIR = Path(__file__).resolve().parent
HEALTH_PATH = BASE_DIR / "kitian_health.json"
LOG_PATH = BASE_DIR / "kitian.log"
MANIFEST_PATH = BASE_DIR / "manifest.json"
HUD_LAYOUT_PATH = BASE_DIR / "hud_layout.json"
DATOS_RED_PATH = BASE_DIR / "datos_red.json"
PLUGINS_DIR = BASE_DIR / "plugins"
CONFIG_PATH = BASE_DIR / "kitian_config.json"

SCHEMA_VERSION = "1.0"
APP_NAME = "Kitian"


def _now():
    return time.strftime("%Y-%m-%d %H:%M:%S")


def _initial_health():
    return {
        "app": APP_NAME,
        "schema_version": SCHEMA_VERSION,
        "generated_at": _now(),
        "status": "UNKNOWN",
        "score": 0,
        "summary": "Sin sondeo ejecutado todavía.",
        "environment": {},
        "metrics": {},
        "components": [],
        "anomalies": [],
        "recommendations": [],
        "history": [],
    }


def load_health(path=HEALTH_PATH):
    if path.exists():
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                return data
        except Exception:
            pass
    return _initial_health()


def save_health(data, path=HEALTH_PATH):
    tmp = Path(path).with_suffix(".json.tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    tmp.replace(path)


def _anom_id(component, title, source):
    raw = f"{component}|{title}|{source}".lower().strip()
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:16]


def registrar_anomalia(component, severity, title, detail, recommendation="", source="manual", path=HEALTH_PATH):
    data = load_health(path)
    anomalies = data.setdefault("anomalies", [])
    now = _now()
    anom_id = _anom_id(component, title, source)
    existing = next((a for a in anomalies if a.get("id") == anom_id), None)
    if existing:
        existing["severity"] = severity
        existing["detail"] = detail
        existing["recommendation"] = recommendation
        existing["last_seen"] = now
        existing["hits"] = int(existing.get("hits", 1)) + 1
        existing["status"] = "OPEN"
    else:
        anomalies.insert(0, {
            "id": anom_id,
            "severity": severity,
            "component": component,
            "title": title,
            "detail": detail,
            "recommendation": recommendation,
            "source": source,
            "first_seen": now,
            "last_seen": now,
            "hits": 1,
            "status": "OPEN",
        })
    save_health(data, path)
    return anom_id


def _check_file_json(path, required_keys=None):
    if not path.exists():
        return False, f"No existe: {path.name}", None
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if required_keys:
            for key in required_keys:
                if key not in data:
                    return False, f"Falta clave '{key}' en {path.name}", data
        return True, "OK", data
    except Exception as e:
        return False, f"JSON inválido en {path.name}: {e}", None


# LM Studio eliminado por optimización de recursos (sólo nube ligera)


def _read_recent_log_issues(path=LOG_PATH, max_lines=300):
    if not path.exists():
        return []
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()[-max_lines:]
    except Exception:
        return []
    issues = []
    for line in lines:
        upper = line.upper()
        if "[CRITICAL]" in upper or "[ERROR]" in upper:
            issues.append(("HIGH", line.strip()))
        elif "[WARNING]" in upper:
            issues.append(("MEDIUM", line.strip()))
    return issues[-25:]


def _plugin_health():
    checks = []
    plugin_count = 0
    enabled_count = 0
    try:
        from kitian_plugins import listar_plugins, cargar_comandos_plugins
        plugins = listar_plugins()
        plugin_count = len(plugins)
        enabled_count = len([p for p in plugins if p.get("enabled") is not False])
        checks.append({"name": "Plugins detectados", "ok": plugin_count >= 0, "severity": "OK", "detail": str(plugin_count)})
        commands = cargar_comandos_plugins()
        checks.append({"name": "Comandos cargados", "ok": len(commands) >= 0, "severity": "OK", "detail": str(len(commands))})
        status = "OK"
        detail = f"{enabled_count}/{plugin_count} habilitados"
        return status, detail, checks, []
    except Exception as e:
        return "DEGRADED", f"Fallo cargando plugins: {e}", checks, [{
            "component": "Plugins",
            "severity": "HIGH",
            "title": "Error de carga de plugins",
            "detail": str(e),
            "recommendation": "Revisar kitian_plugins.py y manifests.",
            "source": "kitian_health_probe.py",
        }]


def build_health_snapshot():
    existing = load_health()
    anomalies = list(existing.get("anomalies", []))
    recommendations = []
    components = []

    cpu = psutil.cpu_percent(interval=0.2)
    ram = psutil.virtual_memory().percent
    disk = psutil.disk_usage(str(BASE_DIR.drive + "\\") if BASE_DIR.drive else "/").percent

    env = {
        "cwd": str(BASE_DIR),
        "hostname": socket.gethostname(),
        "python": sys.version.split()[0],
        "platform": py_platform.platform(),
    }

    metrics = {
        "cpu_percent": round(cpu, 1),
        "ram_percent": round(ram, 1),
        "disk_percent": round(disk, 1),
    }

    manifest_ok, manifest_msg, manifest_data = _check_file_json(MANIFEST_PATH, ["visuals", "kitian_assistant", "projects"])
    components.append({
        "name": "Core Manifest",
        "status": "OK" if manifest_ok else "DEGRADED",
        "detail": manifest_msg,
        "checks": [
            {"name": "manifest.json", "ok": manifest_ok, "severity": "HIGH" if not manifest_ok else "OK", "detail": manifest_msg},
            {"name": "Proyecto activo", "ok": bool((manifest_data or {}).get("kitian_assistant", {}).get("active_project")), "severity": "MEDIUM", "detail": (manifest_data or {}).get("kitian_assistant", {}).get("active_project", "--")},
        ],
    })
    if not manifest_ok:
        anomalies.append({
            "id": _anom_id("Core", "Manifest inválido", "probe"),
            "component": "Core",
            "severity": "HIGH",
            "title": "Manifest inválido",
            "detail": manifest_msg,
            "recommendation": "Revisar manifest.json y kitian_core.py.",
            "source": "kitian_health_probe.py",
            "first_seen": _now(),
            "last_seen": _now(),
            "hits": 1,
            "status": "OPEN",
        })

    hud_ok, hud_msg, _ = _check_file_json(HUD_LAYOUT_PATH, ["positions", "positions_exp", "visibility"])
    components.append({
        "name": "HUD Layout",
        "status": "OK" if hud_ok else "DEGRADED",
        "detail": hud_msg,
        "checks": [
            {"name": "hud_layout.json", "ok": hud_ok, "severity": "HIGH" if not hud_ok else "OK", "detail": hud_msg},
            {"name": "preview.html", "ok": (BASE_DIR / "kitian_health_dashboard.html").exists(), "severity": "MEDIUM", "detail": "Dashboard HTML presente" if (BASE_DIR / "kitian_health_dashboard.html").exists() else "Falta dashboard final"},
        ],
    })

    datos_ok, datos_msg, datos_data = _check_file_json(DATOS_RED_PATH, ["nodes", "edges"])
    components.append({
        "name": "Red de Conocimiento",
        "status": "OK" if datos_ok else "WARN",
        "detail": datos_msg if DATOS_RED_PATH.exists() else "datos_red.json aún no creado",
        "checks": [
            {"name": "datos_red.json", "ok": datos_ok, "severity": "MEDIUM" if DATOS_RED_PATH.exists() else "LOW", "detail": datos_msg},
            {"name": "Nodos", "ok": isinstance((datos_data or {}).get("nodes", []), list), "severity": "LOW", "detail": str(len((datos_data or {}).get("nodes", [])))},
            {"name": "Aristas", "ok": isinstance((datos_data or {}).get("edges", []), list), "severity": "LOW", "detail": str(len((datos_data or {}).get("edges", [])))},
        ],
    })

    plugin_status, plugin_detail, plugin_checks, plugin_anoms = _plugin_health()
    components.append({
        "name": "Plugins",
        "status": plugin_status,
        "detail": plugin_detail,
        "checks": plugin_checks,
    })
    anomalies.extend(plugin_anoms)

    config_ok, config_msg, config_data = _check_file_json(CONFIG_PATH, ["backend", "model"])
    components.append({
        "name": "IA Core / Config",
        "status": "OK" if config_ok else "DEGRADED",
        "detail": f"Backend activo: {(config_data or {}).get('backend', 'gemini')}",
        "checks": [
            {"name": "kitian_config.json", "ok": config_ok, "severity": "MEDIUM" if not config_ok else "OK", "detail": config_msg},
            {"name": "Backend configurado", "ok": bool((config_data or {}).get("backend")), "severity": "LOW", "detail": (config_data or {}).get("backend", "--")},
        ],
    })

    recent_issues = _read_recent_log_issues()
    components.append({
        "name": "Logs",
        "status": "OK" if not recent_issues else "DEGRADED",
        "detail": f"{len(recent_issues)} issue(s) reciente(s)" if recent_issues else "Sin errores recientes",
        "checks": [
            {"name": "kitian.log", "ok": LOG_PATH.exists(), "severity": "MEDIUM" if not LOG_PATH.exists() else "OK", "detail": "Presente" if LOG_PATH.exists() else "No existe"},
            {"name": "Errores recientes", "ok": len([i for i in recent_issues if i[0] == 'HIGH']) == 0, "severity": "HIGH" if recent_issues else "OK", "detail": str(len(recent_issues))},
        ],
    })
    for sev, line in recent_issues[-8:]:
        anomalies.append({
            "id": _anom_id("Logs", line[:60], "probe"),
            "component": "Logs",
            "severity": sev,
            "title": "Evento reciente en log",
            "detail": line,
            "recommendation": "Revisar kitian.log y el módulo fuente.",
            "source": "kitian.log",
            "first_seen": _now(),
            "last_seen": _now(),
            "hits": 1,
            "status": "OPEN",
        })

    components.append({
        "name": "Sistema",
        "status": "OK" if cpu < 85 and ram < 90 and disk < 92 else "WARN",
        "detail": f"CPU {cpu:.1f}% | RAM {ram:.1f}% | Disco {disk:.1f}%",
        "checks": [
            {"name": "CPU", "ok": cpu < 85, "severity": "HIGH" if cpu >= 95 else "MEDIUM", "detail": f"{cpu:.1f}%"},
            {"name": "RAM", "ok": ram < 90, "severity": "HIGH" if ram >= 95 else "MEDIUM", "detail": f"{ram:.1f}%"},
            {"name": "Disco", "ok": disk < 92, "severity": "HIGH" if disk >= 97 else "MEDIUM", "detail": f"{disk:.1f}%"},
        ],
    })

    merged = {}
    for anomaly in anomalies:
        anomaly = dict(anomaly)
        key = anomaly.get("id") or _anom_id(anomaly.get("component", "?"), anomaly.get("title", "?"), anomaly.get("source", "probe"))
        anomaly["id"] = key
        if key in merged:
            prev = merged[key]
            prev["last_seen"] = _now()
            prev["hits"] = int(prev.get("hits", 1)) + 1
            prev["detail"] = anomaly.get("detail", prev.get("detail"))
            prev["recommendation"] = anomaly.get("recommendation", prev.get("recommendation"))
            prev["severity"] = anomaly.get("severity", prev.get("severity"))
            prev["status"] = "OPEN"
        else:
            existing_prev = next((a for a in existing.get("anomalies", []) if a.get("id") == key), None)
            if existing_prev:
                anomaly["first_seen"] = existing_prev.get("first_seen", anomaly.get("first_seen", _now()))
                anomaly["hits"] = int(existing_prev.get("hits", 1)) + 1
            else:
                anomaly.setdefault("first_seen", _now())
                anomaly.setdefault("hits", 1)
            anomaly["last_seen"] = _now()
            anomaly["status"] = "OPEN"
            merged[key] = anomaly

    anomalies = list(merged.values())
    anomalies.sort(key=lambda a: (["LOW", "MEDIUM", "HIGH", "CRITICAL"].index(a.get("severity", "LOW")) if a.get("severity", "LOW") in ["LOW", "MEDIUM", "HIGH", "CRITICAL"] else 0), reverse=True)

    score = 100
    for a in anomalies:
        sev = a.get("severity", "LOW").upper()
        score -= {"LOW": 2, "MEDIUM": 6, "HIGH": 12, "CRITICAL": 20}.get(sev, 4)
    score = max(0, min(100, score))

    if any(a.get("severity") == "CRITICAL" for a in anomalies):
        status = "CRITICAL"
    elif any(a.get("severity") == "HIGH" for a in anomalies):
        status = "DEGRADED"
    elif any(a.get("severity") == "MEDIUM" for a in anomalies):
        status = "WARN"
    else:
        status = "OK"

    recs = []
    for anomaly in anomalies:
        rec = anomaly.get("recommendation")
        if rec and rec not in recs:
            recs.append(rec)
    if not recs:
        recs.append("No se detectaron correcciones urgentes.")

    history = existing.get("history", [])
    history.append({
        "generated_at": _now(),
        "status": status,
        "score": score,
        "open_anomalies": len(anomalies),
    })
    history = history[-120:]

    data = {
        "app": APP_NAME,
        "schema_version": SCHEMA_VERSION,
        "generated_at": _now(),
        "status": status,
        "score": score,
        "summary": f"{len(anomalies)} anomalía(s) abierta(s). CPU {cpu:.1f}% | RAM {ram:.1f}% | Disco {disk:.1f}%.",
        "environment": env,
        "metrics": metrics,
        "components": components,
        "anomalies": anomalies,
        "recommendations": recs,
        "history": history,
    }
    return data


def run_probe():
    data = build_health_snapshot()
    save_health(data)
    print(f"[health] {data['status']} | score {data['score']} | anomalies {len(data['anomalies'])}")
    return data


def dump_full(data, path=HEALTH_PATH):
    save_health(data, path)


def dump_quick(data):
    print(f"STATUS={data['status']}|SCORE={data['score']}|ANOMALIES={len(data['anomalies'])}")
    print(data["summary"])
    for rec in data.get("recommendations", [])[:3]:
        print(f"- {rec}")


def main():
    parser = argparse.ArgumentParser(description="Kitian Health Probe")
    parser.add_argument("--watch", type=int, default=0, help="Ejecuta en bucle cada N segundos.")
    parser.add_argument("--quick", action="store_true", help="Salida compacta para agentes/terminal.")
    args = parser.parse_args()

    if args.watch and args.watch > 0:
        while True:
            run_probe()
            time.sleep(args.watch)
    else:
        data = run_probe()
        if args.quick:
            dump_quick(data)


if __name__ == "__main__":
    main()

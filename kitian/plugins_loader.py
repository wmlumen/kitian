import logging
import importlib.util
from pathlib import Path

log = logging.getLogger("kitian")
PLUGINS_DIR = Path(__file__).resolve().parent.parent / "plugins"


def cargar_comandos_plugins():
    comandos = {}
    if not PLUGINS_DIR.exists():
        return comandos
    for plugin_dir in sorted(PLUGINS_DIR.iterdir()):
        if not plugin_dir.is_dir():
            continue
        manifest = plugin_dir / "manifest.json"
        if not manifest.exists():
            continue
        try:
            import json
            data = json.loads(manifest.read_text(encoding="utf-8"))
            nombre = data.get("nombre") or plugin_dir.name
            entrada = data.get("entrada") or "plugin.py"
            modulo_path = plugin_dir / entrada
            if not modulo_path.exists():
                continue
            spec = importlib.util.spec_from_file_location(f"kitian_plugin_{plugin_dir.name}", modulo_path)
            modulo = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(modulo)
            register = getattr(modulo, "register", None)
            if callable(register):
                items = register()
                if isinstance(items, dict):
                    comandos.update(items)
                    log.info("Plugin cargado: %s (%s comandos)", nombre, len(items))
                elif isinstance(items, list):
                    for item in items:
                        cmd = item.get("comando") or item.get("nombre")
                        fn = item.get("funcion") or item.get("respuesta")
                        if cmd and fn:
                            comandos[cmd] = fn
                    log.info("Plugin cargado (list): %s (%s comandos)", nombre, len(comandos))
        except Exception as e:
            log.warning("Error cargando plugin %s: %s", plugin_dir.name, e)
    return comandos

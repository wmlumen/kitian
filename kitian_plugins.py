import json
import logging
import importlib.util
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
PLUGINS_DIR = BASE_DIR / "plugins"
MANIFEST_FILE = "manifest.json"

log = logging.getLogger("kitian.plugins")


def _ensure_plugins_dir():
    PLUGINS_DIR.mkdir(exist_ok=True)
    init_file = PLUGINS_DIR / "__init__.py"
    if not init_file.exists():
        init_file.write_text("# Kitian Plugins\n", encoding="utf-8")


def _is_safe_plugin_name(nombre):
    if not nombre or not isinstance(nombre, str):
        return False
    if "/" in nombre or "\\" in nombre or ".." in nombre:
        return False
    return True


def listar_plugins():
    """
    Devuelve plugins válidos encontrados en /plugins.
    Agrega '_folder' para no depender de 'name' dentro del manifest.
    """
    _ensure_plugins_dir()
    plugins = []

    for folder in PLUGINS_DIR.iterdir():
        if not folder.is_dir() or folder.name.startswith("_"):
            continue

        manifest = folder / MANIFEST_FILE
        if not manifest.exists():
            continue

        try:
            with open(manifest, "r", encoding="utf-8-sig") as f:
                data = json.load(f)

            if not isinstance(data, dict):
                log.warning("Manifest invalido en %s: no es un objeto JSON", folder.name)
                continue

            data["_folder"] = folder.name
            data.setdefault("name", folder.name)
            data.setdefault("enabled", True)
            plugins.append(data)
        except json.JSONDecodeError as e:
            log.error("Manifest JSON invalido en plugin %s: %s", folder.name, e)
        except Exception as e:
            log.error("Error leyendo manifest de %s: %s", folder.name, e)

    return plugins


def cargar_plugin(nombre):
    """
    Carga un plugin específico y devuelve la lista de tools registradas.
    """
    _ensure_plugins_dir()

    if not _is_safe_plugin_name(nombre):
        log.error("Nombre de plugin inseguro o invalido: %r", nombre)
        return []

    plugin_dir = (PLUGINS_DIR / nombre).resolve()

    try:
        plugin_dir.relative_to(PLUGINS_DIR.resolve())
    except ValueError:
        log.error("Intento de cargar plugin fuera del directorio permitido: %s", plugin_dir)
        return []

    plugin_file = plugin_dir / "plugin.py"
    if not plugin_file.exists():
        log.warning("Plugin sin plugin.py: %s", nombre)
        return []

    try:
        module_name = f"kitian_plugin_{nombre}"
        spec = importlib.util.spec_from_file_location(module_name, str(plugin_file))
        if spec is None or spec.loader is None:
            log.error("No se pudo crear spec para plugin: %s", nombre)
            return []

        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)

        if not hasattr(mod, "register"):
            log.warning("Plugin %s no tiene funcion register()", nombre)
            return []

        tools = mod.register()
        if tools is None:
            return []
        if not isinstance(tools, list):
            log.error("register() de %s debe devolver una lista", nombre)
            return []
        return tools
    except Exception as e:
        log.exception("Error cargando plugin %s: %s", nombre, e)
        return []


def cargar_comandos_plugins():
    """
    Carga todos los comandos de plugins habilitados.
    Devuelve un dict:
        {
            "comando": funcion
        }
    """
    comandos = {}

    for plugin in listar_plugins():
        if plugin.get("enabled") is False:
            continue

        folder = plugin.get("_folder")
        nombre_visible = plugin.get("name", folder)
        tools = cargar_plugin(folder)

        for tool in tools:
            if not isinstance(tool, dict):
                log.warning("Tool invalida en plugin %s: %r", nombre_visible, tool)
                continue

            comando = tool.get("comando")
            funcion = tool.get("funcion")

            if not comando or not isinstance(comando, str):
                log.warning("Comando invalido en plugin %s: %r", nombre_visible, tool)
                continue

            comando = comando.strip().lower()

            if not callable(funcion):
                log.warning("Comando %s en plugin %s no tiene funcion valida", comando, nombre_visible)
                continue

            if comando in comandos:
                log.warning("Comando duplicado '%s'. Se conserva el primero.", comando)
                continue

            comandos[comando] = funcion
            log.info("Comando plugin cargado: %s desde %s", comando, nombre_visible)

    return comandos

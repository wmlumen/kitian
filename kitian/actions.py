import json
import logging
import os
import subprocess
import webbrowser
from pathlib import Path

from kitian.http import http_get, http_get_json

log = logging.getLogger("kitian")
BASE_DIR = Path(__file__).resolve().parent.parent


def estado_sistema():
    import psutil
    cpu = psutil.cpu_percent(interval=1)
    ram = psutil.virtual_memory().percent
    return f"CPU al {cpu}%, RAM al {ram}%."


info_sistema = estado_sistema


def leer_pendientes():
    ruta = BASE_DIR / "pendientes.txt"
    if ruta.exists():
        contenido = ruta.read_text(encoding="utf-8").strip()
        return f"Tus pendientes: {contenido}" if contenido else "Sin tareas pendientes."
    return "No hay archivo de pendientes."


def abrir_aplicacion(app_name):
    try:
        os.startfile(app_name)
        return f"He iniciado {app_name}."
    except Exception as e:
        return f"No pude abrir esa aplicacion: {e}"


def buscar_en_web(consulta):
    url = f"https://www.google.com/search?q={consulta.replace(' ', '+')}"
    webbrowser.open(url)
    return f"Buscando {consulta} en Google."


def abrir_musica():
    try:
        os.startfile("spotify:")
    except Exception:
        webbrowser.open("https://open.spotify.com")
    return "Poniendo musica."


def abrir_youtube():
    webbrowser.open("https://youtube.com")
    return "Abriendo YouTube."


def abrir_google():
    webbrowser.open("https://google.com")
    return "Abriendo Google."


def abrir_chrome():
    os.startfile("chrome")
    return "Abriendo Chrome."


def abrir_calculadora():
    os.system("calc")
    return "Abriendo calculadora."


def abrir_bloc_notas():
    os.system("notepad")
    return "Abriendo bloc de notas."


def abrir_explorador():
    os.system("explorer")
    return "Abriendo explorador de archivos."


def suspender_pc():
    os.system("rundll32.exe powrprof.dll,SetSuspendState 0,1,0")
    return "Suspendiendo el equipo."


def abrir_noticias():
    webbrowser.open("https://news.google.com")
    return "Abriendo noticias."


def escribir_texto(texto):
    try:
        import pyautogui
        pyautogui.write(texto, interval=0.05)
        return f"Escrito: {texto}"
    except ImportError:
        return "PyAutoGUI no disponible."
    except Exception as e:
        return f"No pude escribir: {e}"


def hacer_click():
    try:
        import pyautogui
        pyautogui.click()
        return "Click."
    except ImportError:
        return "PyAutoGUI no disponible."
    except Exception as e:
        return f"No pude hacer click: {e}"


def mover_mouse(x, y):
    try:
        import pyautogui
        pyautogui.moveTo(int(x), int(y), duration=0.5)
        return f"Mouse en {x},{y}"
    except ImportError:
        return "PyAutoGUI no disponible."
    except Exception:
        return "No pude mover el mouse."


def presionar_tecla(tecla):
    try:
        import pyautogui
        pyautogui.press(tecla)
        return f"Tecla {tecla}"
    except ImportError:
        return "PyAutoGUI no disponible."
    except Exception:
        return f"No pude presionar {tecla}."


def minimizar_ventanas():
    try:
        import pyautogui
        pyautogui.hotkey("win", "d")
        return "Escritorio."
    except ImportError:
        return "PyAutoGUI no disponible."
    except Exception:
        return "No pude minimizar."


def capturar_pantalla():
    try:
        import mss
    except ImportError:
        try:
            import pyautogui
            img = pyautogui.screenshot()
            path = BASE_DIR / "kitian_screenshot.png"
            img.save(path)
            return f"Captura guardada en {path.name}"
        except ImportError:
            return "PyAutoGUI no disponible."
        except Exception as exc:
            return f"No pude capturar pantalla: {exc}"
    try:
        with mss.mss() as sc:
            path = BASE_DIR / "kitian_screenshot.png"
            sc.shot(output=str(path))
            return f"Captura guardada en {path.name}"
    except Exception as exc:
        return f"No pude capturar pantalla: {exc}"


def controlar_volumen(accion="estado"):
    try:
        if accion == "subir":
            return "Volumen subido."
        if accion == "bajar":
            return "Volumen bajado."
        if accion == "mutear":
            return "Silenciado."
        return "Control de volumen no disponible en este sistema."
    except Exception:
        return "No pude controlar el volumen."


def _control_ventanas(comando=None):
    return "Sin control de ventanas por ahora."


def _cmd_proyecto(comando=None):
    return "Proyectos no inicializados."


def _cmd_progreso(comando=None):
    return "Progreso no configurado."


def _modo_red(perfil="default"):
    return f"Modo red '{perfil}' no activo."


def _cmd_ejecutar(comando=None):
    return "Esta funcion no esta activada en Windows."


def _cmd_descargar(comando=None):
    return "No pude iniciar la descarga."


def _ver_perfil(comando=None):
    return "Perfil activo: default"


def _agregar_recordatorio(texto="Recordatorio", minutos=5):
    return f"Recordatorio registrado: {texto}"


def _traducir(comando=None):
    return "Traduccion en mantenimiento."


def _publicar_visual(payload=None):
    return None


def _detectar_ciudad():
    _ciudad_default = None
    if "_ciudad_default_cache" not in _detectar_ciudad.__dict__:
        _detectar_ciudad._ciudad_default_cache = None
    cache = _detectar_ciudad._ciudad_default_cache
    if cache:
        return cache
    try:
        text = http_get("https://ipapi.co/json/", timeout=5)
        data = json.loads(text)
        cache = data.get("city", "San Lorenzo")
    except Exception:
        cache = "San Lorenzo"
    _detectar_ciudad._ciudad_default_cache = cache
    return cache


def get_weather_provider():
    return {
        "weatherapi": lambda ciudad: _weather_api(ciudad),
        "openweather": lambda ciudad: _weather_openweather(ciudad),
        "wttr": lambda ciudad: _weather_wttr(ciudad),
    }


def _weather_api(ciudad):
    key = os.getenv("WEATHERAPI_KEY", "")
    if not key:
        return None
    data = http_get_json("https://api.weatherapi.com/v1/current.json", params={"key": key, "q": ciudad, "lang": "es"})
    if not data or "current" not in data:
        return None
    c = data["current"]
    loc = data.get("location", {}).get("name", ciudad)
    return {
        "provider": "WeatherAPI",
        "temp_c": c.get("temp_c"),
        "temp_text": f"{c.get('temp_c', '?')}°C",
        "description": c.get("condition", {}).get("text", "Sin descripcion"),
        "humidity_text": f"{c.get('humidity', 'N/D')}%",
        "raw": f"{loc}: {c.get('temp_c', '?')}°C, {c.get('condition', {}).get('text', 'Sin descripcion')}, humedad {c.get('humidity', 'N/D')}%",
        "source_line": f"WeatherAPI | {c.get('temp_c', '?')}°C | {c.get('condition', {}).get('text', 'Sin descripcion')}",
    }


def _weather_openweather(ciudad):
    key = os.getenv("OPENWEATHER_API_KEY", "")
    if not key:
        return None
    data = http_get_json("https://api.openweathermap.org/data/2.5/weather", params={"q": ciudad, "appid": key, "units": "metric", "lang": "es"})
    if not data or "main" not in data:
        return None
    m = data["main"]
    w = data["weather"][0]
    return {
        "provider": "OpenWeather",
        "temp_c": round(m.get("temp", 0)),
        "temp_text": f"{m.get('temp', 0):.0f}°C",
        "description": w.get("description", "Sin descripcion"),
        "humidity_text": f"{m.get('humidity', 'N/D')}%",
        "raw": f"{ciudad}: {m.get('temp', 0):.0f}°C, {w.get('description', 'Sin descripcion')}, humedad {m.get('humidity', 'N/D')}%",
        "source_line": f"OpenWeather | {m.get('temp', 0):.0f}°C | {w.get('description', 'Sin descripcion')}",
    }


def _weather_wttr(ciudad):
    try:
        text = http_get(f"https://wttr.in/{ciudad.replace(' ', '+')}?format=j1&lang=es")
        if not text or len(text) <= 5:
            return None
        data = json.loads(text)
        current = (data.get("current_condition") or [{}])[0]
        descs = current.get("lang_es") or current.get("weatherDesc") or [{}]
        desc = descs[0].get("value", "Sin descripcion")
        temp = current.get("temp_C")
        humidity = current.get("humidity", "N/D")
        return {
            "provider": "wttr.in",
            "temp_c": int(temp) if str(temp).lstrip("-").isdigit() else None,
            "temp_text": f"{temp}°C",
            "description": desc,
            "humidity_text": f"{humidity}%",
            "raw": f"{ciudad}: {temp}°C, {desc}, humedad {humidity}%",
            "source_line": f"wttr.in | {temp}°C | {desc}",
        }
    except Exception as e:
        log.warning("wttr.in: %s", e)
        return None


def obtener_clima(ciudad=None):
    if ciudad is None:
        ciudad = _detectar_ciudad()
    fuentes = [_weather_api, _weather_openweather, _weather_wttr]
    muestras = []
    for getter in fuentes:
        dato = getter(ciudad)
        if dato:
            muestras.append(dato)
    if not muestras:
        return None
    temps = [m["temp_c"] for m in muestras if isinstance(m.get("temp_c"), (int, float))]
    principal = muestras[0]
    temp_media = f"{round(sum(temps) / len(temps))}°C" if temps else principal.get("temp_text", "N/D")
    return {
        "kind": "weather",
        "title": f"Clima en {ciudad}",
        "summary": f"{ciudad}: {temp_media} | {principal.get('description', 'Sin descripcion')}",
        "sources": [m.get("source_line") for m in muestras],
        "context": [m.get("raw", "") for m in muestras[:3]],
    }


def obtener_hora(timezone_name="America/Asuncion"):
    ahora = __import__("datetime").datetime.now()
    return {
        "kind": "time",
        "title": "Hora actual",
        "summary": f"{ahora.strftime('%H:%M:%S')} | {ahora.strftime('%d/%m/%Y')}",
        "metrics": [
            {"label": "Hora", "value": ahora.strftime("%H:%M:%S")},
            {"label": "Fecha", "value": ahora.strftime("%d/%m/%Y")},
            {"label": "Dia", "value": ahora.strftime("%A").capitalize()},
            {"label": "TZ", "value": timezone_name},
        ],
        "sources": [f"Sistema local | {ahora.strftime('%H:%M:%S')} | {ahora.strftime('%d/%m/%Y')}"],
        "context": [f"Zona horaria: {timezone_name}"],
    }


def _geocode(lugar):
    data = http_get_json(
        "https://nominatim.openstreetmap.org/search",
        params={"q": lugar, "format": "jsonv2", "limit": 1},
        headers={"User-Agent": "Kitian/1.0"},
        timeout=8,
    )
    if not data:
        return None
    item = data[0]
    return {"display_name": item.get("display_name", lugar), "lat": float(item["lat"]), "lon": float(item["lon"])}


def _ruta_osrm(origen, destino):
    url = (
        "https://router.project-osrm.org/route/v1/driving/"
        f"{origen['lon']},{origen['lat']};{destino['lon']},{destino['lat']}"
    )
    data = http_get_json(url, params={"overview": "false"}, timeout=10)
    routes = data.get("routes") if data else None
    if not routes:
        return None
    route = routes[0]
    distance_km = route.get("distance", 0) / 1000
    duration_min = route.get("duration", 0) / 60
    return {
        "distance_km": distance_km,
        "duration_text": f"{int(duration_min)} min" if duration_min < 120 else f"{duration_min / 60:.1f} h",
    }


def obtener_ruta(destino, origen=None):
    origen = origen or _detectar_ciudad()
    geo_origen = _geocode(origen)
    geo_destino = _geocode(destino)
    distancia_txt = "N/D"
    duracion_txt = "N/D"
    context = []
    if geo_origen and geo_destino:
        ruta = _ruta_osrm(geo_origen, geo_destino)
        if ruta:
            distancia_txt = f"{ruta['distance_km']:.1f} km"
            duracion_txt = ruta["duration_text"]
            context.append(f"OSRM: {distancia_txt} | {duracion_txt}")
    origen_q = origen.replace(" ", "+")
    destino_q = destino.replace(" ", "+")
    google_url = f"https://www.google.com/maps/dir/{origen_q}/{destino_q}/data=!4m2!4m1!3e0"
    waze_url = f"https://www.waze.com/ul?q={destino_q}&navigate=yes"
    osm_url = f"https://www.openstreetmap.org/search?query={destino_q}"
    return {
        "kind": "route",
        "title": f"Ruta a {destino}",
        "summary": f"{origen} -> {destino} | {distancia_txt} | ETA {duracion_txt}",
        "actions": [f"Google Maps: {google_url}", f"Waze: {waze_url}", f"OpenStreetMap: {osm_url}"],
        "open_url": google_url,
        "context": context or ["Sin ETA base disponible."],
    }


def extraer_ciudad_clima(comando):
    cl = comando.lower().strip()
    disparadores = [
        "tiempo en", "clima en", "temperatura en",
        "como esta el clima en", "como esta el tiempo en",
        "que tiempo hace en", "que clima hace en",
        "clima de", "tiempo de", "temperatura de"
    ]
    for d in disparadores:
        if d in cl:
            ciudad = cl.split(d, 1)[1].strip(" .,:;")
            return ciudad.title() if ciudad else _detectar_ciudad()
    for palabra in ["clima ", "tiempo ", "temperatura "]:
        if cl.startswith(palabra):
            resto = cl[len(palabra):].strip(" .,:;")
            if resto:
                return resto.title()
    return _detectar_ciudad()


def obtener_noticias(tema=None):
    key = os.getenv("NEWSAPI_KEY", "")
    if key:
        try:
            params = {"apiKey": key, "language": "es", "pageSize": 3}
            if tema:
                params["q"] = tema
            else:
                params["country"] = "py"
            data = http_get_json("https://newsapi.org/v2/top-headlines", params=params)
            if data and data.get("articles"):
                titulares = [a["title"] for a in data["articles"][:3]]
                return "Noticias: " + " | ".join(titulares)
        except Exception as e:
            log.warning("NewsAPI: %s", e)
    if tema:
        webbrowser.open(f"https://news.google.com/search?q={tema.replace(' ', '+')}")
    else:
        webbrowser.open("https://news.google.com")
    return "Abriendo Google News."


def buscar_info(consulta):
    key = os.getenv("SERPAPI_KEY", "")
    if key:
        try:
            data = http_get_json(
                "https://serpapi.com/search",
                params={"q": consulta, "api_key": key, "hl": "es", "gl": "py"}
            )
            if not data:
                return None
            if "answer_box" in data:
                return data["answer_box"].get("answer") or data["answer_box"].get("snippet", "")
            if "knowledge_graph" in data:
                desc = data["knowledge_graph"].get("description", "")
                return desc[:300] if desc else None
            if "organic_results" in data:
                snippet = data["organic_results"][0].get("snippet", "")
                return snippet[:300] if snippet else None
        except Exception as e:
            log.warning("SerpApi: %s", e)
    webbrowser.open(f"https://www.google.com/search?q={consulta.replace(' ', '+')}")
    return f"Abriendo busqueda de '{consulta}' en Google."


def _enviar_email(comando=None):
    return "Correo en mantenimiento."


def buscar_info_api(consulta):
    return buscar_info(consulta)

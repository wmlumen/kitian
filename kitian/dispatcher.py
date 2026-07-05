import logging
import os
import re
import sys
import time
import json
import difflib
import webbrowser
import subprocess
from pathlib import Path

from kitian import state
from kitian.audio import (
    hablar,
    load_whisper,
    escuchar_comando,
    escuchar_continuo,
)
from kitian.actions import (
    abrir_musica,
    abrir_youtube,
    abrir_google,
    abrir_chrome,
    abrir_calculadora,
    abrir_bloc_notas,
    abrir_explorador,
    suspender_pc,
    abrir_noticias,
    leer_pendientes,
    info_sistema,
    buscar_en_web,
    escribir_texto,
    hacer_click,
    mover_mouse,
    presionar_tecla,
    minimizar_ventanas,
    capturar_pantalla,
    controlar_volumen,
    extraer_ciudad_clima,
    _detectar_ciudad,
    obtener_clima,
    obtener_hora,
    obtener_ruta,
    _cmd_proyecto,
    _cmd_progreso,
    _modo_red,
    _cmd_ejecutar,
    _cmd_descargar,
    _enviar_email,
    _ver_perfil,
    _agregar_recordatorio,
    _traducir,
    _control_ventanas,
    buscar_info_api,
    _publicar_visual,
)
from kitian.config import current_model, client as ia_client

log = logging.getLogger("kitian")
BASE_DIR = Path(__file__).resolve().parent.parent
CAPACIDADES = (
    "Comandos: musica, spotify, youtube, chrome, calculadora, bloc de notas, "
    "explorador, hora, fecha, clima, tiempo en [ciudad], busca [tema], sistema, "
    "pendientes, ayuda, noticias, recordatorios, traduccion, ventanas, volumen, "
    "captura, proyectos, progreso, red de conocimiento y terminal."
)
COLORES = {
    "hablando": "#00ffcc",
    "activo": "#00ffff",
    "escuchando": "#00cc66",
    "pensando": "#ffcc00",
    "offline": "#ff4444",
    "apagado": "#666666",
}
_comando_actual = ""
_core = None

try:
    from kitian.assistant_profile import AssistantProfile
    from kitian.preference_engine import PreferenceEngine

    _profile = AssistantProfile()
    _preference_engine = PreferenceEngine(_profile)
except Exception:
    _profile = None
    _preference_engine = None


def _set_comando(cmd):
    global _comando_actual
    _comando_actual = cmd


def _mostrar_ayuda():
    state.set_info(CAPACIDADES)
    return CAPACIDADES


def _parse_recordatorio(comando):
    cl = comando.lower()
    minutos = 0
    for prefijo in ["recuerdame en ", "recordame en ", "recordatorio en ", "alarma en "]:
        if cl.startswith(prefijo):
            resto = cl[len(prefijo):]
            palabras = resto.split()
            for i, p in enumerate(palabras):
                if p.isdigit():
                    if i + 1 < len(palabras) and "min" in palabras[i + 1]:
                        minutos = int(p)
                    elif i + 1 < len(palabras) and "seg" in palabras[i + 1]:
                        minutos = int(p) / 60
                    elif "minuto" in p or "minutos" in p:
                        pass
                    else:
                        minutos = int(p)
                    texto = " ".join(palabras[i + 1:]).strip()
                    if not texto:
                        texto = "Recordatorio Kitian"
                    return (texto, minutos)
    return None


def consultar_ia(prompt, reintentos=3):
    for intento in range(1, reintentos + 1):
        try:
            response = ia_client.chat.completions.create(
                model=current_model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=512,
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            err = str(e)
            log.error("Intento %d/%d: %s", intento, reintentos, err[:150])
            if any(x in err.lower() for x in ["401", "403", "api key", "auth"]):
                return "[AUTH]"
            if intento < reintentos:
                time.sleep(1.5 * intento)
            else:
                if "timed out" in err.lower() or "connection" in err.lower():
                    return "[CONN]"
                return None
    return None


WEB_TRIGGERS = [
    "que es ", "quien es ", "quien fue ", "que son ",
    "informacion sobre ", "informacion de ",
    "busca informacion sobre ", "busca informacion de ",
    "consulta sobre ",
]


def _extraer_tema(comando):
    cl = comando.lower().strip()
    for d in [
        "que es ", "quien es ", "quien fue ",
        "busca informacion sobre ", "informacion sobre ",
        "consulta sobre ", "busca informacion de ", "informacion de ",
    ]:
        if cl.startswith(d):
            return cl[len(d):].strip(" .,;:?")
    return cl


def _extraer_tema_noticias(comando):
    cl = comando.lower().strip()
    for d in ["noticias de ", "noticias sobre ", "ultimas noticias de "]:
        if cl.startswith(d):
            return cl[len(d):].strip(" .,;:?")
    return None


def decir_hora():
    import datetime
    ahora = datetime.datetime.now()
    state.set_info(f"Son las {ahora.hour} horas con {ahora.minute:02d} minutos.")
    return f"Son las {ahora.hour} horas con {ahora.minute:02d} minutos."


def decir_fecha():
    import datetime
    ahora = datetime.datetime.now()
    meses = [
        "enero", "febrero", "marzo", "abril", "mayo", "junio",
        "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
    ]
    payload = {
        "kind": "date",
        "title": "Fecha actual",
        "summary": f"{ahora.day} de {meses[ahora.month - 1]} de {ahora.year}",
        "metrics": [
            {"label": "Dia", "value": str(ahora.day)},
            {"label": "Mes", "value": meses[ahora.month - 1]},
            {"label": "Año", "value": str(ahora.year)},
            {"label": "Semana", "value": ahora.strftime('%A').capitalize()},
        ],
        "sources": ["Sistema local"],
        "actions": [],
        "context": ["Calendario local del sistema"],
    }
    _publicar_visual(payload)
    return f"Hoy es {payload['summary']}."


def decir_clima(ciudad=None):
    if ciudad is None:
        ciudad = _detectar_ciudad()
    log.info("Consultando clima: %s", ciudad)
    payload = None
    try:
        payload = obtener_clima(ciudad)
    except Exception:
        pass
    if payload:
        _publicar_visual(payload)
        return payload["summary"]
    state.set_info(f"No pude obtener clima de {ciudad}")
    webbrowser.open(f"https://www.google.com/search?q=clima+{ciudad.replace(' ', '+')}")
    return f"No pude obtener el clima de {ciudad}. Abriendo Google."


def respuesta_offline(comando):
    cl = comando.lower().strip()
    if cl in ["hora", "que hora", "dime la hora"]:
        return decir_hora()
    if cl in ["fecha", "que dia", "a que estamos"]:
        return decir_fecha()
    if cl in ["ayuda", "que puedes hacer", "que sabes hacer", "comandos"]:
        return _mostrar_ayuda()
    return "Estoy en modo offline. Solo puedo responder consultas basicas sin conexion."


def dispatcher_local(comando):
    global _comando_actual, _core
    cl = comando.lower().strip()
    _set_comando(comando)

    if _profile is not None:
        try:
            _profile.log_interaction(kind="command", text=comando)
        except Exception:
            pass

    if cl.startswith("escribe ") or cl.startswith("escribir "):
        texto = cl.replace("escribe ", "").replace("escribir ", "").strip()
        return escribir_texto(texto) if texto else "Dime que escribo."

    if cl.startswith("proyecto ") or cl.startswith("cambia a ") or cl.startswith("cambiar a "):
        for prefijo in ["proyecto ", "cambia a ", "cambiar a "]:
            if cl.startswith(prefijo):
                nombre = cl[len(prefijo):].strip()
                if nombre and _core:
                    return _core.set_project(nombre)
    if cl == "proyecto":
        if _core:
            p = _core.list_projects()
            a = _core.get_active_project()
            return f"Proyectos: {', '.join(p)}. Activo: {a}."
    if "progreso" in cl:
        for palabra in cl.split():
            if palabra.isdigit():
                if _core:
                    return _core.update_progress(int(palabra))
        if _core:
            return f"Progreso actual: {_core.get_progress()}%"

    if cl.startswith("tarea ") or cl.startswith("agrega tarea "):
        desc = cl.replace("tarea ", "").replace("agrega tarea ", "").strip()
        if desc and _core:
            t = _core.add_task(desc)
            return f"Tarea registrada: {desc}"
    if cl in ["tareas", "mis tareas", "que tareas tengo"]:
        if _core:
            tasks = _core.get_tasks()
            if not tasks:
                return "No hay tareas pendientes."
            activas = [t for t in tasks if not t.get("completado")]
            if not activas:
                return "Todas las tareas completadas."
            return "Tareas: " + " | ".join(
                f"{i + 1}. {t['descripcion']} ({t.get('progreso', 0)}%)"
                for i, t in enumerate(activas[:5])
            )
    if cl.startswith("completa tarea "):
        try:
            idx = int(cl.replace("completa tarea ", "").strip()) - 1
            if _core:
                return _core.complete_task(idx)
        except ValueError:
            pass

    clima_triggers = [
        "tiempo en ", "clima en ", "temperatura en ",
        "que tiempo hace en ", "como esta el clima en ", "como esta el tiempo en ",
        "que clima hace en ", "clima de ", "tiempo de ", "temperatura de ",
    ]
    if any(x in cl for x in clima_triggers):
        return decir_clima(extraer_ciudad_clima(comando))
    if cl.startswith("clima ") or cl.startswith("tiempo ") or cl.startswith("temperatura "):
        return decir_clima(extraer_ciudad_clima(comando))
    if cl in ["tiempo", "clima", "que tiempo", "como esta el clima", "que clima hace"]:
        return decir_clima()

    if any(cl.startswith(p) for p in [
        "ir a ", "ruta a ", "trafico a ", "tráfico a ",
        "llevame a ", "llévame a ", "como llegar a ", "cómo llegar a "
    ]):
        try:
            return obtener_ruta(comando)
        except Exception:
            return "No pude calcular la ruta."

    if "noticias" in cl or "titulares" in cl or "ultima hora" in cl:
        try:
            return abrir_noticias(_extraer_tema_noticias(comando))
        except Exception:
            return "No pude obtener noticias."

    if any(cl.startswith(t) for t in WEB_TRIGGERS):
        consulta = _extraer_tema(comando)
        return buscar_info_api(consulta)
    if cl.startswith("busca ") or cl.startswith("buscar "):
        consulta = cl.replace("busca ", "").replace("buscar ", "").strip()
        return buscar_en_web(consulta) if consulta else None

    if "volumen" in cl:
        for palabra in cl.split():
            if palabra.isdigit():
                return controlar_volumen(int(palabra))
        return controlar_volumen()

    if any(cl.startswith(p) for p in ["recuerdame ", "recordame ", "recordatorio ", "alarma "]):
        parsed = _parse_recordatorio(comando)
        if parsed:
            texto, mins = parsed
            return _agregar_recordatorio(texto, minutos=mins)

    if any(cl.startswith(p) for p in ["traduce ", "traducir ", "traduci "]):
        trad = _traducir(comando)
        if trad:
            state.set_info(trad)
            return trad

    if any(p in cl for p in ["ventanas", "minimiza todo", "minimizar todo", "trae"]):
        res = _control_ventanas(comando)
        if res:
            return res

    try:
        from kitian.kitian_plugins_loader import cargar_comandos_plugins
        plugins_cmds = cargar_comandos_plugins()
        for cmd_name, cmd_fn in plugins_cmds.items():
            if cl == cmd_name or cl.startswith(cmd_name + " "):
                if callable(cmd_fn):
                    args = comando[len(cmd_name):].strip() if len(comando) >= len(cmd_name) else ""
                    try:
                        result = cmd_fn(args)
                    except TypeError:
                        result = cmd_fn()
                    return _coerce_text_response(result)
                return _coerce_text_response(cmd_fn)
    except Exception as e:
        log.warning("Plugins dispatcher error: %s", e)

    COMANDOS_DIRECTOS = {
        "musica": abrir_musica,
        "spotify": abrir_musica,
        "reproduce": abrir_musica,
        "pon musica": abrir_musica,
        "pon cancion": abrir_musica,
        "hora": decir_hora,
        "que hora": decir_hora,
        "dime la hora": decir_hora,
        "fecha": decir_fecha,
        "que dia": decir_fecha,
        "a que estamos": decir_fecha,
        "noticias": abrir_noticias,
        "youtube": abrir_youtube,
        "abre youtube": abrir_youtube,
        "google": abrir_google,
        "abre google": abrir_google,
        "busca en google": abrir_google,
        "chrome": abrir_chrome,
        "abre chrome": abrir_chrome,
        "calculadora": abrir_calculadora,
        "bloc de notas": abrir_bloc_notas,
        "notepad": abrir_bloc_notas,
        "explorador": abrir_explorador,
        "archivos": abrir_explorador,
        "carpetas": abrir_explorador,
        "suspender": suspender_pc,
        "apaga el equipo": suspender_pc,
        "dormir": suspender_pc,
        "captura": capturar_pantalla,
        "screenshot": capturar_pantalla,
        "pantalla": capturar_pantalla,
        "foto": capturar_pantalla,
        "volumen": lambda: controlar_volumen("estado"),
        "sube volumen": lambda: controlar_volumen("subir"),
        "baja volumen": lambda: controlar_volumen("bajar"),
        "mutea": lambda: controlar_volumen("mutear"),
        "silencio": lambda: controlar_volumen("mutear"),
        "click": hacer_click,
        "clic": hacer_click,
        "minimiza": minimizar_ventanas,
        "minimizar": minimizar_ventanas,
        "escritorio": minimizar_ventanas,
        "proyecto": _cmd_proyecto,
        "progreso": _cmd_progreso,
        "alquimista": lambda: _modo_red("alquimista"),
        "ontologo": lambda: _modo_red("ontologo"),
        "ontólogo": lambda: _modo_red("ontologo"),
        "conector": lambda: _modo_red("conector"),
        "poeta": lambda: _modo_red("poeta"),
        "fortaleza": lambda: _modo_red("fortaleza"),
        "fusion": lambda: _modo_red("fusion"),
        "fusión": lambda: _modo_red("fusion"),
        "ejecuta": _cmd_ejecutar,
        "terminal": lambda: os.system("start cmd"),
        "cmd": lambda: os.system("start cmd"),
        "descarga": _cmd_descargar,
        "email": lambda: _enviar_email(_comando_actual),
        "correo": lambda: _enviar_email(_comando_actual),
        "perfil": _ver_perfil,
        "ayuda": _mostrar_ayuda,
        "hola": lambda: "Hola, en que puedo ayudarte?",
        "buenos dias": lambda: "Buenos dias. En que te ayudo?",
        "buenas tardes": lambda: "Buenas tardes. Que necesitas?",
        "buenas noches": lambda: "Buenas noches. Que se te ofrece?",
        "gracias": lambda: "De nada, para eso estoy.",
        "como estas": lambda: "Estoy operativo y listo para ayudarte.",
        "quien eres": lambda: "Soy Kitian, tu asistente personal.",
    }

    for clave, fn in COMANDOS_DIRECTOS.items():
        if clave in cl:
            try:
                return _coerce_text_response(fn() if not callable(fn) else fn())
            except Exception as e:
                log.error("Error comando directo %s: %s", clave, e)
                return None
    return None


def _coerce_text_response(value, fallback="No entendi."):
    if value is None:
        return None
    if isinstance(value, str):
        return value
    if isinstance(value, (dict, list, tuple)):
        try:
            return json.dumps(value, ensure_ascii=False)
        except Exception:
            return fallback
    return str(value)


def procesar(comando):
    # Router semántico silencioso: resuelve local si hay match exacto
    try:
        from kitian.intent_router import get_router
        r = get_router().route(comando)
        if r.handler in {"reminder.create", "reminder.delete", "reminder.list"}:
            respuesta = _handle_reminder_command(comando, r)
            if respuesta:
                try:
                    state.visual_data["status"] = "Activo"
                    state.visual_data["color"] = COLORES["activo"]
                except Exception:
                    pass
                state.set_info(respuesta)
                log.info("Router local [%s]: %s -> %s", r.handler, comando[:60], respuesta[:60])
                # Guardar igual en perfil/memoria
                try:
                    if _profile is not None and comando:
                        _profile.log_interaction("command", comando, extra={"response": respuesta, "router": r.handler})
                except Exception:
                    pass
                hablar(respuesta)
                return
    except Exception:
        pass

    respuesta = dispatcher_local(comando)
    if respuesta:
        log.info("Dispatcher local: %s -> %s", comando[:60], respuesta[:60])
        state.visual_data["status"] = "Activo"
        state.visual_data["color"] = COLORES["activo"]
        state.set_info(respuesta)
        hablar(respuesta)
        return

    tools = []
    contexto = ""
    try:
        core = get_core()
        historial = core.get_context(4) if hasattr(core, "get_context") else []
        if historial:
            contexto = "Historial reciente:\n" + "\n".join(
                f"Usuario: {h['user']}\nKitian: {h['kitian']}" for h in historial
            ) + "\n\n"
    except Exception:
        pass

    prompt = (
        f"{contexto}Eres Kitian, sistema operativo asistencial. Estetica Jarvis. "
        "Tono tecnico, eficiente, directo. Datos > Palabras. "
        "Gestiona proyectos y tareas. "
        f"Usuario: '{comando}'\n"
        f"Herramientas: {json.dumps(tools, ensure_ascii=False)}\n"
        "Responde SOLO JSON: {\"funcion\": \"...\", \"argumento\": null, \"mensaje\": \"texto breve\"}. "
        "Si no es herramienta, funcion=\"charlar\"."
    )
    state.visual_data["status"] = "Pensando"
    state.visual_data["color"] = COLORES["pensando"]
    log.info("Procesando: %s", comando[:80])
    raw = consultar_ia(prompt)
    log.info("Prompt enviado: %s", comando[:60])
    if raw in ("[AUTH]", "[CONN]") or raw is None:
        log.warning("Modo offline activado por fallo de API")
        state.visual_data["status"] = "Activo"
        state.visual_data["color"] = COLORES["offline"]
        respuesta = respuesta_offline(comando)
        try:
            from kitian.kitian_core import get_core
            core = get_core()
            if hasattr(core, "add_context"):
                core.add_context(comando, respuesta)
        except Exception:
            pass
        state.set_info(respuesta)
        hablar(respuesta)
        return

    try:
        d = json.loads(raw)
    except json.JSONDecodeError:
        log.error("JSON invalido del modelo: %s", raw[:200])
        state.set_info("No entendi la respuesta. Intenta de nuevo.")
        hablar("No entendi la respuesta. Intenta de nuevo.")
        return

    func = d.get("funcion", "charlar")
    arg = d.get("argumento")
    msg = d.get("mensaje", "")

    respuesta = None
    if func in HERRAMIENTAS:
        info = HERRAMIENTAS[func]
        respuesta = info["fn"](arg) if info["arg"] else info["fn"]()

    if respuesta is None:
        respuesta = msg or "No entendi."

    try:
        from kitian.kitian_core import get_core
        core = get_core()
        if hasattr(core, "add_context"):
            try:
                core.add_context(comando, respuesta)
            except Exception:
                pass
    except Exception:
        pass

    state.visual_data["status"] = "Activo"
    state.visual_data["color"] = COLORES["activo"]
    state.set_info(respuesta)
    log.info("Dispatcher: %s -> %s", func, respuesta[:80])

    respuesta_final = respuesta

    try:
        if _profile is not None and comando:
            _profile.log_interaction("command", comando, extra={"response": respuesta_final})
            for key in ("crear", "abrir", "investigar", "buscar", "programar", "recordar"):
                if key in (comando or "").lower():
                    goals: List[Dict[str, Any]] = list(
                        _profile.get("memory.recent_goals", [])
                    )
                    goals.append(
                        {
                            "text": comando.strip(),
                            "ts": time.time(),
                            "keyword": key,
                        }
                    )
                    if len(goals) > 20:
                        goals = goals[-20:]
                    _profile.set("memory.recent_goals", goals)
                    break
    except Exception:
        pass

    try:
        from kitian.voice_flow import VoiceFlow
        VoiceFlow(tts_enabled=True, default_response_type="balanced").process_interaction(
            comando, respuesta_final
        )
    except Exception:
        try:
            hablar(respuesta_final)
        except Exception:
            pass


# Router local rápido para recordatorios / agenda (Capa 1)
def _handle_reminder_command(comando: str, route: "RouteDecision") -> str:  # noqa: F821
    cl = comando.lower()
    parsed = _parse_recordatorio(comando)
    if parsed:
        texto, mins = parsed
        if mins <= 0:
            return "Decime en cuántos minutos querés el recordatorio."
        return _agregar_recordatorio(texto, minutos=mins)
    if cl.startswith("lista ") or "lista de recordatorios" in cl or "mostrar recordatorios" in cl:
        return leer_pendientes()
    if cl.startswith("borra recordatorio") or cl.startswith("elimina recordatorio"):
        return "Para eliminar un recordatorio, decime el texto exacto o la posición en la lista."
    return "No pude interpretar el recordatorio. Probá de nuevo."


HERRAMIENTAS = {}

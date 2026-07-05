import os
import json
import sys
import time
import shutil
from pathlib import Path
from openai import OpenAI

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).with_name(".env"))
except Exception:
    pass

client = OpenAI(
    base_url=os.getenv("KN_BACKEND_URL", "https://generativelanguage.googleapis.com/v1beta/openai/"),
    api_key=os.getenv("KN_API_KEY", os.getenv("GEMINI_API_KEY", os.getenv("KITIAN_API_KEY", "missing"))),
    timeout=60.0,
)

MODOS = {
    "alquimista": """Actúa como un Alquimista del Lenguaje. Analiza el archivo `datos_red.json` actual.
Identifica los nodos que representan conceptos 'densos' (materia/tierra) y 'volátiles' (espíritu/aire).
Añade una propiedad `tipo` a cada nodo ('Tierra', 'Aire', 'Fuego', 'Agua') basándote en su significado esotérico
y sugiere nuevas aristas que conecten elementos opuestos para crear 'transmutaciones'.
Responde SOLO con el JSON completo actualizado, sin explicaciones ni markdown.""",

    "ontologo": """Actúa como un Ontólogo Estricto. Revisa el archivo `datos_red.json` actual.
Identifica nodos que sean sinónimos o redundantes (como 'Espejo' y 'Reflejo').
Fusiona estos nodos en uno solo, transfiere todas sus conexiones (aristas) al nodo resultante
y elimina los duplicados. Asegúrate de que no queden 'nodos huérfanos' (sin conexiones).
Responde SOLO con el JSON limpio, sin explicaciones ni markdown.""",

    "conector": """Actúa como un Conector de Ideas. Explora la red actual.
¿Qué dos nodos parecen estar desconectados pero comparten una relación simbólica oculta?
Propón 3 nuevas aristas (relaciones) que unan partes distantes de la red.
Justifica cada nueva arista con una breve explicación esotérica.
Luego, integra estas nuevas aristas en el archivo `datos_red.json`.
Responde SOLO con el JSON completo actualizado, sin explicaciones ni markdown. Las justificaciones deben ir dentro de cada arista como propiedad `justificacion`.""",

    "poeta": """Actúa como un Poeta Filósofo. Recorre el camino entre el nodo 'AGUA' y el nodo más lejano de la red.
Escribe una breve narrativa o meditación que conecte estos conceptos, siguiendo el camino de las aristas que los unen.
Haz que la explicación se sienta como un flujo constante de información.
Al final, sugiere un nuevo nodo que podría servir de 'núcleo' para esta historia.
Responde con dos secciones: [NARRATIVA] con el texto poético y [JSON] con el JSON actualizado incluyendo el nuevo nodo y sus aristas.""",

    "fortaleza": """Actúa como un Cartógrafo de la Fuerza Conceptual. Analiza el archivo `datos_red.json`.
Calcula la 'fuerza' de cada nodo basándote en:
1. Cuántas aristas entrantes y salientes tiene (centralidad).
2. La profundidad semántica del concepto (qué tan fundamental es).
Asigna una propiedad `fuerza` a cada nodo (valor numérico de 1 a 100).
Además, asigna un `peso` a cada arista (1 a 10) según la intensidad de la relación.
Responde SOLO con el JSON completo actualizado, sin explicaciones ni markdown.""",

    "fusion": """Actúa como un Arquitecto de Síntesis. Toma dos grafos (archivos JSON) que te voy a dar
y encuentra los puntos de unión entre ellos: nodos que representen el mismo concepto,
nodos complementarios, y aristas que puedan cruzarse para formar un tejido coherente.
Construye un NUEVO grafo unificado que contenga lo mejor de ambos, eliminando redundancias.
Responde SOLO con el JSON fusionado, sin explicaciones ni markdown.""",
}


def validar_red(red):
    if not isinstance(red, dict):
        return False, "La red debe ser un objeto JSON."
    if "nodes" not in red or "edges" not in red:
        return False, "La red debe contener nodes y edges."
    if not isinstance(red["nodes"], list):
        return False, "nodes debe ser una lista."
    if not isinstance(red["edges"], list):
        return False, "edges debe ser una lista."
    return True, "OK"


def cargar_red(ruta="datos_red.json"):
    if not os.path.exists(ruta):
        return {"nodes": [], "edges": []}
    with open(ruta, "r", encoding="utf-8") as f:
        return json.load(f)


def guardar_red(red, ruta="datos_red.json"):
    ok, msg = validar_red(red)
    if not ok:
        print(f"[!] No se guardó la red: {msg}")
        guardar_respuesta_cruda(json.dumps(red, indent=2, ensure_ascii=False))
        return False

    ruta = Path(ruta)
    tmp = ruta.with_suffix(ruta.suffix + ".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(red, f, indent=2, ensure_ascii=False)
    tmp.replace(ruta)
    print(f"[+] Red guardada en '{ruta}' ({len(red.get('nodes', []))} nodos, {len(red.get('edges', []))} aristas)")
    return True


def respaldar_red(ruta="datos_red.json"):
    ruta = Path(ruta)
    if ruta.exists():
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        backup = ruta.with_name(f"{ruta.stem}_backup_{timestamp}{ruta.suffix}")
        shutil.copy2(ruta, backup)
        print(f"[*] Respaldo creado: {backup}")
        return backup
    return None


def enviar_a_lm_studio(prompt, temperatura=0.7, max_tokens=4096):
    print("[...] Consultando a la IA en la nube...")
    try:
        response = client.chat.completions.create(
            model=os.getenv("KN_MODEL", "gemini-2.0-flash"),
            messages=[{"role": "user", "content": prompt}],
            temperature=temperatura,
            max_tokens=max_tokens,
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"[!] Error de conexión con API: {e}")
        print("[!] Verifica tus claves y conexión a internet en .env")
        return None


def limpiar_json(raw):
    """Extrae el JSON de la respuesta, limpiando markdown y texto extra."""
    raw = raw.strip()
    if "[JSON]" in raw:
        raw = raw.split("[JSON]", 1)[1].strip()
    if "```json" in raw:
        raw = raw.split("```json", 1)[1].split("```", 1)[0].strip()
    elif "```" in raw:
        raw = raw.split("```", 1)[1].split("```", 1)[0].strip()
    start = raw.find("{")
    end = raw.rfind("}")
    if start != -1 and end != -1 and end > start:
        raw = raw[start:end + 1]
    return raw.strip()


def aplicar_modo(modo, red_actual, extra_context=None):
    if modo not in MODOS:
        print(f"[!] Modo desconocido: {modo}")
        print(f"    Disponibles: {', '.join(MODOS.keys())}")
        return None

    prompt_base = MODOS[modo]
    red_json = json.dumps(red_actual, indent=2, ensure_ascii=False)

    prompt = f"""{prompt_base}

Aquí está el archivo `datos_red.json` actual:
```json
{red_json}
```"""

    if extra_context:
        prompt += f"\n\nContexto adicional: {extra_context}"

    if modo != "poeta":
        prompt += "\n\nIMPORTANTE: Responde ÚNICAMENTE con el JSON resultante. Nada de explicaciones fuera del JSON."

    raw = enviar_a_lm_studio(prompt)
    if not raw:
        return None

    json_str = limpiar_json(raw)
    try:
        nueva = json.loads(json_str)
        ok, msg = validar_red(nueva)
        if not ok:
            print(f"[!] Red inválida: {msg}")
            guardar_respuesta_cruda(json.dumps(nueva, indent=2, ensure_ascii=False))
            return None
        return nueva
    except json.JSONDecodeError as e:
        print(f"[!] Error al decodificar JSON: {e}")
        print(f"[!] Respuesta recibida (primeros 500 chars):\n{raw[:500]}")
        guardar_respuesta_cruda(raw)
        return None


def guardar_respuesta_cruda(raw):
    ruta = f"respuesta_cruda_{time.strftime('%Y%m%d_%H%M%S')}.txt"
    with open(ruta, "w", encoding="utf-8") as f:
        f.write(raw)
    print(f"[*] Respuesta cruda guardada en '{ruta}' para depuración")


def modo_interactivo():
    red = cargar_red()
    print(f"[*] Red cargada: {len(red.get('nodes', []))} nodos, {len(red.get('edges', []))} aristas")

    while True:
        print("\n" + "=" * 60)
        print("  ARQUITECTO DE CONOCIMIENTO - Modos disponibles:")
        print("=" * 60)
        print("  1. alquimista  - Clasificar nodos por elementos (Tierra/Aire/Fuego/Agua)")
        print("  2. ontologo    - Fusionar sinónimos y limpiar redundancias")
        print("  3. conector    - Descubrir conexiones ocultas entre nodos")
        print("  4. poeta       - Generar narrativa entre nodos distantes")
        print("  5. fortaleza   - Calcular fuerza de nodos y peso de aristas")
        print("  6. fusion      - Fusionar dos grafos en uno")
        print("  7. ver         - Mostrar red actual")
        print("  8. guardar     - Guardar red a archivo")
        print("  9. respaldar   - Crear backup de la red")
        print("  0. salir")
        print("-" * 60)
        cmd = input("Modo > ").strip().lower()

        if cmd in ("0", "salir", "exit", "q"):
            guardar_red(red)
            print("[*] Saliendo. Red guardada.")
            break

        elif cmd in ("7", "ver"):
            print(json.dumps(red, indent=2, ensure_ascii=False)[:2000])
            if len(json.dumps(red)) > 2000:
                print(f"\n... (truncado, {len(json.dumps(red))} bytes totales)")

        elif cmd in ("8", "guardar"):
            ruta = input("Nombre del archivo [datos_red.json]: ").strip() or "datos_red.json"
            guardar_red(red, ruta)

        elif cmd in ("9", "respaldar"):
            respaldar_red()

        elif cmd == "fusion" or cmd == "6":
            ruta2 = input("Ruta del segundo grafo JSON: ").strip()
            if not os.path.exists(ruta2):
                print(f"[!] No se encontró: {ruta2}")
                continue
            with open(ruta2, "r", encoding="utf-8") as f:
                red2 = json.load(f)
            extra = json.dumps(red2, indent=2, ensure_ascii=False)
            nueva = aplicar_modo("fusion", red, extra_context=f"Segundo grafo:\n```json\n{extra}\n```")
            if nueva:
                red = nueva
                guardar_red(red)

        elif cmd in ("1", "alquimista", "2", "ontologo", "3", "conector", "4", "poeta", "5", "fortaleza"):
            mapa = {
                "1": "alquimista", "2": "ontologo", "3": "conector",
                "4": "poeta", "5": "fortaleza",
                "alquimista": "alquimista", "ontologo": "ontologo",
                "conector": "conector", "poeta": "poeta", "fortaleza": "fortaleza",
            }
            modo = mapa.get(cmd, cmd)

            if modo == "poeta":
                raw = enviar_a_lm_studio(
                    f"""{MODOS['poeta']}

Aquí está el archivo `datos_red.json` actual:
```json
{json.dumps(red, indent=2, ensure_ascii=False)}
```"""
                )
                if raw:
                    print("\n" + "=" * 60)
                    if "[NARRATIVA]" in raw:
                        narrativa = raw.split("[NARRATIVA]")[1]
                        if "[JSON]" in narrativa:
                            narrativa = narrativa.split("[JSON]")[0]
                        print(narrativa.strip())
                    else:
                        print(raw[:3000])
                    print("=" * 60)

                    if "[JSON]" in raw:
                        json_str = raw.split("[JSON]")[1].strip()
                        json_str = limpiar_json(json_str)
                        try:
                            nueva = json.loads(json_str)
                            ok, msg = validar_red(nueva)
                            if not ok:
                                print(f"[!] No se pudo guardar la red poética: {msg}")
                                guardar_respuesta_cruda(raw)
                                continue
                            red = nueva
                            guardar_red(red)
                        except json.JSONDecodeError:
                            print("[!] No se pudo extraer JSON de la respuesta poética.")
            else:
                respaldar_red()
                nueva = aplicar_modo(modo, red)
                if nueva:
                    red = nueva
                    guardar_red(red)
        else:
            print("[!] Opción no válida")


def ejecutar_modo_directo(modo):
    if modo not in MODOS:
        print(f"[!] Modo desconocido: {modo}")
        return None
    red = cargar_red()
    respaldar_red()
    nueva = aplicar_modo(modo, red)
    if nueva:
        guardar_red(nueva)
    return nueva


if __name__ == "__main__":
    if len(sys.argv) > 1:
        modo = sys.argv[1].lower()
        if modo in MODOS:
            ejecutar_modo_directo(modo)
        elif modo == "escanear":
            from escaneo_inicial import main
            carpeta = sys.argv[2] if len(sys.argv) > 2 else "./mis_documentos"
            main(carpeta)
        else:
            print(f"Uso: python {sys.argv[0]} [modo]")
            print(f"Modos: {', '.join(MODOS.keys())}")
            print(f"Sin argumentos entra en modo interactivo.")
    else:
        modo_interactivo()

import os
import json
from openai import OpenAI

client = OpenAI(
    base_url=os.getenv("KN_BACKEND_URL", "https://generativelanguage.googleapis.com/v1beta/openai/"),
    api_key=os.getenv("KN_API_KEY", os.getenv("GEMINI_API_KEY", os.getenv("KITIAN_API_KEY", "missing"))),
)


def extraer_estructura(texto, nombre_archivo):
    prompt = f"""Eres un experto en simbolismo esoterico y analisis conceptual.
Analiza el siguiente texto del archivo '{nombre_archivo}' y extrae:
1. Conceptos clave (nodos) con su nombre y tipo elemental si aplica.
2. Relaciones entre conceptos (aristas).

Responde UNICAMENTE con JSON, sin markdown:
{{
  "nodes": [{{"id": "Concepto", "label": "Concepto", "archivo": "{nombre_archivo}"}}, ...],
  "edges": [{{"from": "Origen", "to": "Destino", "tipo": "relacion"}}, ...]
}}

Texto a analizar (primeros 3000 caracteres):
{texto[:3000]}"""

    try:
        response = client.chat.completions.create(
            model=os.getenv("KN_MODEL", "gemini-2.0-flash"),
            messages=[{"role": "user", "content": prompt}],
            temperature=0.4,
            max_tokens=2048,
        )
        raw = response.choices[0].message.content
        raw = raw.replace("```json", "").replace("```", "").strip()
        return json.loads(raw)
    except Exception as e:
        print(f"  [!] Error con {nombre_archivo}: {e}")
        return None


def main(carpeta_path):
    if not os.path.isdir(carpeta_path):
        print(f"[!] Carpeta no encontrada: {carpeta_path}")
        print("    Creando carpeta de ejemplo...")
        os.makedirs(carpeta_path, exist_ok=True)
        with open(os.path.join(carpeta_path, "ejemplo.txt"), "w", encoding="utf-8") as f:
            f.write("El agua es el principio de toda creación.\n"
                    "Del agua surge la tierra, y de la tierra el fuego interior.\n"
                    "El aire eleva el fuego hacia el cielo.\n"
                    "La sabiduría antigua conecta los cuatro elementos en un ciclo eterno.")
        print(f"    Archivo de ejemplo creado en '{carpeta_path}/ejemplo.txt'")

    grafo_total = {"nodes": [], "edges": []}
    archivos = [f for f in os.listdir(carpeta_path) if f.endswith((".txt", ".md"))]

    print(f"[*] Escaneando {len(archivos)} archivos en '{carpeta_path}'...")

    for i, archivo in enumerate(archivos, 1):
        ruta = os.path.join(carpeta_path, archivo)
        print(f"[{i}/{len(archivos)}] Procesando: {archivo}")
        with open(ruta, "r", encoding="utf-8") as f:
            contenido = f.read()

        if not contenido.strip():
            print("  [-] Archivo vacío, saltando.")
            continue

        data = extraer_estructura(contenido, archivo)
        if data:
            seen_ids = {n["id"] for n in grafo_total["nodes"]}
            for nodo in data.get("nodes", []):
                if nodo["id"] not in seen_ids:
                    grafo_total["nodes"].append(nodo)
                    seen_ids.add(nodo["id"])
            grafo_total["edges"].extend(data.get("edges", []))
            print(f"  [+] {len(data.get('nodes', []))} nodos, {len(data.get('edges', []))} aristas")

    with open("datos_red.json", "w", encoding="utf-8") as f:
        json.dump(grafo_total, f, indent=2, ensure_ascii=False)

    print(f"\n[+] Red inicial generada:")
    print(f"    {len(grafo_total['nodes'])} nodos")
    print(f"    {len(grafo_total['edges'])} aristas")
    print(f"    Guardada en 'datos_red.json'")


if __name__ == "__main__":
    import sys
    ruta = sys.argv[1] if len(sys.argv) > 1 else "./mis_documentos"
    main(ruta)

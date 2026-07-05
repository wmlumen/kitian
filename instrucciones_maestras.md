# Instrucciones Maestras para Kitian - Arquitecto de Conocimiento

## Modo Alquimista (Análisis Temático)
Usalo cuando la red sea muy plana y quieras darle un giro esoterico mas profundo.

> "Actua como un Alquimista del Lenguaje. Analiza el archivo `datos_red.json` actual.
> Identifica los nodos que representan conceptos 'densos' (materia/tierra) y 'volatiles' (espiritu/aire).
> Anade una propiedad `tipo` a cada nodo ('Tierra', 'Aire', 'Fuego', 'Agua') basandote en su significado esoterico
> y sugiere nuevas aristas que conecten elementos opuestos para crear 'transmutaciones'.
> Devuelve el JSON completo actualizado."

## Modo Ontologo (Limpieza y Refinamiento)
Usalo cuando la red tenga demasiados conceptos repetidos o ruido.

> "Actua como un Ontologo Estricto. Revisa el archivo `datos_red.json`.
> Identifica nodos que sean sinonimos o redundantes (como 'Espejo' y 'Reflejo').
> Fusiona estos nodos en uno solo, transfiere todas sus conexiones (aristas) al nodo resultante
> y elimina los duplicados. Asegurate de que no queden 'nodos huerfanos' (sin conexiones).
> Devuelve el JSON limpio."

## Modo Conector (Descubrimiento)
Usalo para encontrar conexiones no obvias entre conceptos.

> "Actua como un Conector de Ideas. Explora la red actual.
> Que dos nodos parecen estar desconectados pero comparten una relacion simbolica oculta?
> Propon 3 nuevas aristas (relaciones) que unan partes distantes de la red.
> Justifica cada nueva arista con una breve explicacion esoterica.
> Luego, integra estas nuevas aristas en el archivo `datos_red.json`."

## Modo Poeta (Narrativa)
Usalo para convertir la red en un texto de reflexion.

> "Actua como un Poeta Filosofo. Recorre el camino entre el nodo 'AGUA' y el nodo mas lejano de la red.
> Escribe una breve narrativa o meditacion que conecte estos conceptos, siguiendo el camino de las aristas que los unen.
> Haz que la explicacion se sienta como un flujo constante de informacion.
> Al final, sugiere un nuevo nodo que podria servir de 'nucleo' para esta historia."

## Modo Fortaleza (Pesos)
Usalo para que los nodos importantes aparezcan mas grandes en la visualizacion.

> "Actua como un Cartografo de la Fuerza Conceptual. Analiza el archivo `datos_red.json`.
> Calcula la 'fuerza' de cada nodo basandote en cuantas aristas tiene y su profundidad semantica.
> Asigna una propiedad `fuerza` a cada nodo (1 a 100).
> Asigna un `peso` a cada arista (1 a 10) segun la intensidad de la relacion."

## Modo Fusion
Para unir dos grafos distintos en uno solo.

> "Actua como un Arquitecto de Sintesis. Toma los dos grafos que te doy
> y encuentra los puntos de union entre ellos: nodos que representen el mismo concepto,
> nodos complementarios, y aristas que puedan cruzarse.
> Construye un NUEVO grafo unificado eliminando redundancias."

---

> Rutas canónicas del proyecto:
> - Windows: `C:\Temp\kitian`
> - WSL/Linux: `/mnt/c/Temp/kitian`
> Ejecutar todos los comandos desde la carpeta base correspondiente.

## Flujo de trabajo

1. ESCANEAR: `python escaneo_inicial.py ./mis_documentos`
2. ALCANZAR: `python arquitecto_conocimiento.py fortaleza` (calcula pesos)
3. REFINAR: `python arquitecto_conocimiento.py ontologo` (limpia duplicados)
4. CLASIFICAR: `python arquitecto_conocimiento.py alquimista` (asigna elementos)
5. CONECTAR: `python arquitecto_conocimiento.py conector` (descubre vinculos)
6. NARRAR: `python arquitecto_conocimiento.py poeta` (genera reflexion)
7. VISUALIZAR: Abrir `red_del_conocimiento.html` en el navegador

## Comandos de voz para Kitian

- "Kitian, indexa mis documentos" → Escanea carpeta y genera red
- "Kitian, limpia la red" → Modo Ontologo
- "Kitian, clasifica por elementos" → Modo Alquimista
- "Kitian, descubre conexiones" → Modo Conector
- "Kitian, genera una reflexion" → Modo Poeta
- "Kitian, muestra la red" → Abre visualizador
- "Kitian, abre [programa]" → Abre aplicacion
- "Kitian, que hay en [carpeta]" → Lista archivos

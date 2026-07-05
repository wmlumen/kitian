# KI-TIAN JARVIS 2150 — Arquitectura del Sistema

> Documento vivo de la arquitectura unificada de Kitian.  
> Estado: store central backend + store Zustand-like frontend + API HTTP unificada.

---

## 1. Visión general

Kitian es un asistente ejecutivo local sin dependencias de nube.  
Su arquitectura sigue el patrón JARVIS 2150:

- **Single Source of Truth (SSOT)** por capa:
  - Backend → `kitian.store.KitianStore` (`kitian_store`)
  - Frontend → `createStore()` en `nebula_web.html` (Zustand-like vanilla)
- **HTTP BFF** en `kitian_http_standalone_real.py`:
  - Expone el estado actualizado a UI/audio/clientes externos
  - Orquesta research stream (SSE), files, goals, memory
- **Módulos backend locadores** (`kitian/`):
  - `dispatcher.py`: router local + plugins
  - `assistant_profile.py`: perfil de usuario e interacciones
  - `preference_engine.py`: adaptación de tono y preferencias
  - `file_manager.py`: administración segura de archivos
  - `goal_tree.py`: árbol de objetivos
  - `memory_engine.py`: memoria viva multicapa
  - `director.py`: modo director 0-3 (Manual / Asistido / Autónomo / Emergencia)
  - `research_orchestrator.py`: investigaciones en streaming

---

## 2. Estado central (`kitian/store.py`)

Objetivo: un único store en backend al que todos los módulos pueden escribir.

Estructura mínima del estado (campos principales):

```json
{
  "core": {
    "connected": false,
    "mode": "IDLE",
    "status": "offline",
    "via": "-",
    "searching": false,
    "latencyMs": null
  },
  "priorities": {
    "cpu": 0,
    "ram": 0,
    "disk": 0,
    "netDown": 0,
    "netUp": 0
  },
  "memory": {
    "interactions": 0,
    "keywords": [],
    "activeGoal": null,
    "recent": []
  },
  "inputs": {
    "lastCommand": null,
    "lastResponse": null,
    "voiceMode": "PUNCTUAL",
    "listening": false
  },
  "director": {
    "mode": 0,
    "label": "Manual",
    "lastExplanation": null,
    "audit": []
  },
  "goalTree": {
    "active": null,
    "branches": [],
    "status": "IDLE"
  },
  "emotional": {
    "claridad": 85.0,
    "carga": 15.0,
    "riesgo": "Bajo",
    "entropia": 20.0
  },
  "perception": {
    "motion": 0,
    "gesture": "NONE",
    "cursor": null
  },
  "updatedAt": "HH:MM:SS"
}
```

Reglas:
- Todo cambio pasa por `kitian_store.merge(patch)`.
- `snapshot_from_profile(profile)` sincroniza memoria/perfil cuando se recarga el perfil.
- Los listeners del store se usan para eventos críticos (emotional, director mode).
- No se permite múltiples stores escribiendo el mismo namespace de forma no coordinada.

---

## 3. Backend HTTP (`kitian_http_standalone_real.py`)

Responsabilidades:
- Exponer endpoints REST para consumo del frontend y clientes externos.
- Reenviar eventos de research por **SSE** (`/api/research/stream`).
- Centralizar lecturas del estado (`/api/state/snapshot`) y parches (`/api/state/merge`).

### 3.1 Endpoints read

| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/api/status` | Estado básico y binding |
| GET | `/api/system` | Métricas CPU/RAM/disk/net + actualiza `kitian_store.priorities` |
| GET | `/api/health` | Salud del sistema |
| GET | `/api/emotional` | Estado emocional desde el store (fallback `state.py`) |
| GET | `/api/state/snapshot` | Estado completo de `kitian_store` |
| GET | `/api/files/list` | Listar directorios |
| GET | `/api/files/open` | Abrir archivo |
| GET | `/api/files/search` | Buscar archivos |
| GET | `/api/files/move` | Mover archivo |
| GET | `/api/files/delete` | Eliminar archivo |
| GET | `/api/files/note` | Crear nota |
| GET | `/api/profile` | Perfil + preferencias + directorio actual |
| GET | `/api/memory/snapshot` | Snapshot de memoria |
| GET | `/api/memory/recent` | Interacciones recientes |
| GET | `/api/memory/keywords` | Keywords principales |
| GET | `/api/goals/list` | Lista de objetivos |
| GET | `/api/goals/advance` | Avanzar objetivo |
| GET | `/api/goals/complete` | Completar objetivo |
| GET | `/api/director/mode` | Modo actual del director |
| GET | `/api/director/explain` | Explicación y auditoría del director |
| GET | `/api/research/stream` | Streaming SSE de hallazgos |
| GET | `/api/ai-status` | Procesos IA detectados |

### 3.2 Endpoints write

| Método | Ruta | Descripción |
|--------|------|-------------|
| POST | `/api/state/merge` | Parche parcial sobre el store |
| POST | `/api/command` | Comandos locales / research / fallback Hermes |
| POST | `/api/research` | Controlar research (start/pause/resume/close) |
| POST | `/api/director/set_mode` | Cambia modo director y lo sincroniza al store |
| POST | `/api/goals/interpret` | Interpretar texto como objetivo |

Reglas de escritura:
- `/api/state/merge` acepta cualquier objeto parcial y lo aplica con `merge()`.
- `/api/director/set_mode` además llama a `get_director().set_mode(mode)` y guarda `directorMode` en el store.
- `/api/system` actualiza `priorities` automáticamente con CPU/RAM/disk en cada respuesta.

### 3.3 Backpressure y timeouts

- `/api/command` usa dispatcher con timeout 3s; fallback Hermes 20s.
- Research stream: suscriptores en cola circular (`queue_buf`), limpieza con `discard` caídos.
- SSE no tiene backpressure TCP avanzada; producción requiere conexión persistente controlada.

### 3.4 CORS + cache

Todas las respuestas JSON usan:
- `Access-Control-Allow-Origin: *`
- `Content-Type: application/json; charset=utf-8`
- `Cache-Control: no-store`

HTML: `no-store, no-cache, must-revalidate, max-age=0`.

---

## 4. Estado frontend (`nebula_web.html`)

Se usa un patrón Zustand-like vanilla:

```js
const useStore = createStore({
  core: { connected: false, mode: 'IDLE', status: 'offline', via: '-', searching: false },
  priorities: { cpu: 0, ram: 0, disk: 0 },
  memory: { interactions: 0, keywords: [], recent: [] },
  inputs: { lastCommand: null, lastResponse: null, voiceMode: 'PUNCTUAL', listening: false },
  directorMode: 0,
  director: { mode: 0, label: 'Manual', lastExplanation: null, audit: [] },
  goalTree: { active: null, branches: [], status: 'IDLE' },
  emotional: { claridad: 85, carga: 15, riesgo: 'Bajo', entropia: 20 },
  perception: { motion: 0, gesture: 'NONE', cursor: null },
  updatedAt: ''
});
```

Eventos consumidos:
- Mousemotion → `perception.motion`, selección de cuadrícula activa.
- Comandos → `core.searching = true/false` según envío/respuesta.
- `/api/profile` → inicializa `memory.interactions`, `keywords`, `goalTree`.
- `/api/system` y `/api/emotional` → mantienen `priorities` y `emotional`.

El frontend expone un **HUD 5x**:
- Panel métrico (CPU/RAM/disk/red)
- Centro canvás (percepción + pulso)
- Derecha: métricas avanzadas + log
- Abajo: estado emocional (claridad/carga/riesgo/entropía)
- Comandos + feedback directo

---

## 5. Puente de sesión (navegador)

Diseño propuesto:
- Reutilizar sesión de Gemini/GitHub del navegador cuando esté logueado.
- No almacenar credenciales en Kitian.
- Pasar únicamente `cookies` o tokens efímeros en RAM.
- Flujo:
  1. Detectar sesión activa en navegador (Browser Session Bridge)
  2. Obtener cookie/token limitado(s) al dominio del servicio.
  3. Usarlo en la petición de research con expiración controlada.
  4. Limpiar token al cerrar la investigación.

Segmento “Zero Trust”:
- Todo tráfico research atraviesa router JARVIS/URI.
- No hay credenciales en disco ni en el store.

---

## 6. Capa de percepción multimodal

Entradas soportadas hoy:
- Mouse (posición/gestos)
- Teclado (comandos)
- Audio (micrófono; comandos por voz)
- Cámara (si `voice/video`/embeddings están disponibles)

Representación interna:
- `perception.motion` → nivel de actividad (0-1)
- `perception.gesture` → “NONE” / nombre del gesto
- `perception.cursor` → objeto de posición/sector cuando el canvas está activo

Regla:
- Solo se escribe en `store.perception` desde un único productor (loop de render HUD).

---

## 7. Modo Director 0-3

- 0 Manual — usuario ejecuta libremente
- 1 Asistido — sugerencias suaves, sin bloqueos
- 2 Autónomo — ejecuta acciones directas con confirmación post
- 3 Emergencia — control total del sistema (prompt override/admin)

Sincronización:
- POST `/api/director/set_mode` → escribe en store y en módulo `director.py`.
- GET `/api/director/explain` → devuelve última explicación y auditoría.
- Frontend muestra el modo en el panel “Director”.

---

## 8. Research

Stack:
- `research_orchestrator.py` como orquestador.
- `research_outside` ejecuta scraping/búsqueda fuera del proceso local.
- `stream_manager.py` mantiene cola de eventos SSE.
- `/api/research/stream` entrega eventos tipo:
  - `research:init` (estado inicial)
  - `research:update` (hallazgo)
  - `research:end`

---

## 9. Reglas generales de desarrollo

- Única fuente de verdad por capa.
- No duplicar estado entre módulos legacy y store.
- Usar facade `SharedState` solo como puente hacia `kitian_store`.
- Toda mutación del estado visible pasa por `merge()`.
- No crear stores locales por módulo.
- No almacenar credenciales en disco.

---

## 10. Roadmap corto (pendiente inmediata)

1. Reemplazar todos los `state.set_info()` y `state.set()` remotos por writes al store central.
2. Agregar tests unitarios básicos de store (thread-safety, merge, snapshot).
3. Validar en runtime que ningún endpoint nuevo escapa de `kitian_store`.
4. Definir un único escritor por namespace (`director`, `emotional`) para evitar merges cruzados.

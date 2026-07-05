# J.A.R.V.I.S. X20 - Neural Command Core
### Protocolo KI-TIAN // Stark Industries Tactical Interface

El **Kitian HUD X20** es una interfaz de telemetría de quinta generación diseñada para la monitorización total del entorno digital. Basado en la arquitectura de Stark Industries, este núcleo de comando fusiona inteligencia artificial con visualización táctica en tiempo real.

## 1. Arquitectura Visual
El sistema utiliza paneles flotantes sin bordes con brillo ambiental cibernético y marcadores de esquina.
*   **Modo Compacto (1/4 de pantalla):** Ubicado lateralmente para monitorización persistente mientras se realizan otras tareas.  
*   **Modo Expandido (Pantalla Completa):** Despliegue total de todos los módulos de diagnóstico.

## 2. Componentes y Módulos

### A. Reactor ARC Central
**Nombre técnico:** Renderizado de Vectores en Coordenadas Polares y Arcos de Barrido.
*   **Lógica Funcional:** Convierte el radio (R) y ángulo (θ) en coordenadas cartesianas (X, Y) para posicionar elementos en rotación.
*   **Sincronización de CPU:** La velocidad de rotación de sus 12 anillos depende directamente de la carga del procesador.
*   **Estados de Ánimo:** Cambia de color según el estado del asistente (Activo, Escuchando, Pensando, Hablando).
*   **Semaforización de Procesos:** Muestra los nombres de los programas que más consumen recursos en el anillo interior.
    *   🟢 **Verde:** Operación Nominal (<5% CPU)
    *   🟡 **Naranja:** Carga Activa (>10% CPU)
    *   🔴 **Rojo:** Sobrecarga / Proceso Crítico (>20% CPU)
*   **Alerta Crítica:** Si el CPU supera el 85%, el reactor entra en modo de alerta roja.
*   **Efecto Habla:** Pulsa ondas de luz concéntricas sincronizadas con la salida de voz.

### B. Red Neuronal de Procesos
Representa el cerebro del sistema operativo.
**Nombre técnico:** Efecto Constelación / Grafo Dinámico de Partículas.
*   **Matemática de Enlace:** Utiliza el Teorema de Pitágoras para calcular la Distancia Euclidiana entre procesos. Si la distancia es < 45px, se crea una sinapsis (línea).
*   **Monitorización Real:** Muestra los procesos activos del PC como nodos interconectados.
*   **Relaciones:** Traza líneas de conexión entre procesos que comparten la misma carpeta o relación Padre-Hijo (PID/PPID).
*   **Código de Colores:** 
    *   **Cian:** Reposo.
    *   **Ámbar:** Actividad moderada.
    *   **Rojo:** Proceso de alto consumo.
*   **Interactividad:** Al hacer clic en un nodo, se muestra la ruta del ejecutable en la consola.

### C. Entorno y Red (Globo 3D)
**Nombre técnico:** Globo de Estructura de Alambre 3D con Proyección Ortográfica.
*   **Lógica de Rotación:** Aplica matrices de rotación sobre trigonometría esférica para aplanar la profundidad (Z) en un plano 2D.
*   **Globo Wireframe:** Representación 3D de la Tierra en rotación.
*   **Geolocalización:** Marca tu posición actual (basada en IP) con un punto rojo.
*   **Tráfico Global:** Mapea las IPs de conexiones externas entrantes como puntos amarillos.
*   **Pulsos de Datos:** Muestra líneas de arco (Beziér) con pulsos de luz blanca que viajan desde la IP de origen hacia tu ubicación. El tamaño del pulso depende del volumen de datos transferidos.

### D. Sistemas Centrales (Telemetría)
Datos puros de hardware.
*   Lectura en tiempo real de **CPU**, **RAM**, **Almacenamiento** y estado de la **Batería**.

### E. Radar de Amenazas y Analítica
*   **Radar:** Barrido circular que detecta nuevas conexiones de red establecidas.
*   **Analítica:** Gráficos históricos de rendimiento del CPU para predicción de carga.

### F. Vista Táctica (Nave 3D)
**Nombre técnico:** Renderizado de Malla de Estructura de Alambre 3D.
*   **Vigilancia de IA:** Muestra información en tiempo real sobre el motor de IA en uso (Ollama, LM Studio, etc.).
*   **Defensa Activa:** El caza estelar dispara láseres cuando se detectan IPs externas (intrusos) en el radar de amenazas.
*   **Geometría:** Vértices y aristas proyectados con matrices de rotación X/Y/Z.

### F. Consola de Comandos e Input
*   **Historial de Logs:** Muestra la actividad interna, errores y respuestas de la IA.
*   **Comandos Integrados:** Permite ejecutar acciones como `COLOR #HEX`, `LOGS`, `RESET` u `OPEN [PROCESO]`.
*   **Efecto de Escritura:** Brilla con el color del tema cuando detecta actividad en el teclado.

## 3. Funciones Interactivas

### Gestión de Paneles (Drag & Drop)
*   **Bloqueo de Seguridad:** El icono del candado (inferior derecha) impide movimientos accidentales.
*   **Personalización:** Cuando está desbloqueado (**X** verde), los paneles pueden arrastrarse libremente.
*   **Snap-to-Grid:** Los elementos se ajustan automáticamente a una rejilla de 20px para mantener el orden.
*   **Efecto Hover:** Los paneles aumentan ligeramente de tamaño y se iluminan al pasar el ratón por encima.
*   **Ghosting:** Durante el movimiento, los paneles se vuelven translúcidos para mejorar la visibilidad.

### Selección para Modo 1/4
*   **Doble Clic:** Al hacer doble clic sobre un panel, se selecciona si este debe aparecer o no en la versión compacta de la pantalla.
*   **Feedback Visual:** El borde del panel parpadea en blanco para confirmar que se ha guardado la preferencia.
*   **Chispas de Energía:**
    *   🔥 **Rojo:** Alarma de intrusión de red.
    *   ⚡ **Naranja:** Tarea o comando completado con éxito.

### Sistema de Persistencia
*   Todas las posiciones (tanto en modo compacto como expandido), colores de tema y estados de visibilidad se guardan automáticamente en `hud_layout.json`.
*   **Reset de Fábrica:** El botón `RESET` devuelve todos los elementos a su posición original con una animación de "vuelo" suavizada.

## 4. Comandos de Consola Detallados

| Comando | Función |
| :--- | :--- |
| `HELP` | Muestra la lista de comandos disponibles. |
| `COLOR #HEX` | Cambia el color global del HUD (ej: `COLOR #ff0000`). |
| `LOGS` | Filtra y muestra los últimos 5 eventos de seguridad/sistema de `kitian.log`. |
| `OPEN [NAME]` | Busca un proceso en la red neuronal y abre su carpeta en el explorador. |
| `RESET` | Restaura el layout original con animación. |
| `LIMPIAR` | Borra el historial de la consola visual. |
| `IA` | Muestra el estado del motor de inteligencia artificial local. |
| `UBICACION` | Muestra coordenadas de latitud y longitud actuales. |

## 5. Requerimientos de Datos
El HUD se alimenta de `SharedState`, una estructura de memoria compartida que recibe datos de:
1.  **psutil:** Para métricas de hardware y procesos.
2.  **socket:** Para monitorización de red.
3.  **ip-api:** Para geolocalización.
4.  **kitian_core:** Para sincronización de proyectos y progreso de tareas.

## 6. Estado de Desarrollo (Registro de Módulos)

### ✅ Implementado (100% Funcional)
*   Reactor ARC con semaforización de procesos y chispas de energía.
*   Red Neuronal con mapeo de PID/PPID y apertura de directorios.
*   Globo 3D con tráfico de red real (IPs externas) y arcos de datos.
*   Sistema de Glitch visual por carga de CPU o integridad crítica.
*   Persistencia de Layout (Posición 1/4 vs Expandida) y color de tema.
*   Control de voz asíncrono y alertas de seguridad auditivas.

### ⏳ Roadmap (Próximas Fases)
*   **Visión Computacional:** Detección facial y reconocimiento de objetos vía cámara.
*   **RAG:** Integración con base de datos vectorial para análisis de documentos locales.
*   **Full-Duplex:** Capacidad de interrumpir al asistente mientras habla.
*   **Smart Home:** Enlace con protocolos IoT (Zigbee/Matter).

---
*KI-TIAN X20 Neural Command Core · STARK INDUSTRIES QUANTUM LINK · © 2026 KEIM INDUSTRIES*
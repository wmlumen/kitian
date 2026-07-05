# Kitian Health Monitor

Archivos del paquete:

- `kitian_health_dashboard.html`: dashboard visual de salud.
- `kitian_health.json`: snapshot/histórico consumido por el dashboard.
- `kitian_health_probe.py`: generador/actualizador del JSON.

Uso rápido:

```powershell
cd C:\Temp\kitian
python kitian_health_probe.py
```

Modo continuo cada 10 segundos:

```powershell
python kitian_health_probe.py --watch 10
```

Servidor local para el HTML:

```powershell
python -m http.server 8080
```

Abrir:

- `http://localhost:8080/kitian_health_dashboard.html`

Qué revisa el probe:

- CPU, RAM y disco.
- `manifest.json`
- `hud_layout.json`
- `datos_red.json`
- plugins cargables
- conectividad con LM Studio
- errores recientes en `kitian.log`

Registro manual desde otros módulos:

```python
from kitian_health_probe import registrar_anomalia

registrar_anomalia(
    component="HUD",
    severity="HIGH",
    title="FPS bajo",
    detail="El promedio cayó por debajo de 25 FPS.",
    recommendation="Reducir partículas o bajar a 30 FPS.",
    source="kitian_hud.py",
)
```

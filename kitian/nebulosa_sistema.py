class NebulosaSistema:
    """Datos de sistema dibujados como una nebulosa de puntos/microred."""

    def __init__(self):
        self.particulas = []
        self._last_update = 0

    def estado_metricas(self, cpu, ram, disco):
        return {
            'cpu': max(0.0, min(100.0, float(cpu or 0.0))),
            'ram': max(0.0, min(100.0, float(ram or 0.0))),
            'disk': max(0.0, min(100.0, float(disco or 0.0))),
        }

    def seed(self, metricas):
        estado = self.estado_metricas(
            metricas.get('cpu'), metricas.get('ram'), metricas.get('disk')
        )
        carga = max(1, min(30, int(estado['cpu'] / 3.3)))

        base = [
            {'etiqueta': 'CPU', 'valor': estado['cpu'], 'x': 1.1, 'y': 0.5},
            {'etiqueta': 'RAM', 'valor': estado['ram'], 'x': 0.5, 'y': 0.25},
            {'etiqueta': 'DISCO', 'valor': estado['disk'], 'x': 0.35, 'y': 0.75},
            {'etiqueta': 'RED', 'valor': 18.0, 'x': 0.75, 'y': 0.4},
            {'etiqueta': 'IA', 'valor': 9.0, 'x': 0.8, 'y': 0.7},
            {'etiqueta': 'PWR', 'valor': 6.0, 'x': 0.2, 'y': 0.6},
        ]

        semillas = []
        for nodo in base:
            semillas.append({
                'x': nodo['x'],
                'y': nodo['y'],
                'peso': max(1, int(nodo['valor'] / 7)),
                'etiqueta': nodo['etiqueta'],
                'valor': nodo['valor'],
            })

        microparticulas = []
        objetivo = 34 + carga + len(semillas) * 4
        objetivo = min(objetivo, 180)

        existentes = list(self.particulas)
        for _ in range(objetivo - len(existentes)):
            microparticulas.append({
                'x': 0.0, 'y': 0.0,
                'vx': 0.0, 'vy': 0.0,
                'r': 0.6,
                'c': '#00f0ff',
                'alfa': 0.55,
            })

        microparticulas.extend(existentes)
        self.particulas = microparticulas
        return semillas

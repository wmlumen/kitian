import tkinter as tk
import tkinter.font as tkfont
import math
import random
import time
import psutil
import platform
import socket
import threading
import subprocess
import urllib.request
import json
import logging
import os
import ipaddress
from datetime import datetime
from pathlib import Path
from kitian.nebulosa_sistema import NebulosaSistema

ANCHO, ALTO = 1200, 720
CX, CY = ANCHO // 2, ALTO // 2 - 20

_hud_logs = []

COLORS = {
    "Activo":      ("#00e5ff", "#00ff88"),
    "Escuchando":  ("#00f0ff", "#0088ff"),
    "Pensando":    ("#cc44ff", "#ff88cc"),
    "Hablando":    ("#ffd000", "#ffaa00"),
    "Offline":     ("#555555", "#333333"),
    "Error":       ("#ff2a00", "#990000"),
}

FUNC_WORDS = ["ANALIZAR","ADAPTAR","APRENDER","DECIDIR","EJECUTAR"]

def _t(h):
    h = h.lstrip('#')
    r,g,b = int(h[0:2],16),int(h[2:4],16),int(h[4:6],16)
    return [f"#{r:02x}{g:02x}{b:02x}",
            f"#{int(r*.65):02x}{int(g*.65):02x}{int(b*.65):02x}",
            f"#{int(r*.40):02x}{int(g*.40):02x}{int(b*.40):02x}",
            f"#{int(r*.20):02x}{int(g*.20):02x}{int(b*.20):02x}",
            f"#{int(r*.10):02x}{int(g*.10):02x}{int(b*.10):02x}",
            f"#{int(r*.04):02x}{int(g*.04):02x}{int(b*.04):02x}"]

class KitianHUD:
    def __init__(self, shared_state=None):
        self.st = shared_state
        self.root = tk.Tk()
        self.root.title("KI - TIAN X20 - Neural Command Core")
        self.root.configure(bg="#010408")

        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        self._cw = max(int(sw * 0.30), 420)   # modo compacto: 30% ancho
        self._ch = sh - 10
        self._fw = sw                           # pantalla completa: 100%
        self._fh = sh
        self.root.title("")
        self.root.overrideredirect(True)
        self.root.attributes("-alpha", 0.99)
        self.root.attributes("-topmost", True)
        self.root.configure(bg="#010408")
        # Fondo sólido activado: eliminamos -transparentcolor para que no se transparente el fondo
        # Arrancar SIEMPRE en pantalla completa
        self.root.geometry(f"{self._fw}x{self._fh}+0+0")
        self.canvas = tk.Canvas(self.root, bg="#010408", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)

        self.canvas.bind("<Button-1>", self._on_click)
        self.canvas.bind("<B1-Motion>", self._on_drag)
        self.canvas.bind("<ButtonRelease-1>", self._on_release)
        self.canvas.bind("<Motion>", self._on_mouse_move)
        self.canvas.bind("<Double-Button-1>", self._handle_double_click)
        self.canvas.bind("<Button-3>", lambda e: self.root.destroy())

        self.estado = "Activo"
        self.prev_estado = "Activo"
        self.color = COLORS[self.estado][0]
        self.fotogramas = 0
        self.si = 99.4
        self.inicio = time.time()
        self._expanded = True   # arrancar siempre en pantalla completa
        self._locked = False
        self._focus_panel = None
        self._drag = None
        self._drag_off = {}
        self._panel_pos = {}
        self._panel_pos_exp = {}
        self._panel_vis = {}
        self._panel_bounds = {}
        self._flash_panels = {}
        self._scan_glitch = 0
        self._stress_test = False
        self._http_active = False
        self._active_profile = "operativo"
        self._filter_mode = "all"
        self._last_completed_frame = 0
        self._animating = False
        self.last_key_time = 0
        self.mx = -999
        self.my = -999
        self.cmd_history = []
        self.cmd_history_idx = -1
        self._reset_rect = (0, 0, 0, 0)
        self._lock_rect = (0, 0, 0, 0)
        self.cpu_hist = []
        self.ram_hist = []
        self.disk_hist = []
        self.cpu_val = 0.0
        self.ram_val = 0.0
        self.disk_val = 0.0
        self.net_val = 0.0
        self.ubica = "--"
        self.lat = 0.0
        self.lon = 0.0
        self.red_nodos = []
        self.red_aristas = []
        self.nodos = []
        self.conex_prev = []
        self.ia_local = "LM Studio"
        self.ia_estado = "OK"
        self.sub = ""
        self.logs_terminal = type("L", (), {"_items": [], "append": lambda self, x: self._items.append(x) or self._items.__setitem__("_items", self._items[-120:]), "clear": lambda self: self._items.__setitem__("_items", [])})()
        self.visual_data = {}
        self.lt = time.time()
        self.fps = 60
        self.ang_r = 0.0
        self.sub = 'KI - TIAN: "Sistemas estables."'
        self.particulas = []
        self.lasers = []
        self._locked = True
        self._xc = 0
        self._yc = 0
        self._drag = None
        self._drag_off = {}
        self._lock_rect = (0,0,0,0)
        self._reset_rect = (0,0,0,0)
        self.last_key_time = 0
        self._stress_test = False
        self.mx = 0
        self.my = 0

        # Sistema de pestañas
        self._tabs = ["REACTOR", "RESPUESTA", "SISTEMA", "RED", "ENTORNO", "ALERTAS"]
        self._active_tab = "REACTOR"
        self._tab_rects = {}       # {nombre_tab: (x1,y1,x2,y2)}
        self._last_response = ""  # última respuesta IA para mostrar en tab RESPUESTA

        # Indicador de estado HTTP (puerto 8080)
        self._http_active = False
        try:
            _s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            _s.settimeout(0.3)
            _s.connect(("127.0.0.1", 8080))
            _s.close()
            self._http_active = True
        except Exception:
            self._http_active = False
        
        self._security_alert_played = False
        self._scan_glitch = 0
        self._last_completed_frame = 0 # Para chispas naranjas
        self._flash_panels = {} # Temporizadores para parpadeo de paneles
        self._ip_map_pts = {} # Mapeo persistente de IP -> (lat, lon)
        self._panel_bounds = {}
        self._header_chip_rects = {}
        self._focus_panel = None
        self._filter_mode = "all"
        self._active_profile = "deportivo"
        self.nebulosa_particulas = []
        self.nebulosa_etiquetas = [
            {"nombre": "CPU", "peso": 1.0, "color": "#00f0ff"},
            {"nombre": "RAM", "peso": 1.0, "color": "#ffd000"},
            {"nombre": "DISCO", "peso": 0.8, "color": "#ff9d00"},
            {"nombre": "RED", "peso": 0.9, "color": "#00ff88"},
            {"nombre": "IA", "peso": 0.7, "color": "#cc44ff"},
            {"nombre": "TERMO", "peso": 0.6, "color": "#00e5ff"},
        ]
        self._nebulosa_base = 0.0

        # Sistema de Animación de Vuelo
        self._animating = False
        self._anim_start_time = 0
        self._anim_duration = 0.8  # Segundos que dura el vuelo
        self._anim_start_pos = {}
        self._anim_target_pos = {}

        self.logs_terminal = [
            "[SISTEMA]: KI - TIAN X20 iniciado",
            "[SISTEMA]: Telemetria activa",
            "[INFO]: Doble click expandir | Click derecho salir"
        ]
        self.visual_data = {
            "kind": "idle",
            "title": "Centro de control",
            "summary": "Esperando comando de voz o texto.",
            "metrics": [],
            "sources": [],
            "actions": [],
            "context": [],
            "updated_at": "--:--:--",
        }

        self.ang_globo = 0.0
        self.lat = -25.33
        self.lon = -57.51
        self.ubica = "Buscando..."
        self.pts_tierra = [
            {"n": "MALIBU", "lat": 34.025, "lon": -118.779},
            {"n": "ORBITA", "lat": 0.0, "lon": 45.0},
            {"n": "NUCLEO STARK", "lat": 40.712, "lon": -74.006},
            {"n": "SERVER FARM", "lat": 37.333, "lon": -121.89}
        ]

        self.ang_caza = 0.0
        self.caza_v = [(0,0,35),(12,0,-15),(-12,0,-15),(0,6,-15),(0,-4,-15),(30,-2,-8),(-30,-2,-8),(0,15,-25)]
        self.caza_e = [(0,1),(0,2),(0,3),(0,4),(1,5),(5,2),(2,6),(6,1),(1,3),(2,3),(1,4),(2,4),(3,7),(7,4),(7,0)]

        self.barrido = 0.0
        self.radar_objs = []
        self.conex_prev = set()
        self.nodos = []
        self.procs_alto = []
        self.ia_local = "Kitian AI Core"
        self.ia_estado = "STANDBY"

        self.cpu_val = 0
        self.ram_val = 0
        try:
            self.disk_val = psutil.disk_usage('/').percent if platform.system() != 'Windows' else psutil.disk_usage('C:\\').percent
        except:
            self.disk_val = 0
        self.so = platform.system()
        self.cpu_n = psutil.cpu_count(logical=True)
        try:
            self.local_ip = socket.gethostbyname(socket.gethostname())
        except:
            self.local_ip = "127.0.0.1"

        self.cpu_hist = [0.0] * 45
        self.ram_hist = [0.0] * 45
        self.disk_hist = [float(self.disk_val)] * 45
        try:
            n = psutil.net_io_counters()
            self.last_recv = n.bytes_recv
            self.last_sent = n.bytes_sent
        except:
            self.last_recv = 0
            self.last_sent = 0
        self.net_down = "0 KB/s"
        self.net_up = "0 KB/s"
        self._current_dr = 0

        self.layout_file = Path(__file__).parent / "hud_layout.json"
        
        # ── Layout adaptativo: 3 columnas relativas al tamaño real de pantalla ──
        # Columnas: izq=col_l, centro=col_c, derecha=col_r
        # Filas: fila1..fila5 repartidas en la altura disponible (quitando cabecera)
        _W = self._fw
        _H = self._fh
        _HDR = 100          # altura cabecera reservada
        _FOOT = 120         # altura pie (console + input)
        _BODY = _H - _HDR - _FOOT   # altura disponible para paneles de cuerpo
        _COL_W = _W // 3   # ancho de cada columna
        _PAD = 16           # margen interno

        # Columna izquierda
        col_l = _PAD
        # Columna central (centrada sobre el reactor)
        col_c = _COL_W + _PAD
        # Columna derecha
        col_r = 2 * _COL_W + _PAD

        # Filas del cuerpo divididas equitativamente
        row1 = _HDR + _PAD
        row2 = _HDR + _PAD + _BODY // 4
        row3 = _HDR + _PAD + _BODY * 2 // 4
        row4 = _HDR + _PAD + _BODY * 3 // 4

        self.default_pos = {
            "core":      (col_l, row1),
            "neural":    (col_l, row2),
            "nebula":    (col_l, row3),
            "env":       (col_l, row4),
            "pred":      (col_r, row1),
            "threat":    (col_r, row2),
            "diag":      (col_r, row3),
            "reactor":   (col_c, row1),
            "tactical":  (col_c, row3),
            "console":   (_PAD, _H - _FOOT + 10),
            "input_bar": (_W - 380, _H - _FOOT + 10),
        }
        self.default_pos_exp = self.default_pos.copy()  # mismo layout, mismo grid

        self.default_vis = {
            "core":      "full",
            "neural":    "full",
            "nebula":    "full",
            "env":       "full",
            "pred":      "full",
            "threat":    "full",
            "diag":      "full",
            "reactor":   "full",
            "input_bar": "full",
            "console":   "full",
            "tactical":  "full",
        }

        self.theme_color = "#00e5ff"
        saved_data = self._load_layout()
        self._panel_pos = self.default_pos.copy()
        self._panel_pos_exp = self.default_pos_exp.copy()
        self._panel_vis = self.default_vis.copy()
        if saved_data:
            self.theme_color = saved_data.get("theme_color", "#00e5ff")
            # Solo restaurar posiciones si son del mismo layout expandido
            # (ignoramos layouts viejos del modo compacto que estén fuera de pantalla)
            saved_positions = saved_data.get("positions", {})
            if any(x < 100 and y < 100 for x, y in saved_positions.values()):
                self._panel_pos.update(saved_positions)
            self._panel_pos_exp.update(saved_data.get("positions_exp", {}))
            self._panel_vis.update(saved_data.get("visibility", {}))
        self._update_all_colors(self.theme_color)
        self._sanitize_layout()

        self._crear_entrada()
        threading.Thread(target=self._geolocalizar, daemon=True).start()
        threading.Thread(target=self._escanear_sistema, daemon=True).start()
        self.root.update_idletasks()
        self.loop()
        self.root.mainloop()

    def _toggle_max(self, e=None):
        self._expanded = not self._expanded
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        if self._expanded:
            w, h = self._fw, self._fh
            x, y = 20, 20
            self.root.attributes("-alpha", 0.99)
        else:
            w, h = self._cw, self._ch
            x, y = sw - w - 10, 20
            self.root.attributes("-alpha", 0.96)
        self.root.geometry(f"{w}x{h}+{x}+{y}")
        self._sanitize_layout()
        self.canvas.config(width=w, height=h)
        self.logs_terminal.append(f"{'Pantalla completa' if self._expanded else 'Modo compacto'}")

    def _diagnostico_pantalla(self):
        """Verifica si la ventana está dentro de los límites visibles."""
        self.root.update_idletasks()
        wx, wy = self.root.winfo_x(), self.root.winfo_y()
        ww, wh = self.root.winfo_width(), self.root.winfo_height()
        sw, sh = self.root.winfo_screenwidth(), self.root.winfo_screenheight()
        msg = f"[SISTEMA]: Ventana en {wx},{wy} | Monitor: {sw}x{sh}"
        print(msg) # Salida a terminal para depuración
        if wx < 0 or wy < 0 or wx > sw or wy > sh:
            print("[ALERTA]: Ventana fuera de rango. Reubicando...")
            self.root.geometry(f"+{sw - ww - 20}+20")

    def _handle_double_click(self, e):
        """Determina si se muestra en 1/4 o expande la ventana."""
        panel_areas = {
            "core": (260, 160), "neural": (260, 180), "nebula": (260, 220),
            "env": (260, 210), "pred": (260, 170), "threat": (260, 190),
            "diag": (260, 200), "console": (self.root.winfo_width() - 420, 90),
            "reactor": (240, 240), "input_bar": (350, 50),
            "tactical": (200, 200)
        }
        pos_dict = self._panel_pos_exp if self._expanded else self._panel_pos
        # Ejecutar diagnóstico al hacer doble click también
        self._diagnostico_pantalla()
        for name, (bw, bh) in panel_areas.items():
            bx, by = pos_dict.get(name, (0, 0))
            if bx < e.x < bx+bw and by < e.y < by+bh:
                old_vis = self._panel_vis.get(name, "full")
                new_vis = "compact" if old_vis != "compact" else "full"
                self._panel_vis[name] = new_vis
                self._flash_panels[name] = self.fotogramas + 40 # Parpadeo por 40 frames
                self.logs_terminal.append(f"{name}: {'Visible en 1/4' if new_vis=='compact' else 'Solo Expandido'}")
                self._save_layout()
                return
        self._toggle_max(e)

    def _reset_layout(self):
        """Inicia la animación de vuelo hacia las posiciones de fábrica."""
        if self._animating: return
        
        self._animating = True
        self._anim_start_time = time.time()
        self._panel_vis = self.default_vis.copy()
        
        if self._expanded:
            self._anim_start_pos = self._panel_pos_exp.copy()
            self._anim_target_pos = self.default_pos_exp.copy()
        else:
            self._anim_start_pos = self._panel_pos.copy()
            self._anim_target_pos = self.default_pos.copy()
            
        self.logs_terminal.append("[SISTEMA]: Iniciando secuencia de reubicación...")

    def _set_filter_mode(self, mode):
        mode = str(mode or "all").lower()
        if mode not in {"all", "critical", "system", "network"}:
            mode = "all"
        self._filter_mode = mode
        self.logs_terminal.append(f"[HUD]: Filtro {mode}")

    def _panel_group(self, name):
        if name in {"core", "reactor", "tactical", "console"}:
            return "system"
        if name in {"env", "threat", "diag"}:
            return "network"
        return "general"

    def _panel_priority(self, name):
        alerts = self._build_alerts()
        warn_count = sum(1 for level, _ in alerts if level in {"WARN", "CRITICAL"})
        critical_count = sum(1 for level, _ in alerts if level == "CRITICAL")
        if name == "core":
            return "critical" if critical_count else ("warn" if warn_count else "normal")
        if name in {"threat", "console"}:
            return "warn" if warn_count else "normal"
        if name == "reactor":
            return "warn" if self.cpu_val >= 80 or self.ram_val >= 85 else "normal"
        return "normal"

    def _panel_allowed(self, name):
        if self._focus_panel and name not in {self._focus_panel, "input_bar"}:
            return False
        if self._filter_mode == "all":
            return True
        if self._filter_mode == "critical":
            return name in {"core", "threat", "console", "reactor", "input_bar"}
        return self._panel_group(name) == self._filter_mode or name == "input_bar"

    def _apply_profile(self, profile):
        profile = str(profile or "operativo").lower()
        profiles = {
            "operativo": {"show": {"core", "reactor", "env", "threat", "console", "input_bar", "tactical"}, "filter": "all"},
            "ia": {"show": {"pred", "tactical", "console", "input_bar", "core", "reactor"}, "filter": "all"},
            "seguridad": {"show": {"threat", "diag", "env", "console", "input_bar", "core"}, "filter": "critical"},
            "minimal": {"show": {"core", "pred", "console", "input_bar"}, "filter": "critical"},
        }
        cfg = profiles.get(profile)
        if not cfg:
            return False
        self._active_profile = profile
        self._focus_panel = None
        for name in self._panel_vis:
            self._panel_vis[name] = "full" if name in cfg["show"] else "hidden"
        self._panel_vis["input_bar"] = "compact"
        self._set_filter_mode(cfg["filter"])
        self.logs_terminal.append(f"[HUD]: Perfil {profile}")
        self._save_layout()
        return True

    def _on_click(self, e):
        # 1. Clic en pestañas
        for tab_name, (tx1, ty1, tx2, ty2) in self._tab_rects.items():
            if tx1 < e.x < tx2 and ty1 < e.y < ty2:
                self._active_tab = tab_name
                self.logs_terminal.append(f"[HUD]: Tab áctiva: {tab_name}")
                return

        # 2. Botón lock
        lx, ly, lx2, ly2 = self._lock_rect
        if lx < e.x < lx2 and ly < e.y < ly2:
            self._locked = not self._locked
            self.logs_terminal.append(f"Panel {'BLOQUEADO' if self._locked else 'DESBLOQUEADO'}")
            return

        # 4. Botón RST
        rx, ry, rx2, ry2 = self._reset_rect
        if not self._locked and rx < e.x < rx2 and ry < e.y < ry2:
            self._reset_layout()
            return

        # 5. Click en nodos de red neuronal (tab RED)
        if self._active_tab == "RED":
            for node in self.nodos:
                if math.hypot(e.x - node.get("ax", -999), e.y - node.get("ay", -999)) < node.get("r", 6) + 8:
                    self.logs_terminal.append(f"[PROC]: {node['name']} | PID: {node['pid']}")
                    self.logs_terminal.append(f" RUTA: {node.get('folder', 'Sistema')}")
                    return

        self._xc = e.x
        self._yc = e.y

    def _on_drag(self, e):
        if self._drag and not self._locked:
            ox, oy = self._drag_off[self._drag]
            nx, ny = e.x - ox, e.y - oy
            G = 20
            nx = round(nx / G) * G
            ny = round(ny / G) * G
            W, H = self.root.winfo_width(), self.root.winfo_height()
            sizes = {
                "core":   (260, 160),
                "neural": (260, 180),
                "nebula": (260, 220),
                "env":    (260, 210),
                "pred":   (260, 170),
                "threat": (260, 190),
                "diag":   (260, 200),
                "console": (W - 420, 90),
                "reactor": (240, 240),
                "input_bar": (350, 50),
                "tactical": (200, 200)
            }

            pw, ph = sizes.get(self._drag, (200, 100))
            nx = max(0, min(nx, W - pw))
            ny = max(0, min(ny, H - ph - 10))
            target_dict = self._panel_pos_exp if self._expanded else self._panel_pos
            target_dict[self._drag] = (nx, ny)
            return
        dx = e.x - self._xc
        dy = e.y - self._yc
        self.root.geometry(f"+{self.root.winfo_x()+dx}+{self.root.winfo_y()+dy}")

    def _on_release(self, e):
        if self._drag:
            self._save_layout()
        self._drag = None

    def _load_layout(self):
        """Carga las posiciones y visibilidad guardadas desde el archivo JSON."""
        try:
            if self.layout_file.exists():
                with open(self.layout_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    # Si es el formato nuevo (diccionario con 'positions' y 'visibility')
                    if isinstance(data, dict) and "positions" in data:
                        data["positions"] = {k: tuple(v) for k, v in data["positions"].items()}
                        data["positions_exp"] = {k: tuple(v) for k, v in data.get("positions_exp", {}).items()}
                        return data
                    # Compatibilidad con el formato viejo (solo posiciones)
                    return {"positions": {k: tuple(v) for k, v in data.items()}, "visibility": {}}
        except Exception as e:
            self.logs_terminal.append(f"[ERROR]: No se pudo cargar layout: {e}")
        return None

    def _save_layout(self):
        """Guarda las posiciones y visibilidad actuales en el archivo JSON."""
        try:
            data = {
                "positions": self._panel_pos, 
                "positions_exp": self._panel_pos_exp,
                "visibility": self._panel_vis,
                "theme_color": self.theme_color
            }
            with open(self.layout_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4)
        except Exception as e:
            self.logs_terminal.append(f"[ERROR]: No se pudo guardar layout: {e}")

    def _sanitize_layout(self):
        """Corrige paneles fuera de rango y layouts viejos que dejan el HUD casi vacío."""
        panel_areas = {
            "core": (260, 160),
            "neural": (260, 180),
            "nebula": (260, 220),
            "env": (260, 210),
            "pred": (260, 170),
            "threat": (260, 190),
            "diag": (260, 200),
            "console": (max(self._fw - 420, 300), 90),
            "reactor": (240, 240),
            "input_bar": (350, 50),
            "tactical": (200, 200),
        }

        def clamp_positions(target_dict, width, height):
            for name, (pw, ph) in panel_areas.items():
                x, y = target_dict.get(name, (0, 0))
                if x < 0 or y < 0 or x > width - 40 or y > height - 40:
                    defaults = self.default_pos_exp if target_dict is self._panel_pos_exp else self.default_pos
                    x, y = defaults.get(name, (20, 20))
                x = max(0, min(int(x), max(0, width - pw)))
                y = max(0, min(int(y), max(0, height - ph - 10)))
                target_dict[name] = (x, y)

        clamp_positions(self._panel_pos, self._cw, self._ch)
        clamp_positions(self._panel_pos_exp, self._fw, self._fh)

        for name in ("core", "pred", "threat", "diag", "reactor", "console", "input_bar"):
            if self._panel_vis.get(name) == "hidden":
                self._panel_vis[name] = "full"

    def _update_all_colors(self, color_hex):
        """Actualiza proporcionalmente los colores de los estados basados en el color global."""
        self.theme_color = color_hex
        h = color_hex.lstrip('#')
        try:
            r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
        except (ValueError, IndexError): return

        # Activo: Color base
        COLORS["Activo"] = (color_hex, COLORS["Activo"][1])

        # Escuchando: Variante cian/brillante proporcional (potencia azules/verdes)
        r_esc = min(255, int(r * 0.8))
        g_esc = min(255, int(g * 1.1 + 20))
        b_esc = min(255, int(b * 1.3 + 40))
        COLORS["Escuchando"] = (f"#{r_esc:02x}{g_esc:02x}{b_esc:02x}", COLORS["Escuchando"][1])

        # Pensando: Variante purpura/magenta proporcional (potencia rojos/azules)
        r_pen = min(255, int(r * 1.2 + 50))
        g_pen = min(255, int(g * 0.4))
        b_pen = min(255, int(b * 1.1 + 70))
        COLORS["Pensando"] = (f"#{r_pen:02x}{g_pen:02x}{b_pen:02x}", COLORS["Pensando"][1])

        # Hablando: Variante cálida (ámbar/dorado) proporcional al tema
        r_hab = min(255, int(r * 0.4 + 210))
        g_hab = min(255, int(g * 0.4 + 150))
        b_hab = int(b * 0.1)
        COLORS["Hablando"] = (f"#{r_hab:02x}{g_hab:02x}{b_hab:02x}", COLORS["Hablando"][1])

        if self.estado in COLORS:
            self.color = COLORS[self.estado][0]

    def _speak_alert(self, msg):
        """Reproduce una advertencia de voz en un hilo separado."""
        def run():
            try:
                from kitian_tts import get_tts
                tts = get_tts()
                if tts:
                    tts.hablar(msg)
            except Exception as e:
                self.logs_terminal.append(f"[ERROR]: Voz alerta: {e}")
        threading.Thread(target=run, daemon=True).start()

    def _on_key_press(self, event):
        self.last_key_time = time.time()

    def _on_mouse_move(self, e):
        self.mx = e.x
        self.my = e.y

    def _toggle_lock(self):
        if self._locked:
            self.logs_terminal.append("[SEGURIDAD]: Panel bloqueado.")
        else:
            self._locked = True
            self.logs_terminal.append("[SEGURIDAD]: Panel bloqueado.")

    def _geolocalizar(self):
        try:
            req = urllib.request.Request("http://ip-api.com/json/",
                                        headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=4) as resp:
                data = json.loads(resp.read().decode())
                if data.get("status") == "success":
                    self.lat = float(data.get("lat", -25.33))
                    self.lon = float(data.get("lon", -57.51))
                    self.ubica = f"{data.get('city','?')}, {data.get('countryCode','?')}"
        except Exception as e:
            self.logs_terminal.append(f"[ERROR]: Geolocalizacion: {e}")

    def _do_system_scan(self):
        try:
            # Cargar datos de red (Red de conocimiento) y salud de Kitian
            red_path = Path("datos_red.json")
            self.red_nodos = []
            self.red_aristas = []
            if red_path.exists():
                try:
                    with open(red_path, "r", encoding="utf-8") as f:
                        rdata = json.load(f)
                        self.red_nodos = rdata.get("nodes", [])
                        self.red_aristas = rdata.get("edges", [])
                except Exception as e:
                    self.logs_terminal.append(f"[ERROR]: Cargar red: {e}")

            health_path = Path("kitian_health.json")
            self.health_score = 100
            self.health_status = "OK"
            self.health_anomalies = []
            if health_path.exists():
                try:
                    with open(health_path, "r", encoding="utf-8") as f:
                        hdata = json.load(f)
                        self.health_score = hdata.get("score", 100)
                        self.health_status = hdata.get("status", "OK")
                        self.health_anomalies = hdata.get("anomalies", [])
                except Exception as e:
                    self.logs_terminal.append(f"[ERROR]: Cargar salud: {e}")

            raw_procs = []
            for p in psutil.process_iter(['name', 'cpu_percent', 'memory_percent', 'pid', 'ppid', 'exe']):
                try:
                    info = p.info
                    if info['name'] and info['name'] != "System Idle Process":
                        try:
                            info['folder'] = str(Path(info['exe']).parent) if info['exe'] else "System"
                        except:
                            info['folder'] = "System"
                        raw_procs.append(info)
                except: continue
            raw_procs.sort(key=lambda x: (x.get('cpu_percent') or 0) + (x.get('memory_percent') or 0), reverse=True)
            top_procs = raw_procs[:12]
            nuevos_nodos = []
            for i, p in enumerate(top_procs):
                old_n = next((n for n in self.nodos if n['pid'] == p['pid']), None)
                n = {
                    "name": p['name'].split('.')[0].upper()[:10],
                    "pid": p['pid'], "ppid": p['ppid'], "folder": p['folder'],
                    "cpu": p.get('cpu_percent') or 0,
                    "x": old_n['x'] if old_n else random.uniform(40, 220),
                    "y": old_n['y'] if old_n else random.uniform(40, 140),
                    "vx": old_n['vx'] if old_n else random.uniform(-0.3, 0.3),
                    "vy": old_n['vy'] if old_n else random.uniform(-0.3, 0.3),
                    "r": 4 + (p.get('cpu_percent') or 0) * 0.2,
                    "highlight": old_n['highlight'] if old_n and 'highlight' in old_n else 0
                }
                nuevos_nodos.append(n)
            self.nodos = nuevos_nodos
            self.procs_alto = [p['name'].split('.')[0].upper() for p in top_procs if (p.get('cpu_percent') or 0) > 12][:3]

            conns = psutil.net_connections(kind='inet')
            ext = set()
            for c in conns:
                if c.status == 'ESTABLISHED' and hasattr(c, 'raddr') and c.raddr:
                    rip = c.raddr[0] if isinstance(c.raddr, tuple) else getattr(c.raddr, 'ip', str(c.raddr))
                    if not self._is_private_ip(rip):
                        ext.add(rip)
            nuevos = ext - self.conex_prev
            if nuevos:
                rx_pos, ry_pos = self._panel_pos.get("reactor", (CX - 120, CY - 120))
                rcx, rcy = rx_pos + 120, ry_pos + 120
                for _ in range(10):
                    a = random.uniform(0, 2 * math.pi)
                    v = random.uniform(3, 6)
                    self.particulas.append({"x": rcx, "y": rcy, "vx": math.cos(a) * v, "vy": math.sin(a) * v, "v": 20, "c": "#ff2a00"})
            self.conex_prev = ext
            self.radar_objs = list(ext)

            # Generar/Mantener coordenadas visuales para las IPs detectadas en el globo
            new_map = {}
            for ip in ext:
                if ip in self._ip_map_pts:
                    new_map[ip] = self._ip_map_pts[ip]
                else:
                    new_map[ip] = (random.uniform(-60, 60), random.uniform(-180, 180))
            self._ip_map_pts = new_map

            ai_kws = ["ollama", "llama", "python", "pytorch", "cuda"]
            ia = False
            for p in top_procs:
                pn = p['name'].lower()
                for kw in ai_kws:
                    if kw in pn:
                        self.ia_local = p['name'].split('.')[0]
                        self.ia_estado = "ACTIVO"
                        ia = True
                        break
                if ia:
                    break
            if not ia:
                self.ia_local = "Kitian AI Core"
                self.ia_estado = "STANDBY"
        except Exception as e:
            self.logs_terminal.append(f"[ERROR]: System scan: {e}")

    def _escanear_sistema(self):
        while True:
            try:
                self._do_system_scan()
            except Exception as e:
                self.root.after(0, lambda err=e: self.logs_terminal.append(f"[ERROR]: Scan: {err}"))
            time.sleep(2)

    def _crear_entrada(self):
        ix, iy = self._panel_pos.get("input_bar", (ANCHO-380, ALTO-90))
        self.ifr = tk.Frame(self.root, bg="#010408", bd=0, relief="flat")
        self.ifr.place(x=ix, y=iy+18, width=350, height=26)
        tk.Label(self.ifr, text=">", fg="#00f0ff", bg="#010408", font=("Consolas", 10, "bold")).pack(side="left", padx=4)
        self.cmd = tk.Entry(self.ifr, bg="#010408", fg="#00f0ff", bd=0,
                           insertbackground="#00f0ff", font=("Consolas", 10))
        self.cmd.pack(side="left", fill="both", expand=True)
        self.cmd.bind("<Return>", self._proc)
        self.cmd.bind("<Key>", self._on_key_press)

    def _proc(self, event=None):
        cmd = self.cmd.get().strip()
        if not cmd:
            return
        self.cmd.delete(0, tk.END)
        self.logs_terminal.append(f"> {cmd}")
        cu = cmd.upper()
        if cu in ["HELP", "AYUDA"]:
            self.logs_terminal.append("[SISTEMA]: Comandos: SISTEMA, UBICACION, AMENAZAS, AI, PERFIL [operativo|ia|seguridad|minimal], FILTRO, FOCO, EXPORTAR REPORTE, SCAN, LOGS")
        elif cu in ["LIMPIAR", "CLEAR"]:
            self.logs_terminal.clear()
        elif cu in ["RESET", "REINICIAR"]:
            self._reset_layout()
        elif cu in ["SISTEMA", "DIAGNOSTICO"]:
            self._responder(f"CPU {self.cpu_val:.0f}% | RAM {self.ram_val:.0f}% | Disco {self.disk_val:.0f}%")
        elif cu in ["UBICACION", "DONDE ESTOY"]:
            self._responder(f"Ubicacion: {self.ubica}. Lat {self.lat:.2f} Lon {self.lon:.2f}")
        elif cu in ["AMENAZAS", "RADAR"]:
            n = len(self.conex_prev)
            self._responder(f"{n} conexiones externas activas." if n else "Perimetro seguro.")
        elif cu in ["AI", "IA"]:
            self._responder(f"Motor: {self.ia_local}. Estado: {self.ia_estado}")
        elif cu == "LOGS":
            log_path = Path(__file__).parent / "kitian.log"
            if log_path.exists():
                try:
                    with open(log_path, "r", encoding="utf-8") as f:
                        lines = f.readlines()
                        # Filtramos específicamente por eventos de seguridad y sistema relevantes
                        keywords = ["SECURITY", "ERROR", "CRITICAL", "ALERTA", "HUD"]
                        sec_events = [l for l in lines if any(k in l.upper() for k in keywords)]
                        for line in sec_events[-5:]:
                            # Extraemos solo el mensaje después del timestamp/level para que quepa en pantalla
                            msg = line.strip().split("] ", 1)[-1] if "] " in line else line.strip()
                            self.logs_terminal.append(f"[SEC]: {msg[:85]}")
                except Exception as e:
                    self.logs_terminal.append(f"[ERROR]: Fallo al leer log: {e}")
            else:
                self.logs_terminal.append("[ERROR]: Archivo kitian.log no encontrado.")
        elif cu.startswith("OPEN "):
            target = cu[5:].strip()
            found = False
            for n in self.nodos:
                if n['name'] == target:
                    n['highlight'] = self.fotogramas + 60
                    folder = n.get('folder')
                    if folder and folder != "System":
                        try:
                            if self._open_folder(folder):
                                self._responder(f"Abriendo: {folder}")
                            else:
                                self._responder("No pude abrir la carpeta.")
                        except Exception as e:
                            self._responder(f"Error: {e}")
                        found = True
                        break
            if not found:
                self._responder(f"Proceso '{target}' no detectado en red.")
        elif cu == "SCAN":
            self.logs_terminal.append("[SISTEMA]: Iniciando escaneo profundo de telemetría...")
            self._scan_glitch = self.fotogramas + 30
            self._update_telemetry_metrics()
            self._do_system_scan()
            self._geolocalizar()
            self._responder("Escaneo completado. Datos de paneles actualizados.")
        elif cu == "STRESS":
            self._stress_test = not self._stress_test
            status = "ACTIVADO" if self._stress_test else "DESACTIVADO"
            self.logs_terminal.append(f"[SISTEMA]: Modo STRESS {status}")
            self._responder(f"Simulación de carga al 100% {status.lower()}.")
        elif cu in ["ANALIZAR"]:
            self._responder("Reactor calibrado.")
        elif cu in ["VISTA GLOBAL", "TODAS"]:
            self._focus_panel = None
            self._set_filter_mode("all")
            self._responder("Vista global restaurada.")
        elif cu.startswith("PERFIL "):
            profile = cmd.split(" ", 1)[1].strip().lower()
            aliases = {"operativo": "operativo", "ia": "ia", "seguridad": "seguridad", "minimal": "minimal", "minimo": "minimal"}
            if self._apply_profile(aliases.get(profile)):
                self._responder(f"Perfil activo: {self._active_profile}")
            else:
                self._responder("Perfil no reconocido.")
        elif cu.startswith("FILTRO "):
            filt = cmd.split(" ", 1)[1].strip().lower()
            aliases = {"critico": "critical", "critica": "critical", "critical": "critical", "sistema": "system", "red": "network", "network": "network", "todo": "all", "all": "all"}
            self._set_filter_mode(aliases.get(filt, "all"))
            self._responder(f"Filtro activo: {self._filter_mode}")
        elif cu.startswith("FOCO "):
            target = cmd.split(" ", 1)[1].strip().lower()
            aliases = {
                "operativo": "core", "core": "core", "red neuronal": "neural", "neural": "neural",
                "entorno": "env", "respuesta": "pred", "ruta": "threat", "trafico": "threat",
                "fuentes": "diag", "acciones": "tactical", "reactor": "reactor", "log": "console", "comandos": "input_bar"
            }
            self._focus_panel = aliases.get(target)
            if self._focus_panel:
                self._responder(f"Foco en {self._focus_panel}")
            else:
                self._focus_panel = None
                self._responder("Panel no reconocido.")
        elif cu in ["EXPORTAR REPORTE", "REPORTE", "EXPORTAR"]:
            try:
                report_path = self._export_system_report()
                self._responder(f"Reporte exportado en {report_path.name}")
            except Exception as e:
                self.logs_terminal.append(f"[ERROR]: Exportar reporte fallo: {e}")
                self._responder("No pude exportar el reporte.")
        elif cu.startswith("INICIAR "):
            est = cu.split(" ")[1].capitalize() if len(cu.split(" ")) > 1 else ""
            if est in COLORS:
                self.estado = est
                self.color = COLORS[est][0]
                self._responder(f"Estado: {est.upper()}")
        elif cu.startswith("COLOR "):
            partes = cmd.split(" ")
            if len(partes) > 1:
                nc = partes[1] if partes[1].startswith("#") else "#" + partes[1]
                if len(nc) == 7:
                    self._update_all_colors(nc)
                    self._save_layout()
                    self._responder(f"Color de sistema actualizado: {nc}")
                else:
                    self._responder("Use formato hexadecimal #RRGGBB")
        else:
            try:
                from kitian_full import dispatcher_local
                result = dispatcher_local(cmd)
                if result:
                    self.logs_terminal.append(f"[CMD]: {result[:90]}")
                    self._responder(result)
                else:
                    self._responder("No entendi. Pruebe: ayuda.")
            except Exception:
                self._responder("No entendi. Pruebe: ayuda.")

    def _responder(self, t):
        self._responder_voz(t)

    def _responder_voz(self, t):
        self.estado = "Hablando"
        self.color = COLORS["Hablando"][0]
        self.sub = f'KI - TIAN: "{t}"'
        self._last_response = t          # guardar para tab RESPUESTA
        self._active_tab = "RESPUESTA"   # auto-navegar al tab de respuesta
        self.root.after(4000, lambda: self._cambiar_estado_si("Activo") if self.estado == "Hablando" else None)

    def _cambiar_estado_si(self, e):
        if e in COLORS:
            self.estado = e
            self.color = COLORS[e][0]

    def _panel_sizes(self):
        """Tamaños de panel adaptados dinámicamente a la resolución de pantalla."""
        W = self.root.winfo_width() or self._fw
        H = self.root.winfo_height() or self._fh
        _COL_W = W // 3
        _BODY   = H - 100 - 120  # quitar cabecera y pie
        row_h   = _BODY // 4     # altura de cada fila de paneles
        side_w  = max(260, _COL_W - 24)   # ancho paneles laterales
        ctr_w   = max(280, _COL_W - 24)   # ancho panel central
        return {
            "core":      (side_w, row_h - 8),
            "neural":    (side_w, row_h - 8),
            "nebula":    (side_w, row_h - 8),
            "env":       (side_w, row_h - 8),
            "pred":      (side_w, row_h - 8),
            "threat":    (side_w, row_h - 8),
            "diag":      (side_w, row_h - 8),
            "reactor":   (ctr_w,  _BODY * 2 // 4 - 8),
            "tactical":  (ctr_w,  _BODY * 2 // 4 - 8),
            "console":   (W - 400, 80),
            "input_bar": (360, 52),
        }

    def _panel(self, name, x, y, w, h, titulo):
        vis = self._panel_vis.get(name, "full")
        is_moving = (self._drag == name) or self._animating
        if not self._panel_allowed(name):
            return None, None, False
        if vis == "hidden":
            return None, None, False
        # En compacto mostrar solo la cabecera (32px)
        if vis == "compact":
            h = min(h, 32)

        # Usar tamaños dinámicos si está disponible
        sizes = self._panel_sizes()
        if name in sizes:
            dw, dh = sizes[name]
            if vis != "compact":
                w, h = dw, dh
            else:
                w = dw

        pos_dict = self._panel_pos_exp if self._expanded else self._panel_pos
        px, py = pos_dict.get(name, (x, y))

        # Efecto Glitch visual (CPU alto, SI bajo o comando SCAN)
        cond_glitch = (self.cpu_val > 90) or (self.si < 90) or (self._scan_glitch > self.fotogramas)
        is_glitching = cond_glitch and random.random() < 0.3
        if is_glitching:
            px += random.randint(-4, 4)
            py += random.randint(-2, 2)

        # Efecto Hover: aumenta el tamaño si el mouse está encima (solo si está desbloqueado)
        is_hover = not self._locked and not is_moving and px < self.mx < px+w and py < self.my < py+h
        if is_hover:
            px -= 2; py -= 2; w += 4; h += 4

        priority = self._panel_priority(name)
        if self._focus_panel == name:
            px -= 4; py -= 4; w += 8; h += 8
        elif priority == "critical":
            px -= 2; py -= 2; w += 4; h += 4
        elif priority == "warn":
            pass

        # Fondo del panel con sombra interna y borde luminoso
        # Sombra sutil
        self.canvas.create_rectangle(px+3, py+4, px+w+3, py+h+4, fill="#020810", outline="")
        # Fondo principal
        self.canvas.create_rectangle(px, py, px+w, py+h, fill="#06121a", outline="")
        # Borde exterior glow
        self.canvas.create_rectangle(px-1, py-1, px+w+1, py+h+1, outline="#0bb8d4", width=1)
        # Borde interior tenue
        self.canvas.create_rectangle(px+1, py+1, px+w-1, py+h-1, outline="#042030", width=1)
        # Barra de acento superior (color del tema)
        accent_col = COLORS.get(self.estado, ("#00e5ff",))[0]
        self.canvas.create_rectangle(px, py, px+w, py+3, fill=accent_col, outline="")
        # Línea separadora de cabecera
        self.canvas.create_line(px+6, py+22, px+w-6, py+22, fill="#103a50", width=1)

        t_color = "#d4f9ff"
        if is_moving:
            t_color = "#005577"
        if is_glitching and random.random() < 0.5:
            t_color = COLORS["Error"][0]
        if is_hover:
            t_color = "#ffffff"
        # Título del panel más grande y con icono simple
        self.canvas.create_text(px+12, py+13, text=f"■ {titulo}", fill=t_color, font=("Consolas", 9, "bold"), anchor="w")
        # Indicador de estado del panel (mini punto de color)
        prio_col = {"critical": "#ff2a00", "warn": "#ffb700"}.get(priority, "#003a4a")
        self.canvas.create_oval(px+w-14, py+8, px+w-6, py+16, fill=prio_col, outline="")

        self._panel_bounds[name] = (px, py, w, h, 22)
        return px, py, is_moving

    def _proyectar_globo(self, cx, cy, r, lat, lon):
        phi = math.radians(lat)
        theta = math.radians(lon) + self.ang_globo
        x3d = r * math.cos(phi) * math.sin(theta)
        y3d = r * math.sin(phi)
        z3d = r * math.cos(phi) * math.cos(theta)
        return cx + x3d, cy - y3d, z3d >= 0

    def _visual_metric(self, idx, fallback_label="", fallback_value="N/D"):
        metrics = self.visual_data.get("metrics") or []
        if idx < len(metrics):
            item = metrics[idx]
            return item.get("label", fallback_label), item.get("value", fallback_value)
        return fallback_label, fallback_value

    def _draw_info_rows(self, px, py, rows, start_y=34, row_h=18, value_color="#00f0ff", label_color="#005b66"):
        y = py + start_y
        for label, value in rows:
            self.canvas.create_text(px+12, y, text=label, fill=label_color, font=("Consolas", 9, "bold"), anchor="w")
            self.canvas.create_text(px+248, y, text=str(value)[:30], fill=value_color, font=("Consolas", 9, "bold"), anchor="e")
            y += row_h

    def _draw_wrapped_lines(self, px, py, lines, width=236, start_y=34, color="#c8f7ff", max_lines=6, font=("Consolas", 8)):
        y = py + start_y
        for line in (lines or [])[:max_lines]:
            self.canvas.create_text(px+12, y, text=str(line), fill=color, font=font, anchor="nw", width=width)
            y += 20

    def _stamp(self):
        return datetime.now().strftime("%H:%M:%S")

    def _status_color(self, level):
        level = str(level or "").upper()
        if level in ("OK", "ACTIVE", "ONLINE"):
            return "#00ff88"
        if level in ("WARN", "WARNING", "MEDIUM"):
            return "#ffd000"
        if level in ("DEGRADED", "HIGH"):
            return "#ff9d00"
        if level in ("CRITICAL", "ERROR", "OFFLINE"):
            return "#ff2a00"
        return "#8b98a3"

    def _health_state(self, value, warn=75, critical=90):
        if value >= critical:
            return "CRITICAL", "#ff2a00"
        if value >= warn:
            return "WARN", "#ffd000"
        return "OK", "#00ff88"

    def _build_alerts(self):
        alerts = []
        stamp = self._stamp()
        cpu_state, _ = self._health_state(self.cpu_val, 70, 90)
        ram_state, _ = self._health_state(self.ram_val, 80, 92)
        disk_state, _ = self._health_state(self.disk_val, 85, 95)
        ia_state = "OK" if self.ia_estado == "ACTIVO" else "WARN"
        alerts.append((cpu_state, f"CPU {self.cpu_val:.0f}% | {cpu_state} | psutil | {stamp}"))
        alerts.append((ram_state, f"RAM {self.ram_val:.0f}% | {ram_state} | psutil | {stamp}"))
        alerts.append((disk_state, f"DISCO {self.disk_val:.0f}% | {disk_state} | sistema | {stamp}"))
        alerts.append((ia_state, f"IA {self.ia_estado} | {ia_state} | {self.ia_local[:14]} | {stamp}"))

        if hasattr(self, "health_anomalies") and self.health_anomalies:
            for a in self.health_anomalies:
                if a.get("status") == "OPEN":
                    severity = a.get("severity", "MEDIUM")
                    level = "WARN" if severity in ("MEDIUM", "LOW") else "CRITICAL"
                    title = a.get("title", "")
                    comp = a.get("component", "")
                    alerts.append((level, f"{comp}: {title[:18]}"))
        return alerts

    def _normalize_info_line(self, label, value, state, source, updated_at):
        return f"{label}: {value} | {state} | {source} | {updated_at}"

    def _build_operational_rows(self):
        stamp = self.visual_data.get("updated_at") or self._stamp()
        cpu_state, _ = self._health_state(self.cpu_val, 70, 90)
        ram_state, _ = self._health_state(self.ram_val, 80, 92)
        disk_state, _ = self._health_state(self.disk_val, 85, 95)
        rows = [
            ("CPU", f"{self.cpu_val:.0f}% | {cpu_state} | psutil | {stamp}"),
            ("RAM", f"{self.ram_val:.0f}% | {ram_state} | psutil | {stamp}"),
            ("DISCO", f"{self.disk_val:.0f}% | {disk_state} | sistema | {stamp}"),
            ("RED", f"{self.net_down} | OK | net_io | {stamp}"),
        ]
        metrics = self.visual_data.get("metrics") or []
        for item in metrics[:2]:
            label = str(item.get("label", "dato")).upper()
            value = str(item.get("value", "N/D"))
            source = item.get("source", self.visual_data.get("kind", "runtime"))
            state = item.get("state", "INFO")
            rows.append((label, f"{value} | {state} | {source} | {stamp}"))
        return rows[:5]

    def _build_source_rows(self):
        stamp = self.visual_data.get("updated_at") or self._stamp()
        rows = []
        for src in (self.visual_data.get("sources") or [])[:5]:
            rows.append(self._normalize_info_line("SRC", src, "INFO", self.visual_data.get("kind", "runtime"), stamp))
        if not rows:
            rows = [
                self._normalize_info_line("IA", self.ia_local, self.ia_estado, "modelo local", stamp),
                self._normalize_info_line("RED", f"{len(self.conex_prev)} conexiones", "OK", "socket", stamp),
                self._normalize_info_line("UBIC", self.ubica[:18] or "N/D", "OK", "geo", stamp),
            ]
        return rows

    def _build_command_log(self):
        entries = []
        for level, msg in self._build_alerts()[:3]:
            entries.append(f"[{level}] {msg}")
        for action in list(self.visual_data.get("action_log", []))[-2:]:
            entries.append(f"[INFO] {action}")
        for log in self.logs_terminal[-3:]:
            raw = str(log)
            level = "INFO"
            if "ERROR" in raw:
                level = "ERROR"
            elif "WARN" in raw:
                level = "WARN"
            elif "OK" in raw or "SISTEMA" in raw:
                level = "OK"
            entries.append(f"[{level}] {raw}")
        return entries[-7:]

    def _build_quick_actions(self):
        if self._focus_panel in {"env", "threat", "diag"} or self._active_profile == "seguridad":
            return ["SCAN", "AMENAZAS", "FILTRO RED", "LOGS", "EXPORTAR REPORTE"]
        if self._focus_panel in {"pred", "tactical"} or self._active_profile == "ia":
            return ["AI", "HORA", "CLIMA", "FOCO RESPUESTA", "EXPORTAR REPORTE"]
        if self._active_profile == "minimal":
            return ["TODAS", "SISTEMA", "UBICACION", "EXPORTAR REPORTE"]
        return ["SISTEMA", "SCAN", "FILTRO CRITICO", "PERFIL IA", "EXPORTAR REPORTE"]

    def _draw_sparkline(self, x, y, w, h, values, color="#00f0ff"):
        vals = list(values or [])
        if len(vals) < 2:
            self.canvas.create_rectangle(x, y, x+w, y+h, outline="#103746", width=1)
            return
        self.canvas.create_rectangle(x, y, x+w, y+h, outline="#103746", width=1)
        lo = min(vals)
        hi = max(max(vals), lo + 1.0)
        pts = []
        for idx, val in enumerate(vals):
            px = x + (idx / max(len(vals) - 1, 1)) * w
            py = y + h - ((val - lo) / (hi - lo)) * h
            pts.extend([px, py])
        self.canvas.create_line(*pts, fill=color, width=1.5, smooth=True)

    def _export_system_report(self):
        report_path = Path(__file__).parent / f"kitian_system_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        alerts = self._build_alerts()
        lines = [
            "KI-TIAN SYSTEM REPORT",
            f"Fecha: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}",
            f"Ubicacion: {self.ubica}",
            f"Perfil: {self._active_profile}",
            f"Estado general: {self.si:.1f}%",
            f"CPU: {self.cpu_val:.0f}%",
            f"RAM: {self.ram_val:.0f}%",
            f"Disco: {self.disk_val:.0f}%",
            f"Red: {self.net_down} down / {self.net_up} up",
            f"IA: {self.ia_local} | {self.ia_estado}",
            f"Alertas: {len([a for a in alerts if a[0] != 'OK'])}",
            "Eventos recientes:",
        ]
        lines.extend(self.logs_terminal[-5:])
        report_path.write_text("\n".join(lines), encoding="utf-8")
        self.logs_terminal.append(f"[OK]: Reporte exportado {report_path.name}")
        return report_path

    def _draw_filter_chip(self, x, y, label, mode):
        active = self._filter_mode == mode
        fill = "#15303a" if active else "#071a22"
        outline = "#ffd000" if active else "#11485a"
        fg = "#fff1a8" if active else "#9fefff"
        w = max(48, 12 + len(label) * 7)
        self.canvas.create_rectangle(x, y, x+w, y+22, fill=fill, outline=outline, width=1)
        self.canvas.create_text(x + w/2, y + 11, text=label, fill=fg, font=("Consolas", 8, "bold"))
        self._header_chip_rects[mode] = (x, y, x+w, y+22)
        return w

    def _draw_chip(self, x, y, text, fill="#071a22", outline="#11485a", fg="#9fefff"):
        w = max(44, 10 + len(text) * 7)
        self.canvas.create_rectangle(x, y, x+w, y+22, fill=fill, outline=outline, width=1)
        self.canvas.create_text(x + w/2, y + 11, text=text, fill=fg, font=("Consolas", 8, "bold"))
        return w

    def _draw_kpi_box(self, x, y, w, h, label, value, accent="#00e5ff", sub=None):
        self.canvas.create_rectangle(x+3, y+4, x+w+3, y+h+4, fill="#02060a", outline="", stipple="gray25")
        self.canvas.create_rectangle(x, y, x+w, y+h, fill="#06131b", outline="#103b49", width=1)
        self.canvas.create_rectangle(x, y, x+4, y+h, fill=accent, outline=accent)
        self.canvas.create_text(x+12, y+12, text=label, fill="#5f93a0", font=("Consolas", 7, "bold"), anchor="w")
        self.canvas.create_text(x+12, y+h/2+4, text=value, fill="#ebfeff", font=("Consolas", 13, "bold"), anchor="w")
        if sub:
            self.canvas.create_text(x+w-10, y+h-10, text=sub, fill="#6bc0cf", font=("Consolas", 7), anchor="e")

    def _fmt_rate(self, bps):
        if bps >= 1024 * 1024:
            return f"{bps / (1024 * 1024):.1f} MB/s"
        return f"{bps / 1024:.1f} KB/s"

    def _update_telemetry_metrics(self):
        try:
            self.cpu_val = psutil.cpu_percent(interval=None)
            mem = psutil.virtual_memory()
            self.ram_val = mem.percent

            try:
                self.disk_val = psutil.disk_usage('/').percent if platform.system() != 'Windows' else psutil.disk_usage('C:\\').percent
            except Exception:
                pass

            now = time.time()
            last_t = getattr(self, "_last_net_t", now)
            dt = max(now - last_t, 0.001)

            n = psutil.net_io_counters()
            dr = max(0, n.bytes_recv - self.last_recv)
            ds = max(0, n.bytes_sent - self.last_sent)

            self.last_recv = n.bytes_recv
            self.last_sent = n.bytes_sent
            self._last_net_t = now

            self._current_dr = dr
            self.net_down = self._fmt_rate(dr / dt)
            self.net_up = self._fmt_rate(ds / dt)

            self.cpu_hist.append(self.cpu_val)
            self.cpu_hist = self.cpu_hist[-45:]
            self.ram_hist.append(self.ram_val)
            self.ram_hist = self.ram_hist[-45:]
            self.disk_hist.append(self.disk_val)
            self.disk_hist = self.disk_hist[-45:]
        except Exception as e:
            self.logs_terminal.append(f"[ERROR]: Telemetria fallo: {e}")

    def _is_private_ip(self, ip):
        try:
            obj = ipaddress.ip_address(ip)
            return obj.is_private or obj.is_loopback or obj.is_link_local
        except ValueError:
            return True

    def _open_folder(self, folder):
        try:
            if platform.system() == "Windows":
                os.startfile(folder)
            elif platform.system() == "Darwin":
                subprocess.Popen(["open", folder])
            else:
                subprocess.Popen(["xdg-open", folder])
            return True
        except Exception as e:
            self.logs_terminal.append(f"[ERROR]: No se pudo abrir carpeta: {e}")
            return False

    def loop(self):
        self.canvas.delete("all")
        self._panel_bounds = {}
        self._header_chip_rects = {}
        self.fotogramas += 1
        ahora = time.time()
        if (ahora - self.lt) > 0:
            self.fps = max(1, int(1.0 / (ahora - self.lt)))
        self.lt = ahora
        W = self.root.winfo_width() or self._fw
        H = self.root.winfo_height() or self._fh

        # ── CONSTANTES DE LAYOUT ────────────────────────────────────────────
        HDR_H  = 100
        KPI_H  = 40
        TAB_H  = 34
        FOOT_H = 74
        SB_W   = 210
        BODY_Y = HDR_H + KPI_H + TAB_H
        BODY_H = H - BODY_Y - FOOT_H
        CX_START = SB_W
        CW     = W - SB_W * 2
        CX_MID = SB_W + CW // 2
        CY_MID = BODY_Y + BODY_H // 2

        # ── FONDO ───────────────────────────────────────────────────────────
        for gy in range(0, H, 30):
            lc = "#071e2a" if gy % 60 == 0 else "#04111a"
            self.canvas.create_line(0, gy, W, gy, fill=lc, width=1)
        for gx in range(0, W, 40):
            lc = "#071820" if gx % 80 == 0 else "#030d14"
            self.canvas.create_line(gx, 0, gx, H, fill=lc, width=1)
        scan_y = int((self.fotogramas * 4) % max(H, 1))
        self.canvas.create_line(0, scan_y, W, scan_y, fill=self.color, width=1, stipple="gray12")
        for i in range(5):
            vc = f"#{max(0, 4-i):02x}0d16"
            self.canvas.create_rectangle(i, 0, W-i, H, outline=vc, width=1)

        # ── SINCRONIZAR ESTADO ──────────────────────────────────────────────
        if self.fotogramas % 10 == 0:
            self._update_telemetry_metrics()
        if self.st:
            try:
                e_st, c_st, i_st = self.st.get()
                self.estado = e_st
                self.color = COLORS.get(e_st, ("#00e5ff", "#00ff88"))[0]
                if i_st:
                    self.sub = f'KI - TIAN: "{i_st}"'
                    if i_st != getattr(self, "_prev_i_st", ""):
                        self._last_response = i_st
                        self._active_tab = "RESPUESTA"
                    self._prev_i_st = i_st
                if hasattr(self.st, "get_visual_data"):
                    self.visual_data = self.st.get_visual_data()
                if hasattr(self.st, "get_actions"):
                    ac = self.st.get_actions()
                    if ac:
                        self.visual_data["action_log"] = ac
            except:
                pass
        if self.estado != self.prev_estado:
            if self.prev_estado == "Hablando" and self.estado == "Activo":
                self._last_completed_frame = self.fotogramas + 30
            self.prev_estado = self.estado

        estado_colors = {
            "Activo":"#00ff88","Escuchando":"#00f0ff",
            "Pensando":"#cc44ff","Hablando":"#ffd000",
            "Error":"#ff2a00","Offline":"#555555",
        }
        e_col = estado_colors.get(self.estado, "#00e5ff")
        base_t = _t(self.color)
        R = 54 + 4 * math.sin(self.fotogramas * 0.04)
        v_rot = 0.02 + (self.cpu_val / 100.0) * 0.18
        self.ang_r += v_rot
        cc = self.canvas  # alias

        # ════════════════════════════════════════════════════════════════════
        #  CABECERA (y=0..HDR_H)
        # ════════════════════════════════════════════════════════════════════
        cc.create_rectangle(0, 0, W, HDR_H, fill="#030d15", outline="")
        cc.create_rectangle(0, 0, W, 3, fill=self.color, outline="")
        cc.create_line(0, HDR_H, W, HDR_H, fill="#0d3a50", width=2)
        cc.create_line(0, 56, W, 56, fill="#08263a", width=1)

        uptime = int(time.time() - self.inicio)
        h_up, m_up = uptime // 3600, (uptime % 3600) // 60
        ahora_header = datetime.now().strftime("%H:%M:%S")

        # Izquierda
        cc.create_text(16, 16, text="SYS", fill="#003a50", font=("Consolas", 8, "bold"), anchor="w")
        cc.create_text(16, 32, text=f"{self.si:.1f}%", fill=self.color, font=("Consolas", 13, "bold"), anchor="w")
        cc.create_text(16, 50, text="SECURE", fill="#005b66", font=("Consolas", 7, "bold"), anchor="w")
        cc.create_text(80, 16, text="UPTIME", fill="#003a50", font=("Consolas", 7, "bold"), anchor="w")
        cc.create_text(80, 30, text=f"{h_up:02d}:{m_up:02d}:{uptime%60:02d}", fill="#4ab8cc", font=("Consolas", 11, "bold"), anchor="w")
        cc.create_text(80, 48, text=ahora_header, fill="#7ec7d8", font=("Consolas", 9, "bold"), anchor="w")

        # Título central
        cc.create_text(W//2+2, 27, text="KI-TIAN X20", fill="#001a28", font=("Consolas", 20, "bold"), anchor="center")
        cc.create_text(W//2, 25, text="KI-TIAN X20", fill=self.color, font=("Consolas", 20, "bold"), anchor="center")
        sub_title = str(self.visual_data.get("title", "Neural Command Core")).upper()[:64]
        cc.create_text(W//2, 46, text=sub_title, fill="#4a9ab0", font=("Consolas", 8, "bold"), anchor="center")
        cc.create_line(W//2-180, 54, W//2+180, 54, fill="#0d4055", width=1)

        # Derecha
        cc.create_text(W-16, 16, text="IA CORE", fill="#003a50", font=("Consolas", 8, "bold"), anchor="e")
        cc.create_text(W-16, 30, text=self.ia_local[:20], fill="#4ab8cc", font=("Consolas", 10, "bold"), anchor="e")
        cc.create_text(W-16, 48, text=f"● {self.estado.upper()}", fill=e_col, font=("Consolas", 10, "bold"), anchor="e")

        # Fila 2 cabecera
        cc.create_text(16, 74, text=f"LOC: {self.ubica[:32]}  |  PERFIL: {self._active_profile.upper()}  |  MOTOR: {self.ia_local}",
                       fill="#2d7080", font=("Consolas", 8), anchor="w")

        # ════════════════════════════════════════════════════════════════════
        #  BARRA KPI (y=HDR_H..HDR_H+KPI_H)
        # ════════════════════════════════════════════════════════════════════
        kpi_y = HDR_H
        kpi_count = 5
        kpi_w = W // kpi_count
        kpi_data = [
            ("CPU",   f"{self.cpu_val:.0f}%",  self.cpu_hist[-20:],
             "#00ff88" if self.cpu_val<70 else ("#ffb700" if self.cpu_val<90 else "#ff2a00"),
             self.cpu_val/100.0),
            ("RAM",   f"{self.ram_val:.0f}%",  self.ram_hist[-20:],
             "#00d4ff" if self.ram_val<80 else ("#ffb700" if self.ram_val<92 else "#ff2a00"),
             self.ram_val/100.0),
            ("DISCO", f"{self.disk_val:.0f}%", self.disk_hist[-20:],
             "#ff9d00", self.disk_val/100.0),
            ("RED ▼", self.net_down, [], "#00e5ff", 0.0),
            ("ESTADO", self.estado.upper(), [], e_col, 0.0),
        ]
        for i, (kname, kval, khist, kcol, kfill) in enumerate(kpi_data):
            kx = i * kpi_w
            cc.create_line(kx, kpi_y, kx, kpi_y+KPI_H, fill="#081c28", width=1)
            cc.create_rectangle(kx, kpi_y, kx+kpi_w, kpi_y+KPI_H, fill="#040e18", outline="")
            cc.create_text(kx+9, kpi_y+9, text=kname, fill="#2a6a7c", font=("Consolas",7,"bold"), anchor="w")
            cc.create_text(kx+9, kpi_y+25, text=kval, fill=kcol, font=("Consolas",12,"bold"), anchor="w")
            if khist and len(khist) >= 2:
                self._draw_sparkline(kx+kpi_w-58, kpi_y+6, 52, 28, khist, kcol)
            if kfill > 0:
                bw = int((kpi_w-10) * min(kfill, 1.0))
                cc.create_rectangle(kx+5, kpi_y+KPI_H-4, kx+5+kpi_w-10, kpi_y+KPI_H-1, fill="#0a2030", outline="")
                cc.create_rectangle(kx+5, kpi_y+KPI_H-4, kx+5+bw, kpi_y+KPI_H-1, fill=kcol, outline="")
        cc.create_line(0, kpi_y+KPI_H, W, kpi_y+KPI_H, fill="#0d3a50", width=2)

        # ════════════════════════════════════════════════════════════════════
        #  BARRA DE PESTAÑAS
        # ════════════════════════════════════════════════════════════════════
        tab_y = HDR_H + KPI_H
        tab_w = W // len(self._tabs)
        cc.create_rectangle(0, tab_y, W, tab_y+TAB_H, fill="#030e18", outline="")
        self._tab_rects = {}
        for idx, tab_name in enumerate(self._tabs):
            tx = idx * tab_w
            active = (self._active_tab == tab_name)
            cc.create_rectangle(tx, tab_y, tx+tab_w, tab_y+TAB_H, fill="#071e2e" if active else "#030e18", outline="")
            if active:
                cc.create_rectangle(tx, tab_y, tx+tab_w, tab_y+3, fill=self.color, outline="")
            cc.create_line(tx+tab_w, tab_y+4, tx+tab_w, tab_y+TAB_H-4,
                           fill=(self.color if active else "#0d3040"), width=1)
            cc.create_text(tx+tab_w//2, tab_y+TAB_H//2, text=tab_name,
                           fill=(self.color if active else "#1e5a70"),
                           font=("Consolas", 9, "bold"), anchor="center")
            self._tab_rects[tab_name] = (tx, tab_y, tx+tab_w, tab_y+TAB_H)
        cc.create_line(0, tab_y+TAB_H, W, tab_y+TAB_H, fill="#0d3a50", width=2)

        # ── Divisores de zonas ─────────────────────────────────────────────
        cc.create_line(SB_W, BODY_Y, SB_W, H-FOOT_H, fill="#0a2a3a", width=1)
        cc.create_line(W-SB_W, BODY_Y, W-SB_W, H-FOOT_H, fill="#0a2a3a", width=1)

        # ════════════════════════════════════════════════════════════════════
        #  SIDEBAR IZQUIERDO — plataforma y procesos (sin repetir KPI superior)
        # ════════════════════════════════════════════════════════════════════
        sb_pad = 12
        sx = sb_pad
        sy = BODY_Y + 12
        se = SB_W - sb_pad

        cc.create_text(sx, sy, text="▸ PLATAFORMA & SISTEMA", fill="#0d4055", font=("Consolas", 8, "bold"), anchor="w")
        sy += 20
        for lbl, val in [("IP LOCAL", self.local_ip or "N/D"), ("FPS HUD", str(self.fps)),
                          ("SISTEMA", str(self.so)[:16]), ("PROCESOS", f"{len(self.nodos)} activos"),
                          ("UPTIME", f"{h_up:02d}h {m_up:02d}m")]:
            cc.create_text(sx, sy, text=lbl, fill="#1a5060", font=("Consolas", 8, "bold"), anchor="w")
            cc.create_text(se, sy, text=val, fill="#4a9ab0", font=("Consolas", 8, "bold"), anchor="e")
            sy += 18

        sy += 6; cc.create_line(sx, sy, se, sy, fill="#0a2030", width=1); sy += 12

        cc.create_text(sx, sy, text="▸ TOP PROCESOS ACTIVOS", fill="#0d4055", font=("Consolas", 8, "bold"), anchor="w")
        sy += 18
        max_n = max(1, (H - FOOT_H - sy) // 18)
        for n in self.nodos[:max_n]:
            pc = "#ff2a00" if n['cpu']>15 else ("#ffaa00" if n['cpu']>5 else "#1e5a70")
            cc.create_text(sx, sy, text=f"{'▶' if n['cpu']>5 else '·'} {n['name'][:15]}", fill=pc, font=("Consolas", 8), anchor="w")
            cc.create_text(se, sy, text=f"{n['cpu']:.0f}%", fill=pc, font=("Consolas", 8, "bold"), anchor="e")
            sy += 18

        # ════════════════════════════════════════════════════════════════════
        #  SIDEBAR DERECHO — IA y alertas (sin repetir RED superior)
        # ════════════════════════════════════════════════════════════════════
        rsx = W - SB_W + sb_pad
        rsy = BODY_Y + 12
        rse = W - sb_pad

        cc.create_text(rsx, rsy, text="▸ IA / ESTADO CORE", fill="#0d4055", font=("Consolas", 8, "bold"), anchor="w")
        rsy += 20
        for lbl, val in [("Motor", self.ia_local[:16]), ("Estado", self.ia_estado),
                          ("Modo", self._active_profile.upper()), ("Conex ext", f"{len(self.conex_prev)} nodos")]:
            cc.create_text(rsx, rsy, text=lbl, fill="#1a5060", font=("Consolas", 8, "bold"), anchor="w")
            vc = "#00ff88" if "ACT" in val else ("#ffd000" if "STAND" in val else "#4a9ab0")
            cc.create_text(rse, rsy, text=val, fill=vc, font=("Consolas", 8, "bold"), anchor="e")
            rsy += 18

        rsy += 6; cc.create_line(rsx, rsy, rse, rsy, fill="#0a2030", width=1); rsy += 12

        alerts = self._build_alerts()
        n_crit = sum(1 for lv, _ in alerts if lv in ("CRITICAL","ERROR"))
        n_warn = sum(1 for lv, _ in alerts if lv == "WARN")
        cc.create_text(rsx, rsy, text="▸ ALERTAS DE SISTEMA", fill="#0d4055", font=("Consolas", 8, "bold"), anchor="w"); rsy += 18
        cc.create_text(rsx, rsy, text=f"● {n_crit} CRITICAS", fill="#ff2a00" if n_crit else "#1a5060", font=("Consolas", 9, "bold"), anchor="w"); rsy += 18
        cc.create_text(rsx, rsy, text=f"● {n_warn} AVISOS", fill="#ffb700" if n_warn else "#1a5060", font=("Consolas", 9, "bold"), anchor="w"); rsy += 18
        max_al = min(12, max(0, (H - FOOT_H - rsy - 50) // 16))
        for lv, msg in alerts[:max_al]:
            lc2 = "#ff2a00" if lv in ("CRITICAL","ERROR") else ("#ffb700" if lv=="WARN" else "#1e5a70")
            cc.create_text(rsx, rsy, text=f"[{lv[:4]}] {msg[:24]}", fill=lc2, font=("Consolas", 7), anchor="w")
            rsy += 16

        # Botón lock
        lock_y = H - FOOT_H - 22
        cc.create_text(rse, lock_y, text="LOCK" if self._locked else "UNLK",
                       fill="#ff6644" if self._locked else "#00ff88",
                       font=("Consolas", 8, "bold"), anchor="e")
        self._lock_rect = (W-SB_W, lock_y-12, W, lock_y+12)
        if not self._locked:
            rst_y = lock_y - 22
            cc.create_text(rse, rst_y, text="RST", fill="#ffaa00", font=("Consolas", 8, "bold"), anchor="e")
            self._reset_rect = (W-SB_W, rst_y-10, W, rst_y+10)
        else:
            self._reset_rect = (0, 0, 0, 0)

        # ════════════════════════════════════════════════════════════════════
        #  ZONA CENTRAL — contenido según pestaña activa
        # ════════════════════════════════════════════════════════════════════
        cx_p, cy_p = CX_MID, CY_MID

        if self._active_tab == "REACTOR":
            rt = base_t if self.cpu_val <= 85 else _t(COLORS["Error"][0])
            # Pulso de voz
            if self.estado == "Hablando":
                ps = 14 * abs(math.sin(self.fotogramas * 0.15))
                cc.create_oval(cx_p-R-ps, cy_p-R-ps, cx_p+R+ps, cy_p+R+ps, outline=rt[3], width=2)
                cc.create_oval(cx_p-R-ps*2, cy_p-R-ps*2, cx_p+R+ps*2, cy_p+R+ps*2, outline=rt[4], width=1)
            # CPU / RAM flotantes
            cpu_c = "#00ff88" if self.cpu_val<50 else ("#ffb700" if self.cpu_val<80 else "#ff2a00")
            ram_c = "#00ff88" if self.ram_val<50 else ("#ffb700" if self.ram_val<80 else "#ff2a00")
            cc.create_text(cx_p-150, cy_p-120, text="CPU", fill="#005b66", font=("Consolas", 8), anchor="w")
            cc.create_text(cx_p-150, cy_p-98, text=f"{self.cpu_val:.0f}%", fill=cpu_c, font=("Consolas", 24, "bold"), anchor="w")
            cc.create_text(cx_p+150, cy_p-120, text="RAM", fill="#005b66", font=("Consolas", 8), anchor="e")
            cc.create_text(cx_p+150, cy_p-98, text=f"{self.ram_val:.0f}%", fill=ram_c, font=("Consolas", 24, "bold"), anchor="e")
            # Anillos
            for i in range(12, 0, -1):
                gr_arc = R + 5 + i * 11
                ci = min(i, 5)
                sa = self.ang_r * (i * 0.8)
                if i % 2 == 0:
                    cc.create_arc(cx_p-gr_arc, cy_p-gr_arc, cx_p+gr_arc, cy_p+gr_arc, start=sa, extent=240, outline=rt[3], width=1, style="arc")
                else:
                    cc.create_arc(cx_p-gr_arc, cy_p-gr_arc, cx_p+gr_arc, cy_p+gr_arc, start=sa, extent=120, outline=rt[ci], width=1.5, style="arc")
            for j in range(48):
                a = j * math.pi / 24 + self.ang_r * 0.04
                x1 = cx_p + (R+42)*math.cos(a); y1 = cy_p + (R+42)*math.sin(a)
                x2 = cx_p + (R+50)*math.cos(a); y2 = cy_p + (R+50)*math.sin(a)
                cc.create_line(x1, y1, x2, y2, fill=rt[3], width=1)
            for i, w in enumerate(FUNC_WORDS):
                a = i * math.pi / 2.5 + self.ang_r * 0.04
                cc.create_text(cx_p+(R+78)*math.cos(a), cy_p+(R+78)*math.sin(a), text=w, fill=rt[1], font=("Consolas", 7, "bold"))
            cc.create_oval(cx_p-R-1, cy_p-R-1, cx_p+R+1, cy_p+R+1, outline=rt[0], width=3)
            cc.create_oval(cx_p-R+8, cy_p-R+8, cx_p+R-8, cy_p+R-8, outline=rt[1], width=1, dash=(3,3))
            sc_arc = 60 + 15 * math.sin(self.ang_r * 1.5)
            cc.create_arc(cx_p-R-28, cy_p-R-28, cx_p+R+28, cy_p+R+28, start=self.ang_r*57.3, extent=sc_arc, outline=rt[0], width=2, style="arc")
            # Texto
            cc.create_text(cx_p, cy_p-6, text="KI - TIAN", fill=rt[0], font=("Consolas", 15, "bold"))
            cc.create_text(cx_p, cy_p+12, text=self.estado.upper(), fill=e_col, font=("Consolas", 9, "bold"))
            # Procesos orbitando
            for idx, n in enumerate(self.nodos[:4]):
                a = -self.ang_r*0.5 + idx*(math.pi/2)
                dist_r = R + 52
                rx2, ry2 = cx_p + dist_r*math.cos(a), cy_p + dist_r*math.sin(a)
                pc = "#ff2a00" if n['cpu']>20 else ("#ffaa00" if n['cpu']>10 else "#00ff88")
                cc.create_text(rx2, ry2, text=n['name'], fill=pc, font=("Consolas", 7, "bold"))
                cc.create_line(rx2-8, ry2+7, rx2-8+min(n['cpu'],30), ry2+7, fill=pc, width=2)
            # Ecualizador de voz
            if self.estado == "Hablando":
                for i in range(14):
                    xo = -50 + i*8 + 2
                    bh2 = 4 + 26*abs(math.sin(self.ang_r*2.2+i*0.3))
                    cc.create_rectangle(cx_p+xo, cy_p+R+24-bh2, cx_p+xo+5, cy_p+R+24, fill=rt[0], outline="")
            # Chispas
            rate = 0; c_spark = "#ffffff"
            if self.estado == "Pensando": rate = 2; c_spark = base_t[0]
            elif self.estado == "Escuchando": rate = 4; c_spark = "#00f0ff"
            if self._last_completed_frame > self.fotogramas: rate = 8; c_spark = "#ffaa00"
            if len(self.conex_prev) > 0 and self.fotogramas % 30 == 0: rate = 12; c_spark = "#ff2a00"
            if rate > 0 and self.fotogramas % 2 == 0:
                for _ in range(rate):
                    a = random.uniform(0, 2*math.pi)
                    d = R + random.uniform(20, 120)
                    self.particulas.append({"x":cx_p+d*math.cos(a), "y":cy_p+d*math.sin(a),
                                            "vx":random.uniform(-1.5, 1.5), "vy":random.uniform(-2.5, -0.5),
                                            "v":22, "c":c_spark})
            for p in self.particulas:
                p["x"] += p["vx"]; p["y"] += p["vy"]; p["v"] -= 1
                if p["v"] > 0:
                    s = 3.2 * (p["v"] / 22)
                    cc.create_oval(p["x"]-s, p["y"]-s, p["x"]+s, p["y"]+s, fill=p["c"], outline="")
            self.particulas = [p for p in self.particulas if p["v"] > 0][-120:]

        elif self._active_tab == "RESPUESTA":
            resp_text = self._last_response or self.visual_data.get("summary") or "Sin respuesta activa."
            pad_r = 28
            cc.create_rectangle(CX_START+pad_r, BODY_Y+pad_r, CX_START+CW-pad_r, BODY_Y+BODY_H-pad_r,
                                 fill="#040f18", outline=self.color, width=1)
            cc.create_rectangle(CX_START+pad_r, BODY_Y+pad_r, CX_START+CW-pad_r, BODY_Y+pad_r+32,
                                 fill="#060f18", outline="")
            cc.create_text(CX_START+pad_r+14, BODY_Y+pad_r+16,
                           text="■ RESPUESTA  KI-TIAN", fill=self.color, font=("Consolas", 10, "bold"), anchor="w")
            cc.create_text(CX_START+CW-pad_r-10, BODY_Y+pad_r+16,
                           text=ahora_header, fill="#2a6a7c", font=("Consolas", 9), anchor="e")
            cc.create_text(cx_p, BODY_Y+pad_r+52,
                           text=resp_text, fill="#d4f9ff",
                           font=("Consolas", 11), anchor="n", width=CW-pad_r*3, justify="center")
            acciones = self.visual_data.get("actions") or self.visual_data.get("action_log") or []
            if acciones:
                ay_r = BODY_Y + BODY_H - pad_r - 20 - len(acciones[:4]) * 30
                cc.create_text(CX_START+pad_r+12, ay_r-18, text="ACCIONES SUGERIDAS",
                               fill="#2a6a7c", font=("Consolas", 8, "bold"), anchor="w")
                for ac2 in acciones[:4]:
                    cc.create_rectangle(CX_START+pad_r+10, ay_r-10, CX_START+CW-pad_r-10, ay_r+16,
                                        fill="#071922", outline="#0d3340", width=1)
                    cc.create_text(CX_START+pad_r+20, ay_r+3, text=str(ac2)[:80],
                                   fill="#d4f9ff", font=("Consolas", 9), anchor="w")
                    ay_r += 30
            cc.create_text(cx_p, BODY_Y+BODY_H-pad_r-8,
                           text="Escribí un comando para nueva consulta  |  Click TAB REACTOR para volver",
                           fill="#0a3040", font=("Consolas", 8), anchor="center")

        elif self._active_tab == "SISTEMA":
            cy2 = BODY_Y + 16
            col2 = CX_START + 20
            cc.create_text(col2, cy2, text="DIAGNÓSTICO Y SENSORES DE TELEMETRÍA", fill=self.color, font=("Consolas", 11, "bold"), anchor="w")
            cy2 += 28

            cc.create_text(col2, cy2, text="▸ ESTADO OPERATIVO DE MÓDULOS", fill="#0d4055", font=("Consolas", 9, "bold"), anchor="w"); cy2 += 22
            for row in self._build_operational_rows()[:8]:
                cc.create_rectangle(col2, cy2-10, col2+CW-40, cy2+14, fill="#05121c", outline="#0a2a3a", width=1)
                cc.create_text(col2+12, cy2+2, text=str(row)[:100], fill="#d4f9ff", font=("Consolas", 9), anchor="w")
                cy2 += 28

            cy2 += 10
            cc.create_line(col2, cy2, col2+CW-40, cy2, fill="#0a2030", width=1); cy2 += 16
            cc.create_text(col2, cy2, text="▸ FUENTES DE DATOS Y CONECTORES", fill="#0d4055", font=("Consolas", 9, "bold"), anchor="w"); cy2 += 22
            for src in self._build_source_rows()[:8]:
                cc.create_text(col2+8, cy2, text=f"● {str(src)[:95]}", fill="#4a9ab0", font=("Consolas", 8), anchor="w"); cy2 += 20


        elif self._active_tab == "RED":
            cw_n = CW - 40
            ch_n = BODY_H - 40
            nx_off = CX_START + 20
            ny_off = BODY_Y + 30
            cc.create_text(nx_off+8, BODY_Y+12, text=f"RED NEURONAL — {len(self.nodos)} procesos",
                           fill=self.color, font=("Consolas", 10, "bold"), anchor="w")
            for n in self.nodos:
                n["x"] += n["vx"]; n["y"] += n["vy"]
                if n["x"] < 20 or n["x"] > cw_n-20: n["vx"] *= -1
                if n["y"] < 20 or n["y"] > ch_n-20: n["vy"] *= -1
                n["ax"] = nx_off + n["x"]
                n["ay"] = ny_off + n["y"]
            for i, n1 in enumerate(self.nodos):
                for j, n2 in enumerate(self.nodos):
                    if i >= j: continue
                    rel = (n1['ppid']==n2['pid'] or n2['ppid']==n1['pid'] or n1['folder']==n2['folder'])
                    if rel:
                        lc3 = "#00ff88" if (n1['cpu']>5 or n2['cpu']>5) else "#062030"
                        cc.create_line(n1["ax"], n1["ay"], n2["ax"], n2["ay"], fill=lc3, width=1)
            for n in self.nodos:
                nc = "#ff2a00" if n['cpu']>15 else ("#ffaa00" if n['cpu']>5 else "#00f0ff")
                cc.create_oval(n["ax"]-n["r"], n["ay"]-n["r"], n["ax"]+n["r"], n["ay"]+n["r"], fill=nc, outline="")
                cc.create_text(n["ax"], n["ay"]+n["r"]+5, text=n["name"], fill="#00a8b5", font=("Consolas", 7), anchor="n")

        elif self._active_tab == "ENTORNO":
            gc_x = CX_MID
            gc_y = CY_MID
            gr = min(CW, BODY_H) // 3
            self.ang_globo += 0.007
            for lat in range(-5, 6):
                lr = gr * math.cos(lat * math.pi / 6)
                ly2 = gc_y + gr * math.sin(lat * math.pi / 6)
                cc.create_oval(gc_x-lr, ly2-lr*0.2, gc_x+lr, ly2+lr*0.2, outline="#003544", width=1)
            for lon2 in range(8):
                el = lon2 * math.pi / 4 + self.ang_globo
                rx2 = gr * math.cos(el)
                col_g = "#005b66" if math.sin(el) > 0 else "#001b22"
                cc.create_oval(gc_x-abs(rx2), gc_y-gr, gc_x+abs(rx2), gc_y+gr, outline=col_g, width=1)
            cc.create_oval(gc_x-gr-3, gc_y-gr-3, gc_x+gr+3, gc_y+gr+3, outline=self.color, width=2)
            ptx, pty, pv = self._proyectar_globo(gc_x, gc_y, gr, self.lat, self.lon)
            if pv:
                sz = 4 + abs(math.sin(self.fotogramas*0.1)*4)
                cc.create_oval(ptx-sz, pty-sz, ptx+sz, pty+sz, outline="#ff2a00", width=2)
                cc.create_text(ptx+8, pty, text=self.ubica[:20], fill="#ff2a00", font=("Consolas", 8), anchor="w")
            for ip, (ip_lat, ip_lon) in self._ip_map_pts.items():
                ipx, ipy, ipv = self._proyectar_globo(gc_x, gc_y, gr, ip_lat, ip_lon)
                if ipv:
                    cc.create_oval(ipx-3, ipy-3, ipx+3, ipy+3, fill="#ffff00", outline="")
                    if pv:
                        mx2 = (ptx+ipx)/2
                        my2 = (pty+ipy)/2 - math.hypot(ipx-ptx, ipy-pty)*0.2
                        cc.create_line(ptx, pty, mx2, my2, ipx, ipy, fill="#ffff00", width=1, smooth=True, dash=(3,5))
            gy2 = BODY_Y + 12
            cc.create_text(CX_START+16, gy2, text="ENTORNO Y GEOLOCALIZACIÓN", fill=self.color, font=("Consolas", 10, "bold"), anchor="w"); gy2 += 28
            for lbl, val in [("LAT", f"{self.lat:.4f}°"), ("LON", f"{self.lon:.4f}°"),
                              ("↓", self.net_down), ("↑", self.net_up),
                              ("IPs ext.", str(len(self._ip_map_pts))), ("Conexiones", str(len(self.conex_prev)))]:
                cc.create_text(CX_START+20, gy2, text=lbl, fill="#1a5060", font=("Consolas", 9, "bold"), anchor="w")
                cc.create_text(CX_START+140, gy2, text=val, fill="#00e5ff", font=("Consolas", 9, "bold"), anchor="w")
                gy2 += 20

        elif self._active_tab == "ALERTAS":
            ax2 = CX_START + 16
            ay2 = BODY_Y + 16
            cc.create_text(ax2, ay2, text="SISTEMA DE ALERTAS", fill=self.color, font=("Consolas", 11, "bold"), anchor="w"); ay2 += 30
            max_al2 = max(1, (BODY_H - 50) // 30)
            for lv, msg in self._build_alerts()[:max_al2]:
                lc4 = "#ff2a00" if lv in ("CRITICAL","ERROR") else ("#ffb700" if lv=="WARN" else "#00ff88")
                cc.create_rectangle(ax2, ay2-8, CX_START+CW-16, ay2+16, fill="#070f18", outline=lc4, width=1)
                cc.create_text(ax2+10, ay2+4, text=f"[{lv}]", fill=lc4, font=("Consolas", 9, "bold"), anchor="w")
                cc.create_text(ax2+80, ay2+4, text=msg[:80], fill="#d4f9ff", font=("Consolas", 9), anchor="w")
                ay2 += 30

        # ════════════════════════════════════════════════════════════════════
        #  FOOTER — log + subtítulo + comandos
        # ════════════════════════════════════════════════════════════════════
        foot_y = H - FOOT_H
        cc.create_rectangle(0, foot_y, W, H, fill="#030d15", outline="")
        cc.create_line(0, foot_y, W, foot_y, fill="#0d3a50", width=2)
        cc.create_rectangle(0, H-2, W, H, fill=self.color, outline="")  # acento inferior

        # Log
        log_w = W - 400
        cc.create_text(12, foot_y+7, text="LOG", fill="#0d4055", font=("Consolas", 7, "bold"), anchor="w")
        logs = self.logs_terminal if isinstance(self.logs_terminal, list) else getattr(self.logs_terminal, "_items", [])
        _lc = {"ERROR":"#ff4444","WARN":"#ffb700","OK":"#00ff88","SISTEMA":"#00e5ff","INFO":"#4a8ea0","CMD":"#cc44ff","SEC":"#ff9d00"}
        max_log = max(1, (FOOT_H-16) // 16)
        for idx, line in enumerate(logs[-max_log:]):
            raw = str(line)
            lc5 = "#2a5060"
            for tag, lcc in _lc.items():
                if tag in raw.upper(): lc5 = lcc; break
            cc.create_text(12, foot_y+16+idx*16, text=raw[:int(log_w/7)], fill=lc5, font=("Consolas", 8), anchor="w")

        # Subtítulo central
        _sub_c = {"Hablando":"#ffd000","Pensando":"#cc44ff","Escuchando":"#00f0ff","Error":"#ff2a00"}
        sub_col = _sub_c.get(self.estado, "#004466")
        cc.create_text(W//2, foot_y + FOOT_H//2, text=self.sub, fill=sub_col, font=("Consolas", 9, "bold"), anchor="center")

        # Campo de comandos
        inp_x = W - 384
        inp_y = foot_y + 6
        cc.create_text(inp_x, inp_y+8, text="> CMD", fill="#0d4055", font=("Consolas", 7, "bold"), anchor="w")
        dt_key = ahora - self.last_key_time
        if dt_key < 1.0:
            for gi in range(1, 4):
                cc.create_rectangle(inp_x-gi, inp_y+18-gi, inp_x+374+gi, inp_y+54+gi, outline=self.color, width=1)
        self.ifr.place(x=inp_x, y=inp_y+18, width=368, height=34)

        self.root.after(33, self.loop)


def run_hud(state=None):
    try:
        KitianHUD(shared_state=state)
    except Exception as e:
        traceback_str = (
            f"KITIAN HUD ERROR\n{type(e).__name__}: {e}\n"
            + __import__("traceback").format_exc()
        )
        print(traceback_str, flush=True)
        try:
            import tkinter.messagebox as mb
            mb.showerror("KITIAN HUD ERROR", traceback_str)
        except Exception:
            pass
        raise

if __name__ == "__main__":
    print("KI-TIAN X20 - modo standalone", flush=True)
    try:
        KitianHUD()
    except Exception as e:
        traceback_str = (
            f"KITIAN HUD ERROR\n{type(e).__name__}: {e}\n"
            + __import__("traceback").format_exc()
        )
        print(traceback_str, flush=True)
        try:
            import tkinter.messagebox as mb
            mb.showerror("KITIAN HUD ERROR", traceback_str)
        except Exception:
            pass
        raise

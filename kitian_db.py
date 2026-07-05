import sqlite3
import json
import time
from pathlib import Path

BASE_DIR = Path(__file__).parent
DB_PATH = BASE_DIR / "kitian_memory.db"

def _conn():
    c = sqlite3.connect(str(DB_PATH))
    c.execute("PRAGMA journal_mode=WAL")
    return c

def init():
    with _conn() as db:
        db.execute("""
            CREATE TABLE IF NOT EXISTS conversaciones (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                usuario TEXT,
                kitian TEXT
            )
        """)
        db.execute("""
            CREATE TABLE IF NOT EXISTS preferencias (
                clave TEXT PRIMARY KEY,
                valor TEXT
            )
        """)
        db.execute("""
            CREATE TABLE IF NOT EXISTS recordatorios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                texto TEXT,
                momento TEXT,
                activo INTEGER DEFAULT 1
            )
        """)
        db.commit()

def guardar_conversacion(usuario, kitian):
    init()
    with _conn() as db:
        db.execute(
            "INSERT INTO conversaciones (timestamp, usuario, kitian) VALUES (?,?,?)",
            (time.strftime("%Y-%m-%d %H:%M:%S"), usuario, kitian)
        )
        db.commit()

def obtener_contexto(limite=4):
    init()
    with _conn() as db:
        rows = db.execute(
            "SELECT usuario, kitian FROM conversaciones ORDER BY id DESC LIMIT ?",
            (limite,)
        ).fetchall()
    return [{"user": r[0], "kitian": r[1]} for r in reversed(rows)]

def set_pref(clave, valor):
    init()
    with _conn() as db:
        db.execute(
            "INSERT OR REPLACE INTO preferencias (clave, valor) VALUES (?,?)",
            (clave, valor)
        )
        db.commit()

def get_pref(clave, default=None):
    init()
    with _conn() as db:
        row = db.execute(
            "SELECT valor FROM preferencias WHERE clave=?", (clave,)
        ).fetchone()
    return row[0] if row else default

def add_recordatorio(texto, momento):
    init()
    with _conn() as db:
        db.execute(
            "INSERT INTO recordatorios (texto, momento) VALUES (?,?)",
            (texto, momento)
        )
        db.commit()

def get_recordatorios_activos():
    init()
    with _conn() as db:
        return db.execute(
            "SELECT id, texto, momento FROM recordatorios WHERE activo=1"
        ).fetchall()

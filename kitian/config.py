import os
import json
import logging
from pathlib import Path
from openai import OpenAI

BASE_DIR = Path(__file__).resolve().parent.parent
CONFIG_FILE = BASE_DIR / "kitian_config.json"
DEFAULT_CONFIG = {"backend": "auto", "model": "auto"}
log = logging.getLogger("kitian")

# ─── Catálogo de backends gratuitos en orden de preferencia ──────────────────
# Kitian probará cada uno en orden hasta encontrar uno con clave configurada.
# Si ninguno tiene clave, cae a LM Studio local.
BACKEND_CATALOG = [
    {
        "name": "gemini",
        "label": "Google Gemini (gratis)",
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai/",
        "env_key": "GEMINI_API_KEY",
        "model": "gemini-2.0-flash",
        "get_key_url": "https://aistudio.google.com/apikey",
    },
    {
        "name": "groq",
        "label": "Groq (gratis, ultra rápido)",
        "base_url": "https://api.groq.com/openai/v1",
        "env_key": "GROQ_API_KEY",
        "model": "llama-3.3-70b-versatile",
        "get_key_url": "https://console.groq.com/keys",
    },
    {
        "name": "nous",
        "label": "Nous Research (gratis)",
        "base_url": "https://inference-api.nousresearch.com/v1",
        "env_key": "KITIAN_API_KEY",
        "model": "stepfun/step-3.7-flash:free",
        "get_key_url": "https://inference-api.nousresearch.com",
    },
    {
        "name": "openai",
        "label": "OpenAI (pago)",
        "base_url": "https://api.openai.com/v1",
        "env_key": "OPENAI_API_KEY",
        "model": "gpt-4o-mini",
        "get_key_url": "https://platform.openai.com/api-keys",
    },
]

LOCAL_FALLBACK = {
    "name": "gemini",
    "label": "Google Gemini (gratis)",
    "base_url": "https://generativelanguage.googleapis.com/v1beta/openai/",
    "env_key": "GEMINI_API_KEY",
    "model": "gemini-2.0-flash",
}


def cargar_env():
    try:
        from dotenv import load_dotenv
        load_dotenv(BASE_DIR / ".env")
        log.info(".env cargado")
    except ImportError:
        log.info("python-dotenv no instalado, usando variables de entorno del sistema")


cargar_env()


def cargar_config():
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(DEFAULT_CONFIG, f, indent=2, ensure_ascii=False)
    return dict(DEFAULT_CONFIG)


config = cargar_config()


def _resolver_backend():
    """Resuelve el backend activo según config y claves disponibles.
    
    Orden:
    1. Si config[backend] == 'auto' → prueba cada backend en BACKEND_CATALOG
       y usa el primero que tenga clave.
    2. Si config[backend] es un nombre específico → lo usa directamente.
    3. Fallback final: Google Gemini / nube gratuita.
    """
    backend_cfg = config.get("backend", "auto")
    model_cfg = config.get("model", "auto")

    # Nombre explícito en config
    if backend_cfg not in ("auto", "local", "lmstudio", "", None):
        for b in BACKEND_CATALOG:
            if b["name"] == backend_cfg:
                key = os.getenv(b["env_key"], "") if b["env_key"] else ""
                if not key:
                    log.warning(
                        "Backend '%s' configurado pero %s no está en .env → "
                        "obtené tu clave gratis en: %s",
                        b["name"], b["env_key"], b.get("get_key_url", ""),
                    )
                model = model_cfg if model_cfg not in ("auto", "", None) else b["model"]
                return OpenAI(base_url=b["base_url"], api_key=key or "no-key"), model, b["name"]

    # Auto: primer backend con clave disponible
    if backend_cfg in ("auto", "local", "lmstudio"):
        for b in BACKEND_CATALOG:
            key = os.getenv(b["env_key"] or "", "") if b["env_key"] else None
            if key:
                log.info("Backend auto-seleccionado: %s", b["label"])
                model = b["model"]
                return OpenAI(base_url=b["base_url"], api_key=key), model, b["name"]
        log.warning(
            "No hay claves de API configuradas. Usando Google Gemini (nube).\n"
            "Para activar IA gratuita agrega tus claves en C:\\Temp\\kitian\\.env:\n"
            "  GEMINI_API_KEY  → https://aistudio.google.com/apikey (gratis)\n"
            "  GROQ_API_KEY    → https://console.groq.com/keys (gratis)\n"
            "  KITIAN_API_KEY  → https://inference-api.nousresearch.com (gratis)"
        )

    # Fallback nube (sin requerir recursos locales)
    fb = LOCAL_FALLBACK
    key_fb = os.getenv(fb["env_key"] or "", "no-key") if fb["env_key"] else "no-key"
    return OpenAI(base_url=fb["base_url"], api_key=key_fb), fb["model"], fb["name"]


def crear_cliente():
    return _resolver_backend()


client, current_model, active_backend = crear_cliente()
log.info("Kitian iniciado | Backend: %s | Modelo: %s", active_backend, current_model)

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
# Si ninguno tiene clave, cae a modo local sin cliente OpenAI.
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
        log.info("python-dotenv no instalado, usando variables del sistema")


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


def _noop_client():
    class _X:
        class chat:
            class completions:
                @staticmethod
                def create(*a, **k):
                    raise RuntimeError("Sin API keys: cliente IA desactivado.")
    return _X()


def crear_cliente():
    fb = LOCAL_FALLBACK
    backend_cfg = config.get("backend", "auto")
    model_cfg = config.get("model", "auto")

    if backend_cfg not in ("auto", "local", "lmstudio", "", None):
        for b in BACKEND_CATALOG:
            if b["name"] == backend_cfg:
                key = os.getenv(b["env_key"] or "", "")
                if not key:
                    log.warning(
                        "Backend '%s' configurado pero %s no está en .env -> "
                        "obtené tu clave en: %s",
                        b["name"], b["env_key"], b.get("get_key_url", ""),
                    )
                model = model_cfg if model_cfg not in ("auto", "", None) else b["model"]
                return OpenAI(base_url=b["base_url"], api_key=key or "no-key"), model, b["name"]

    for b in BACKEND_CATALOG:
        key = os.getenv(b["env_key"] or "", "")
        if key:
            log.info("Backend auto-seleccionado: %s", b["label"])
            model = model_cfg if model_cfg not in ("auto", "", None) else b["model"]
            return OpenAI(base_url=b["base_url"], api_key=key), model, b["name"]

    log.warning(
        "Sin API keys: se fuerza modo local (sin proveedor de IA).\n"
        "Agregá tus claves en C:\\Temp\\kitian\\.env: "
        "GEMINI_API_KEY, GROQ_API_KEY, KITIAN_API_KEY."
    )
    return _noop_client(), fb["model"], "local"


client, current_model, active_backend = crear_cliente()
log.info("Kitian iniciado | Backend: %s | Modelo: %s", active_backend, current_model)

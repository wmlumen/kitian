"""Kitian Multiagent — orquestación ligera con herramientas locales y fallback.

Workers:
- research: búsqueda web/material accesible
- audit: revisión estática local con corte rápido
- writer: generación local de código/documentación
- operator: ejecución/estructura; nunca hace lo obvio sin pedirlo
- chat: respuesta directa

Herramientas disponibles como funciones puras con contrato de salida.
"""

from __future__ import annotations

import ast
import json
import logging
import os
import re
import shlex
import subprocess
from typing import Any

from openai import OpenAI

from kitian.config import config

log = logging.getLogger("kitian.multiagent")

_BACKENDS = {
    "openai": lambda: OpenAI(api_key=os.getenv("OPENAI_API_KEY", "") or "missing"),
    "zai": lambda: OpenAI(
        api_key=os.getenv("ZAI_API_KEY", "") or "missing",
        base_url="https://api.z.ai/api/paas/v4/",
    ),
    "gemini": lambda: OpenAI(
        base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
        api_key=os.getenv("GEMINI_API_KEY", "") or "missing",
    ),
    "groq": lambda: OpenAI(
        base_url="https://api.groq.com/openai/v1",
        api_key=os.getenv("GROQ_API_KEY", "") or "missing",
    ),
    "nous": lambda: OpenAI(
        base_url="https://inference-api.nousresearch.com/v1",
        api_key=os.getenv("KITIAN_API_KEY", "") or "missing",
    ),
}

_CHAT_MODELS = {
    "openai": "gpt-4o-mini",
    "zai": "glm-5.2",
    "gemini": "gemini-2.0-flash",
    "groq": "llama-3.3-70b-versatile",
    "nous": "stepfun/step-3.7-flash:free",
}

_FALLBACK_ORDER = ["gemini", "groq", "nous", "openai", "zai"]


_CURRENT_BACKEND_KEY = (
    config.get("backend", "gemini")
    if isinstance(config, dict)
    else getattr(config, "backend", "gemini")
)
_CURRENT_MODEL = (
    config.get("model", "gemini-2.0-flash")
    if isinstance(config, dict)
    else getattr(config, "model", "gemini-2.0-flash")
)


def _model_for(key: str) -> str:
    cfg = (
        (config.get("backends") or {}).get(key, {})
        if isinstance(config, dict)
        else getattr(config, "backends", {}).get(key, {})
    )
    return cfg.get("model") or _CHAT_MODELS.get(key, _CURRENT_MODEL)


def route_intent(text: str) -> str:
    if not text:
        return "chat"
    t = text.lower()
    if any(k in t for k in ["busca ", "investiga", "web", "github", "investig", "paper"]):
        return "research"
    if any(k in t for k in ["analiza", "errores", "audit", "revisa", "refactor"]):
        return "audit"
    if any(k in t for k in ["file", "archivo", "crea ", "escribe ", "genera"]):
        return "writer"
    if any(k in t for k in ["deploy", "docker", "probar", "ejecuta", "test"]):
        return "operator"
    return "chat"


def _system_for(worker: str) -> str:
    systems = {
        "chat": "Sos Kitian: conciso, ejecutivo, español.",
        "research": "Sos un agente de investigación web/código. Prioriza fuentes accesibles y pasos accionables.",
        "audit": "Sos un revisor estático. Devuelve solo hallazgos accionables con nivel [LOW|MEDIUM|HIGH] y ruta de archivo.",
        "writer": "Sos un generador de código/documentación. Seguí el estilo del proyecto Kitian.",
        "operator": "Sos un operador de sistemas. Datos concretos: comando, riesgo, blocker.",
    }
    return systems.get(worker, systems["chat"])


# -----------------------------------------------------------------------------
# Herramientas locales puras
# -----------------------------------------------------------------------------

_TOOL_REGISTRY: dict[str, Any] = {}


def tool(fn):
    _TOOL_REGISTRY[fn.__name__] = fn
    return fn


@tool
def py_syntax_check(path: str) -> dict[str, Any]:
    try:
        with open(path, "r", encoding="utf-8") as f:
            ast.parse(f.read(), filename=path)
        return {"ok": True, "path": path, "finding": "AST OK"}
    except SyntaxError as e:
        return {"ok": False, "path": path, "finding": f"SyntaxError: {e.msg}:{e.lineno}"}


@tool
def py_ast_nodes(path: str, kinds: str = "function,class") -> dict[str, Any]:
    try:
        with open(path, "r", encoding="utf-8") as f:
            tree = ast.parse(f.read(), filename=path)
        wanted = {s.strip() for s in kinds.split(",") if s.strip()}
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and "function" in wanted:
                out.append({"kind": "function", "name": node.name, "lineno": node.lineno})
            elif isinstance(node, ast.AsyncFunctionDef) and "function" in wanted:
                out.append({"kind": "async_function", "name": node.name, "lineno": node.lineno})
            elif isinstance(node, ast.ClassDef) and "class" in wanted:
                out.append({"kind": "class", "name": node.name, "lineno": node.lineno})
        return {"ok": True, "path": path, "nodes": out[:80]}
    except Exception as e:
        return {"ok": False, "path": path, "nodes": [], "error": str(e)}


@tool
def web_search(query: str, limit: int = 5) -> dict[str, Any]:
    try:
        from hermes_tools import web_search as hs
        payload = hs(query, limit=limit) or {"data": {"web": []}}
        items = (payload.get("data") or {}).get("web", [])[:limit]
        out = [{"title": i.get("title"), "url": i.get("url"), "description": i.get("description")} for i in items]
        return {"ok": True, "query": query, "results": out}
    except Exception as e:
        return {"ok": False, "query": query, "error": str(e)}


@tool
def run_cmd(command: str, timeout: int = 10) -> dict[str, Any]:
    try:
        args = shlex.split(command)
        cp = subprocess.run(args, capture_output=True, text=True, timeout=timeout)
        return {
            "ok": cp.returncode == 0,
            "command": command,
            "code": cp.returncode,
            "stdout": cp.stdout[-2000:],
            "stderr": cp.stderr[-1000:],
        }
    except Exception as e:
        return {"ok": False, "command": command, "error": str(e)}


def tool_call(name: str, arguments: dict[str, Any] | None = None) -> dict[str, Any]:
    fn = _TOOL_REGISTRY.get(name)
    if not fn:
        return {"ok": False, "error": f"tool not found: {name}", "available": sorted(_TOOL_REGISTRY)}
    try:
        return fn(**(arguments or {}))
    except TypeError as e:
        return {"ok": False, "error": f"bad arguments: {e}", "available_args": name}


def tool_prompt_for(query: str) -> list[dict[str, Any]]:
    if not query.strip():
        return []
    prompt = (
        "Si la consulta necesita verificar sintaxis Python, devolvé SOLO JSON:\n"
        '{"tool":"py_syntax_check","args":{"path":"path/al/archivo.py"}}\n'
        "Si necesita fuentes web, devolvé SOLO JSON:\n"
        '{"tool":"web_search","args":{"query":"...", "limit":5}}}\n'
        "Si necesita ejecutar comando local (bash/git/ls/grep), devolvé SOLO JSON:\n"
        '{"tool":"run_cmd","args":{"command":"git status --porcelain"}}'
    )
    return [
        {"role": "system", "content": prompt},
        {"role": "user", "content": query},
    ]


def parse_tool_output(text: str) -> dict[str, Any] | None:
    s = (text or "").strip()
    for prefix in ["```json", "```"]:
        if s.startswith(prefix):
            s = s[len(prefix):]
    if s.endswith("```"):
        s = s[:-3]
    s = s.strip()
    if not (s.startswith("{") and s.endswith("}")):
        return None
    try:
        return json.loads(s)
    except json.JSONDecodeError:
        return None


# -----------------------------------------------------------------------------
# Core trial/call/fallback
# -----------------------------------------------------------------------------

def call(prompt: str, worker: str, model: str | None = None, backend: str | None = None) -> dict[str, Any]:
    order = [backend] if backend in _BACKENDS else _fallback_order_for(worker)
    last_err = None
    for key in order:
        try:
            client = _BACKENDS[key]()
            use_model = model or _model_for(key)
            log.info("multiagent call worker=%s backend=%s model=%s", worker, key, use_model)
            messages = [
                {"role": "system", "content": _system_for(worker)},
                {"role": "user", "content": prompt},
            ]
            if worker == "audit":
                messages.extend(tool_prompt_for(prompt))
            completion = client.chat.completions.create(
                model=use_model,
                messages=messages,
                temperature=0.3 if worker == "audit" else 0.6,
                max_tokens=700,
            )
            text = (completion.choices[0].message.content or "").strip()
            if not text:
                text = "(respuesta vacía)"
            tool_hit = None
            if worker == "audit":
                tool_hit = parse_tool_output(text)
                if tool_hit:
                    tool_hit = tool_call(tool_hit.get("tool", ""), tool_hit.get("args") or {})
            return {
                "ok": True,
                "worker": worker,
                "model": use_model,
                "backend": key,
                "text": text,
                "meta": {"tool_hit": tool_hit} if tool_hit else {},
            }
        except Exception as e:
            last_err = f"{type(e).__name__}: {e}"
            log.warning("multiagent failed backend=%s error=%s", key, last_err)
    short = last_err or "backend unavailable"
    fallback_prompt = (
        "Necesito salida local corta y accionable. "
        "Usá el modo fallback y dividí el problema en pasos verificables."
    )
    local_best = try_local_fallback(prompt if worker != "audit" else fallback_prompt, worker)
    return {
        "ok": bool(local_best),
        "worker": worker,
        "model": model,
        "backend": order[0] if order else "local",
        "text": local_best or f"Sin acceso a backends externos. Detalle: {short}.",
        "meta": {"error": short, "fallback": True},
    }


def try_local_fallback(prompt: str, worker: str) -> str:
    try:
        client = _BACKENDS["local"]()
        completion = client.chat.completions.create(
            model=_model_for("local"),
            messages=[
                {"role": "system", "content": _system_for(worker)},
                {"role": "user", "content": prompt},
            ],
            temperature=0.5,
            max_tokens=300,
        )
        return (completion.choices[0].message.content or "").strip()
    except Exception:
        return ""


def remote_call(url: str, prompt: str, worker: str, backend: str | None = None) -> dict[str, Any]:
    try:
        w = (backend or "").strip().lower() or route_intent(prompt)
        body = json.dumps({"mensaje": prompt, "worker": w}).encode("utf-8")
        req = urllib.request.Request(url, data=body, method="POST")
        with urllib.request.urlopen(req, timeout=20) as r:
            payload = json.loads(r.read().decode("utf-8", errors="replace"))
        return {
            "ok": True,
            "worker": w,
            "model": payload.get("model"),
            "backend": "remote",
            "text": payload.get("text", "") or try_local_fallback(prompt, w),
            "meta": {"remote": url},
        }
    except Exception as e:
        short = f"{type(e).__name__}: {e}"
        local = try_local_fallback(prompt, worker)
        return {
            "ok": bool(local),
            "worker": worker,
            "model": _model_for("local"),
            "backend": "local",
            "text": local or f"Remoto falló: {short}",
            "meta": {"error": short, "fallback": True},
        }


def _fallback_order_for(worker: str, preferred: str | None = None) -> list[str]:
    order = []
    if preferred and preferred in _BACKENDS and preferred not in order:
        order.append(preferred)
    base = _FALLBACK_ORDER if worker != "audit" else ["openai", "groq", "gemini", "nous", "local"]
    for key in base:
        if key not in order:
            order.append(key)
    return order


def handle(query: str, preferred_backend: str | None = None, remote_url: str | None = None) -> dict[str, Any]:
    if remote_url:
        worker = route_intent(query)
        out = remote_call(remote_url, query, worker=worker, backend=preferred_backend)
    else:
        worker = route_intent(query)
        out = call(prompt=query, worker=worker, backend=preferred_backend)
    return {
        "ok": out.get("ok", False),
        "worker": worker,
        "model": out.get("model"),
        "backend": out.get("backend"),
        "text": out.get("text", ""),
        "error": (out.get("meta") or {}).get("error") if not out.get("ok") else None,
    }


def backend_status() -> dict[str, Any]:
    status = {}
    for key in list(_BACKENDS.keys()) + ["local"]:
        try:
            client = _BACKENDS[key]()
            status[key] = "configured" if "not-needed" not in getattr(client.api_key, "get_secret_value", lambda: client.api_key)() else "open"
        except Exception as e:
            status[key] = f"error: {type(e).__name__}"
    return status

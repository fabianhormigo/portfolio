# -*- coding: utf-8 -*-
"""
Adaptador de proveedor de IA — "trae tu propio modelo" (BYO-model).
===================================================================

Abstrae DE QUÉ proveedor y modelo de IA se obtiene la extracción, para que el
cliente pueda facilitar los suyos sin tocar código. Soporta:

  - "ollama"  -> API de Ollama (daemon local en GPU, o Ollama Cloud).
  - "openai"  -> cualquier servidor compatible con la API de OpenAI
                 (OpenAI, OpenRouter, Together, Groq, LM Studio, vLLM, ...).

La configuración se resuelve por precedencia:  argumentos > variables de
entorno (.env) > valores por defecto.  Variables reconocidas:

  IA_PROVIDER   ollama | openai
  IA_MODELO     nombre del modelo
  IA_BASE_URL   raíz del endpoint (sin la ruta /api/... o /chat/completions)
  IA_API_KEY    clave del proveedor (o, por compatibilidad, OLLAMA_API_KEY)

Forma parte del MOTOR (ver ADR-0004): no sabe nada de HTML ni de PDFs; recibe
un prompt + texto y devuelve el JSON que produjo el modelo.
"""

import json
import os
import pathlib
import urllib.request
from dataclasses import dataclass

# Endpoints por defecto de cada proveedor (la ruta se añade en cada adaptador).
OLLAMA_LOCAL = "http://localhost:11434"
OLLAMA_CLOUD = "https://ollama.com"
OPENAI_DEFAULT = "https://api.openai.com/v1"

MODELO_DEF = {"ollama": "mistral:7b", "openai": "gpt-4o-mini"}

# Parámetros de generación (deterministas: temperatura 0, salida JSON).
TIMEOUT = 600       # alto: modelos cloud/grandes tardan
NUM_CTX = 8192      # ventana de contexto (solo Ollama)
TEMPERATURE = 0


def cargar_dotenv(proj=None):
    """Carga `.env` (KEY=VALUE) al entorno sin pisar variables ya definidas.

    Tolera un BOM inicial (utf-8-sig). Sin dependencias externas. Idempotente.
    """
    base = pathlib.Path(proj) if proj else pathlib.Path(__file__).resolve().parent.parent
    env_file = base / ".env"
    if not env_file.exists():
        return
    for raw in env_file.read_text(encoding="utf-8-sig").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        k = k.strip()
        v = v.strip().strip('"').strip("'")
        if k and k not in os.environ:
            os.environ[k] = v


@dataclass
class ConfigIA:
    """Qué proveedor/modelo de IA usar. Lo facilita el cliente (BYO-model)."""
    proveedor: str
    modelo: str
    base_url: str
    api_key: str = None
    timeout: int = TIMEOUT
    num_ctx: int = NUM_CTX
    temperature: float = TEMPERATURE

    def descripcion(self):
        destino = self.base_url
        clave = "con clave" if self.api_key else "sin clave"
        return f"{self.proveedor} · {self.modelo} · {destino} · {clave}"


def cargar_config_ia(proveedor=None, modelo=None, base_url=None, api_key=None, cloud=False):
    """Resuelve la configuración de IA: argumentos > entorno (.env) > defaults.

    `cloud=True` es un atajo de compatibilidad: con proveedor ollama y sin
    base_url, apunta a Ollama Cloud en vez del daemon local.
    """
    proveedor = (proveedor or os.environ.get("IA_PROVIDER") or "ollama").strip().lower()
    if proveedor not in ("ollama", "openai"):
        raise ValueError(f"proveedor de IA no soportado: {proveedor!r} (usa 'ollama' u 'openai')")

    modelo = modelo or os.environ.get("IA_MODELO") or MODELO_DEF[proveedor]

    if not base_url:
        base_url = os.environ.get("IA_BASE_URL")
    if not base_url:
        if proveedor == "ollama":
            base_url = OLLAMA_CLOUD if cloud else OLLAMA_LOCAL
        else:
            base_url = OPENAI_DEFAULT

    if not api_key:
        api_key = os.environ.get("IA_API_KEY")
    if not api_key and proveedor == "ollama":
        api_key = os.environ.get("OLLAMA_API_KEY")  # compatibilidad

    return ConfigIA(proveedor=proveedor, modelo=modelo, base_url=base_url, api_key=api_key)


def _json_seguro(s):
    """Parsea JSON tolerando que el modelo lo envuelva (```json ... ``` o texto).

    Si el parseo directo falla, extrae el primer bloque {...}. Si aun asi falla,
    deja que la excepcion suba (para que el llamador reintente).
    """
    s = (s or "").strip()
    try:
        return json.loads(s)
    except json.JSONDecodeError:
        i, j = s.find("{"), s.rfind("}")
        if i != -1 and j > i:
            return json.loads(s[i:j + 1])
        raise


def _post_json(url, payload, headers, timeout):
    req = urllib.request.Request(
        url, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST")
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())


def _generar_ollama(cfg, contenido):
    payload = {
        "model": cfg.modelo,
        "prompt": contenido,
        "stream": False,
        "format": "json",
        "options": {"temperature": cfg.temperature, "num_ctx": cfg.num_ctx},
    }
    headers = {"Content-Type": "application/json"}
    if cfg.api_key:
        headers["Authorization"] = "Bearer " + cfg.api_key
    resp = _post_json(cfg.base_url.rstrip("/") + "/api/generate", payload, headers, cfg.timeout)
    return _json_seguro(resp.get("response", "{}"))


def _generar_openai(cfg, contenido):
    if not cfg.api_key:
        raise ValueError("el proveedor 'openai' requiere una API key (IA_API_KEY o --api-key)")
    payload = {
        "model": cfg.modelo,
        "messages": [{"role": "user", "content": contenido}],
        "temperature": cfg.temperature,
        "response_format": {"type": "json_object"},
    }
    headers = {"Content-Type": "application/json", "Authorization": "Bearer " + cfg.api_key}
    resp = _post_json(cfg.base_url.rstrip("/") + "/chat/completions", payload, headers, cfg.timeout)
    contenido_resp = resp["choices"][0]["message"]["content"]
    return _json_seguro(contenido_resp or "{}")


def generar_json(cfg, prompt, texto):
    """Envía (prompt + texto) al proveedor configurado y devuelve el JSON parseado.

    Independiente del dominio: no sabe qué se extrae, solo orquesta la llamada.
    """
    contenido = (prompt or "") + (texto or "")
    if cfg.proveedor == "ollama":
        return _generar_ollama(cfg, contenido)
    if cfg.proveedor == "openai":
        return _generar_openai(cfg, contenido)
    raise ValueError(f"proveedor de IA no soportado: {cfg.proveedor!r}")


def _texto_ollama(cfg, mensajes, temperature):
    payload = {
        "model": cfg.modelo, "messages": mensajes, "stream": False,
        "options": {"temperature": temperature, "num_ctx": cfg.num_ctx},
    }
    headers = {"Content-Type": "application/json"}
    if cfg.api_key:
        headers["Authorization"] = "Bearer " + cfg.api_key
    resp = _post_json(cfg.base_url.rstrip("/") + "/api/chat", payload, headers, cfg.timeout)
    return (resp.get("message") or {}).get("content", "").strip()


def _texto_openai(cfg, mensajes, temperature):
    if not cfg.api_key:
        raise ValueError("el proveedor 'openai' requiere una API key (IA_API_KEY o --api-key)")
    payload = {"model": cfg.modelo, "messages": mensajes, "temperature": temperature}
    headers = {"Content-Type": "application/json", "Authorization": "Bearer " + cfg.api_key}
    resp = _post_json(cfg.base_url.rstrip("/") + "/chat/completions", payload, headers, cfg.timeout)
    return (resp["choices"][0]["message"]["content"] or "").strip()


def generar_texto(cfg, sistema, usuario, historial=None, temperature=0.2):
    """Genera TEXTO libre (no JSON) tipo chat: sistema + historial + turno usuario.

    `historial` es una lista opcional de {"rol": "user"|"assistant", "texto": ...}.
    Para chatbots/redacción. Temperatura algo > 0 para lenguaje natural.
    """
    mensajes = [{"role": "system", "content": sistema or ""}]
    for m in (historial or []):
        rol = "assistant" if m.get("rol") == "assistant" else "user"
        mensajes.append({"role": rol, "content": m.get("texto", "")})
    mensajes.append({"role": "user", "content": usuario or ""})
    if cfg.proveedor == "ollama":
        return _texto_ollama(cfg, mensajes, temperature)
    if cfg.proveedor == "openai":
        return _texto_openai(cfg, mensajes, temperature)
    raise ValueError(f"proveedor de IA no soportado: {cfg.proveedor!r}")

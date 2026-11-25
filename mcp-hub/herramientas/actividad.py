"""Registro de actividad del MCP: cada llamada deja eventos en .actividad/eventos.jsonl.

El panel (panel/panel.py) los lee para iluminar en directo la pieza que se está usando.
Nunca rompe una llamada: si no puede escribir el evento, sigue.
"""
import functools
import json
import os
import threading
import time
from pathlib import Path

DIR = Path(__file__).resolve().parent.parent / ".actividad"
FICHERO = DIR / "eventos.jsonl"
MAX_BYTES = 2_000_000  # al superarlo se rota a eventos.1.jsonl
_lock = threading.Lock()


def _resumen(v, n=120):
    s = v if isinstance(v, str) else json.dumps(v, ensure_ascii=False, default=str)
    return s if len(s) <= n else s[:n] + "…"


def registrar(**ev):
    ev.setdefault("t", time.time())
    ev.setdefault("pid", os.getpid())
    try:
        with _lock:
            DIR.mkdir(exist_ok=True)
            if FICHERO.exists() and FICHERO.stat().st_size > MAX_BYTES:
                FICHERO.replace(DIR / "eventos.1.jsonl")
            with open(FICHERO, "a", encoding="utf-8") as fh:
                fh.write(json.dumps(ev, ensure_ascii=False, default=str) + "\n")
    except OSError:
        pass


def instrumentar(tipo: str, nombre: str):
    """Decorador: registra inicio/fin/error de una herramienta, recurso o prompt."""
    def deco(fn):
        @functools.wraps(fn)
        def envoltura(*args, **kwargs):
            idl = f"{os.getpid()}-{time.time_ns()}"
            registrar(id=idl, fase="inicio", tipo=tipo, nombre=nombre,
                      args={k: _resumen(v) for k, v in kwargs.items()})
            t0 = time.perf_counter()
            try:
                res = fn(*args, **kwargs)
            except Exception as e:
                registrar(id=idl, fase="error", tipo=tipo, nombre=nombre,
                          ms=round((time.perf_counter() - t0) * 1000, 1), error=_resumen(str(e), 300))
                raise
            registrar(id=idl, fase="fin", tipo=tipo, nombre=nombre,
                      ms=round((time.perf_counter() - t0) * 1000, 1))
            return res
        return envoltura
    return deco

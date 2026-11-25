"""Métricas del agente y del RAG. Funciones puras (sin modelos ni ficheros), con sus tests en test_metricas.py.

Fragmento de oro: el que pertenece al artículo de referencia Y contiene el dato esperado. Con él se mide cada etapa
por separado y, cuando una pregunta falla, se atribuye el fallo a la primera etapa que perdió ese fragmento.
"""
from __future__ import annotations

import math
import re
import unicodedata

KS = (1, 4, 6, 12)
ETAPAS = ("recuperacion", "lectura", "respuesta")


def normal(s: str) -> str:
    """NFKC (espacios duros, ligaduras) y sin guiones de corte, para comparar con expresiones regulares."""
    return unicodedata.normalize("NFKC", s).replace("­", "")


def coincide(patron: str, texto: str) -> bool:
    return re.search(patron, normal(texto), re.I) is not None


def fragmentos_oro(frags: list[dict], p: dict) -> list[str]:
    if p["ref"] is None:
        return []
    return [f["id"] for f in frags if f["sector"] == p["sector"] and f["ref"] == p["ref"] and coincide(p["esperado"], f["texto"])]


def posicion(ranking: list[str], oro: list[str]) -> int | None:
    """Posición (desde 1) del primer fragmento de oro, o None."""
    return next((n for n, i in enumerate(ranking, 1) if i in oro), None)


def recuperacion(posiciones: list[int | None]) -> dict:
    """hit@k y MRR sobre una lista de posiciones (None = no recuperado)."""
    n = len(posiciones)
    if not n:
        return {}
    m = {f"hit@{k}": sum(p is not None and p <= k for p in posiciones) / n for k in KS}
    return {**m, "mrr": sum(1 / p for p in posiciones if p) / n, "preguntas": n}


def percentil(valores: list[float], q: float) -> float:
    """Percentil por rango más cercano (sin interpolar)."""
    if not valores:
        return 0.0
    v = sorted(valores)
    return v[max(0, math.ceil(q / 100 * len(v)) - 1)]


def correccion(p: dict, estado: str, respuesta: str) -> bool:
    """Con respuesta: respaldada y con el dato. Sin respuesta en el corpus: no debe darse por respaldada."""
    if p["ref"] is None:
        return estado != "respaldada"
    return estado == "respaldada" and coincide(p["esperado"], respuesta)


def etapa_fallida(oro: list[str], vistos: list[str], anotados: list[str] | None) -> str:
    """Primera etapa que perdió la evidencia. `anotados` es None en las líneas base (no hay lectura por separado)."""
    if not set(oro) & set(vistos):
        return "recuperacion"
    if anotados is not None and not set(oro) & set(anotados):
        return "lectura"
    return "respuesta"


def agregar(filas: list[dict]) -> dict:
    """Resumen de las filas de un modo y un conjunto."""
    con = [f for f in filas if f["ref"]]
    sin = [f for f in filas if not f["ref"]]
    tasa = lambda xs: sum(xs) / len(xs) if xs else None  # noqa: E731
    m = {
        "preguntas": len(filas), "con_respuesta": len(con), "sin_respuesta": len(sin),
        "correctas": sum(f["correcta"] for f in con), "exactitud": tasa([f["correcta"] for f in con]),
        "cita_articulo": tasa([bool(f["correcta"] and f["articulo"]) for f in con]),
        "negativas": sum(f["correcta"] for f in sin),
        "negativas_falsas": sum(f["estado"] != "respaldada" for f in con),
        # respuesta dada como respaldada que no es correcta: el error más peligroso
        "errores_confiados": sum(f["estado"] == "respaldada" and not f["correcta"] for f in filas),
        "max_entrada": max((f["max_entrada"] for f in filas), default=0),
        "tokens_medios": round(sum(f["tokens"] for f in filas) / len(filas)) if filas else 0,
        "llamadas_medias": round(sum(f["llamadas"] for f in filas) / len(filas), 1) if filas else 0,
        "segundos_p50": percentil([f["segundos"] for f in filas], 50),
        "segundos_p95": percentil([f["segundos"] for f in filas], 95),
        "fallos": {e: sum(f.get("etapa") == e for f in con if not f["correcta"]) for e in ETAPAS},
    }
    return m


def embudo(filas: list[dict]) -> dict:
    """Del agente: cuántas preguntas conservan la evidencia tras cada etapa."""
    con = [f for f in filas if f["ref"]]
    return {"preguntas": len(con), "recuperada": sum(f["oro_leido"] for f in con), "anotada": sum(f["oro_anotado"] for f in con),
            "correcta": sum(f["correcta"] for f in con),
            "citas_leidas": sum(f["lecturas"] for f in filas), "citas_no_literales": sum(f["no_literales"] for f in filas)}

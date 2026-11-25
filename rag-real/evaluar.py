"""Evaluación reproducible: recuperación (BM25 / vector / híbrido) y respuesta completa. Escribe resultados/."""
from __future__ import annotations

import json
import time
from pathlib import Path

from datos import CORPUS, PREGUNTAS, RESERVADAS
from rag import EMBED, LLM, Rag

SALIDA = Path(__file__).resolve().parent / "resultados"


def acierta(esperado: str, respuesta: str) -> bool:
    """El valor esperado aparece como palabra completa (o como raíz si es texto)."""
    import re
    patron = rf"(?<![\d,]){re.escape(esperado)}(?![\d,])" if esperado[0].isdigit() else re.escape(esperado)
    return re.search(patron, respuesta.lower()) is not None


def main() -> None:
    rag = Rag(CORPUS)
    con = [p for p in PREGUNTAS if p["gold"]]
    recuperacion = {}
    for modo in ("bm25", "vector", "hibrido"):
        tops = [(p["gold"], rag.recuperar(p["pregunta"], p["norma"], p["version"], modo)) for p in con]
        recuperacion[modo] = {"acierto@1": sum(t[:1] == [g] for g, t in tops) / len(con),
                              "acierto@3": sum(g in t for g, t in tops) / len(con)}
        print(modo, recuperacion[modo], flush=True)

    resumen = {"modelos": {"embeddings": EMBED, "llm": LLM}, "fragmentos": len(CORPUS),
               "recuperacion": recuperacion, "generacion": {}}
    detalle = []
    for conjunto, preguntas in (("desarrollo", PREGUNTAS), ("reservado", RESERVADAS)):
        for vp in (1, 2):
            filas = []
            for p in preguntas:
                t0 = time.time()
                r = rag.preguntar(p["pregunta"], p["norma"], p["version"], vp)
                # v1 no rechazaba respuestas vacías: se puntúa igual (una respuesta vacía no acierta)
                ok = (r["estado"] == "sin_evidencia") if p["gold"] is None else (
                    r["estado"] == "valida" and acierta(p["esperado"], r["respuesta"])
                    and r["id"].strip("[] ") == p["gold"])
                filas.append({**p, **r, "conjunto": conjunto, "prompt": vp, "correcta": ok,
                              "segundos": round(time.time() - t0, 1)})
            con_r = [f for f in filas if f["gold"]]
            sin = [f for f in filas if not f["gold"]]
            m = {"respondidas_bien": sum(f["correcta"] for f in con_r), "con_respuesta": len(con_r),
                 "negativas_bien": sum(f["correcta"] for f in sin), "sin_respuesta": len(sin),
                 "rechazadas_por_validacion": sum(f["estado"] == "rechazada" for f in filas),
                 "version_equivocada": sum(f["estado"] == "valida" and f["version"] not in f["id"] for f in filas),
                 "mediana_segundos": sorted(f["segundos"] for f in filas)[len(filas) // 2]}
            resumen["generacion"][f"{conjunto}_v{vp}"] = m
            detalle += filas
            print(conjunto, "prompt", vp, m, flush=True)
    SALIDA.mkdir(exist_ok=True)
    (SALIDA / "resumen.json").write_text(json.dumps(resumen, ensure_ascii=False, indent=2), encoding="utf-8")
    (SALIDA / "detalle.json").write_text(json.dumps(detalle, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()

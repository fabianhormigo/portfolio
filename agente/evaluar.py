"""Evaluación completa: recuperación, agente por etapas y dos líneas base con la misma ventana de 4096 tokens.

    python agente/evaluar.py             -> resultados/evaluacion.json, grabaciones.json y la documentación
    python agente/evaluar.py --reanudar  continúa una ejecución interrumpida

Modos: simple (RAG con 4 fragmentos), volcado (12 fragmentos de golpe) y agente (lectura aislada + notas).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import platform
import time
from datetime import date

import informe
import metricas as M
from agente import AQUI, EMBED, LECTURAS, NUM_CTX, Indice, investigar, rag_simple

MODELO = "qwen2.5:7b-instruct"
LINEAS_BASE = (("simple", 4), ("volcado", 12))
GRABAR = {0, 5, 8, 10, 11, 13, 16}     # preguntas que se reproducen en la web
SALIDA = AQUI / "resultados"
PARCIAL = SALIDA / "parcial.jsonl"


def huella() -> str:
    """Cambia si cambia el código, las preguntas o el modelo: un parcial antiguo no se reutiliza."""
    datos = b"".join((AQUI / f).read_bytes() for f in ("agente.py", "preguntas.json", "metricas.py"))
    return hashlib.sha256(datos + MODELO.encode()).hexdigest()[:16]


def medir_recuperacion(indice: Indice, p: dict, oro: list[str]) -> dict:
    return {m: M.posicion(indice.buscar(p["q"], p["sector"], max(M.KS), m), oro) for m in ("bm25", "vector", "hibrido")}


def evaluar_base(indice: Indice, p: dict, oro: list[str], modo: str, k: int) -> dict:
    t0 = time.perf_counter()
    r = rag_simple(indice, p["q"], p["sector"], MODELO, k)
    vistos = indice.buscar(p["q"], p["sector"], k)
    ok = M.correccion(p, r["estado"], r["respuesta"])
    return {"modo": modo, "correcta": ok, "articulo": p["ref"] in r["refs"] if p["ref"] else None, "estado": r["estado"],
            "respuesta": r["respuesta"], "max_entrada": r["ctx"]["entrada"], "tokens": r["ctx"]["entrada"] + r["ctx"]["salida"],
            "llamadas": 1, "segundos": round(time.perf_counter() - t0, 1),
            "etapa": None if ok or not p["ref"] else M.etapa_fallida(oro, vistos, None)}


def evaluar_agente(indice: Indice, p: dict, oro: list[str]) -> tuple[dict, list[dict]]:
    eventos = list(investigar(indice, p["q"], p["sector"], MODELO))
    fin, ctxs = eventos[-1], [e["ctx"] for e in eventos if e.get("ctx")]
    lecturas = [e for e in eventos if e["paso"] == "leer"]
    leidos = [e["id"] for e in lecturas]
    anotados = [e["id"] for e in lecturas if e["nota"]]
    ok = M.correccion(p, fin["estado"], fin["respuesta"])
    fila = {"modo": "agente", "correcta": ok, "articulo": p["ref"] in [c["ref"] for c in fin["citas"]] if p["ref"] else None,
            "estado": fin["estado"], "respuesta": fin["respuesta"], "max_entrada": max(c["entrada"] for c in ctxs),
            "tokens": sum(c["entrada"] + c["salida"] for c in ctxs), "llamadas": len(ctxs), "segundos": fin["segundos"],
            "lecturas": len(lecturas), "no_literales": sum(e["motivo"] == "cita no literal" for e in lecturas),
            "notas": len(anotados), "ampliada": any(e["paso"] == "ampliar" for e in eventos),
            "oro_leido": bool(set(oro) & set(leidos)), "oro_anotado": bool(set(oro) & set(anotados)),
            "etapa": None if ok or not p["ref"] else M.etapa_fallida(oro, leidos, anotados)}
    return fila, eventos


def evaluar_pregunta(indice: Indice, n: int, p: dict) -> dict:
    oro = M.fragmentos_oro(indice.frags, p)
    if p["ref"] and not oro:
        raise ValueError(f"Pregunta {n}: ningún fragmento de {p['ref']} contiene {p['esperado']!r}")
    filas = [evaluar_base(indice, p, oro, modo, k) for modo, k in LINEAS_BASE]
    agente, eventos = evaluar_agente(indice, p, oro)
    return {"n": n, "pregunta": p, "recuperacion": medir_recuperacion(indice, p, oro) if p["ref"] else None,
            "filas": [{**p, "n": n, **f} for f in (*filas, agente)], "eventos": eventos}


def resumir(res: list[dict]) -> dict:
    salida = {}
    for conj in ("desarrollo", "reservado"):
        sub = [r for r in res if r["pregunta"]["conjunto"] == conj]
        filas = [f for r in sub for f in r["filas"]]
        salida[conj] = {m: M.agregar([f for f in filas if f["modo"] == m]) for m in ("simple", "volcado", "agente")}
        salida[conj]["embudo"] = M.embudo([f for f in filas if f["modo"] == "agente"])
        salida[conj]["recuperacion"] = {m: M.recuperacion([r["recuperacion"][m] for r in sub if r["recuperacion"]])
                                        for m in ("bm25", "vector", "hibrido")}
    return salida


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--reanudar", action="store_true")
    a = ap.parse_args()
    indice = Indice()
    preguntas = json.loads((AQUI / "preguntas.json").read_text(encoding="utf-8"))
    SALIDA.mkdir(exist_ok=True)
    marca, hechas = huella(), {}
    if a.reanudar and PARCIAL.exists():
        for linea in PARCIAL.read_text(encoding="utf-8").splitlines():
            r = json.loads(linea)
            if r["huella"] == marca:
                hechas[r["n"]] = r
    else:
        PARCIAL.unlink(missing_ok=True)
    for n, p in enumerate(preguntas):
        if n not in hechas:
            hechas[n] = {**evaluar_pregunta(indice, n, p), "huella": marca}
            with PARCIAL.open("a", encoding="utf-8") as fh:      # cada pregunta queda guardada
                fh.write(json.dumps(hechas[n], ensure_ascii=False) + "\n")
        marcas = " ".join(f"{f['modo']}:{'ok' if f['correcta'] else 'MAL:' + str(f['etapa'])}" for f in hechas[n]["filas"])
        print(f"{n + 1:2d}/{len(preguntas)} {marcas}", flush=True)
    res = [hechas[n] for n in range(len(preguntas))]
    datos = {"fecha": date.today().isoformat(), "modelo": MODELO, "embeddings": EMBED, "num_ctx": NUM_CTX, "lecturas": LECTURAS,
             "fragmentos": len(indice.frags), "equipo": f"{platform.system()} {platform.machine()}", "huella": marca,
             "resumen": resumir(res), "detalle": [f for r in res for f in r["filas"]]}
    (SALIDA / "evaluacion.json").write_text(json.dumps(datos, ensure_ascii=False, indent=1), encoding="utf-8")
    grab = [{"q": {"pregunta": r["pregunta"]["q"], "sector": r["pregunta"]["sector"]}, "eventos": r["eventos"]} for r in res if r["n"] in GRABAR]
    (AQUI / "grabaciones.json").write_text(json.dumps(grab, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    informe.escribir(datos)
    print(json.dumps(datos["resumen"], ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()

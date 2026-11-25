"""Agente investigador de normativa con gestión del contexto.

    plan -> búsqueda híbrida -> lectura aislada de cada fragmento -> notas con cita literal -> respuesta desde las notas

La idea: ningún texto largo se acumula en la ventana del modelo. Cada fragmento se lee en una llamada propia, solo
sobrevive una nota con su cita (verificada contra el original) y la respuesta final se escribe únicamente con notas.
Cada llamada informa de los tokens reales que ocupa (Ollama), y emite eventos para verlo en la web.
"""
from __future__ import annotations

import json
import math
import re
import time
import unicodedata
import urllib.request
from collections import Counter
from collections.abc import Iterator
from pathlib import Path

import numpy as np

AQUI = Path(__file__).resolve().parent
OLLAMA = "http://127.0.0.1:11434/api/"
EMBED = "nomic-embed-text"
NUM_CTX = 4096                 # ventana deliberadamente pequeña: la de un modelo local modesto
LECTURAS = 6                   # fragmentos que se leen en la primera ronda
CHARS_CITA = 400
VACIAS = set("a al algo como con cual cuando cuanto de del desde donde el ella en entre es esa ese esta este hay la las le "
             "lo los mas me mi no o para pero por que quien se si sin sobre son su sus un una unos y ya cada debe puede".split())


def tokens(s: str) -> list[str]:
    s = "".join(c for c in unicodedata.normalize("NFKD", s.lower()) if not unicodedata.combining(c))
    return [t[:6] for t in re.findall(r"[a-z0-9]+", s) if t not in VACIAS]


def plano(s: str) -> str:
    """Normaliza para comparar citas: sin guiones de corte, espacios ni comillas sobrantes."""
    s = unicodedata.normalize("NFKC", s).replace("­", "").replace("- ", "")
    return re.sub(r"\s+", "", s).strip(".\"«»'…").lower()


def post(ruta: str, cuerpo: dict) -> dict:
    req = urllib.request.Request(OLLAMA + ruta, json.dumps(cuerpo).encode(), {"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=600) as r:
        return json.load(r)


class Indice:
    def __init__(self, carpeta: Path = AQUI / "indice"):
        if not (carpeta / "fragmentos.json").exists():
            raise FileNotFoundError("Falta el índice. Ejecuta antes: python agente/ingesta.py")
        self.frags = json.loads((carpeta / "fragmentos.json").read_text(encoding="utf-8"))
        self.vec = np.load(carpeta / "vectores.npy")
        self.por_id = {f["id"]: f for f in self.frags}
        self.tf = [Counter(tokens(f"{f['ref']} {f['titulo']} {f['titulo']} {f['texto']}")) for f in self.frags]

    def buscar(self, consulta: str, sector: str, k: int, modo: str = "hibrido") -> list[str]:
        """Dentro del sector: 'bm25', 'vector' o 'hibrido' (fusión RRF de ambas)."""
        if modo not in ("bm25", "vector", "hibrido"):
            raise ValueError(f"modo desconocido: {modo}")
        ids = [i for i, f in enumerate(self.frags) if f["sector"] == sector]
        if not ids:
            raise ValueError(f"Sector desconocido: {sector}")
        n = len(ids)
        media = sum(sum(self.tf[i].values()) for i in ids) / n
        bm = np.zeros(n)
        for t in set(tokens(consulta)):
            con = [j for j, i in enumerate(ids) if t in self.tf[i]]
            if not con:
                continue
            idf = math.log(1 + (n - len(con) + .5) / (len(con) + .5))
            for j in con:
                tf, largo = self.tf[ids[j]][t], sum(self.tf[ids[j]].values())
                bm[j] += idf * tf * 2.5 / (tf + 1.5 * (.25 + .75 * largo / media))
        ordenes = [] if modo == "vector" else [np.argsort(-bm, kind="stable")]
        if modo != "bm25":
            q = np.asarray(post("embed", {"model": EMBED, "input": [f"search_query: {consulta}"]})["embeddings"][0])
            ordenes.append(np.argsort(-(self.vec[ids] @ (q / np.linalg.norm(q))), kind="stable"))
        puntos = np.zeros(n)
        for orden in ordenes:
            puntos[orden] += 1 / (60 + np.arange(1, n + 1))
        return [self.frags[ids[j]]["id"] for j in np.argsort(-puntos, kind="stable")[:k]]


def llamar(modelo: str, partes: dict[str, str], sistema: str, esquema: dict, num_ctx: int = NUM_CTX) -> tuple[dict, dict]:
    """Una llamada con salida JSON. `partes` es el contenido del mensaje por bloques, para medir qué ocupa cada uno."""
    usuario = "\n\n".join(v for v in partes.values() if v)
    t0 = time.perf_counter()
    r = post("chat", {"model": modelo, "stream": False, "format": esquema,
                      "options": {"temperature": 0, "seed": 0, "num_ctx": num_ctx, "num_predict": 400},
                      "messages": [{"role": "system", "content": sistema}, {"role": "user", "content": usuario}]})
    entrada, salida = r.get("prompt_eval_count", 0), r.get("eval_count", 0)
    chars = {"instrucciones": len(sistema), **{k: len(v) for k, v in partes.items() if v}}
    total = sum(chars.values()) or 1
    ctx = {"num_ctx": num_ctx, "entrada": entrada, "salida": salida, "ms": round(1000 * (time.perf_counter() - t0)),
           "partes": {k: round(entrada * v / total) for k, v in chars.items()}}
    try:
        return json.loads(r["message"]["content"]), ctx
    except json.JSONDecodeError:
        return {}, ctx        # respuesta cortada: se trata como "no sé", y se ve en la traza


def objeto(**props) -> dict:
    return {"type": "object", "required": list(props), "properties": props}


TEXTO, SINO = {"type": "string"}, {"type": "boolean"}
S_PLAN = ("Eres documentalista jurídico. Escribe 2 búsquedas para encontrar en la norma la respuesta. Cada búsqueda son "
          "de 3 a 8 palabras clave en el lenguaje formal de la norma (sinónimos de la pregunta). Sin frases completas y "
          "sin nombrar la norma. Ejemplo: 'cuantía multas infracciones muy graves'.")
S_LEER = ("Lees UN fragmento de una norma. Primero copia en 'cita', LITERALMENTE, la frase del fragmento más útil para "
          "contestar la pregunta (máximo 2 frases). Después resume en 'dato' qué responde. Por último relevante=true si "
          "con esa frase se puede contestar la pregunta, aunque la norma use otras palabras; false si trata de otra cosa.")
def sistema_final(fuente: str) -> str:
    """Instrucción de la respuesta final; la misma para el agente (notas) y las líneas base (fragmentos)."""
    return (f"Respondes usando SOLO el material numerado ({fuente}). Primero escribe en 'respuesta' el dato concreto que "
            "contesta, en una o dos frases. Después lista en 'notas' los números de donde sale. Por último, "
            "hay_respuesta=true si ese material contiene el dato; false solo si ninguno trata lo preguntado.")


# el orden importa: el modelo redacta y cita antes de decidir si hay respuesta
ESQUEMA_FINAL = {"respuesta": TEXTO, "notas": {"type": "array", "items": {"type": "integer"}}, "hay_respuesta": SINO}


def planificar(modelo: str, pregunta: str, norma: str) -> tuple[list[str], dict]:
    r, ctx = llamar(modelo, {"pregunta": f"Norma: {norma}\nPregunta: {pregunta}"}, S_PLAN,
                    objeto(busquedas={"type": "array", "items": TEXTO, "maxItems": 2}))
    extra = [" ".join(b.split()[:10]) for b in r.get("busquedas", []) if b.strip()][:2]
    return [pregunta, *extra], ctx


def candidatos(indice: Indice, busquedas: list[str], sector: str) -> list[str]:
    """Fusiona los resultados de todas las búsquedas; la pregunta original pesa doble."""
    puntos: dict[str, float] = {}
    for n, b in enumerate(busquedas):
        for pos, i in enumerate(indice.buscar(b, sector, 10), 1):
            puntos[i] = puntos.get(i, 0) + (2 if n == 0 else 1) / (10 + pos)
    por_articulo: Counter = Counter()
    elegidos = []
    for i in sorted(puntos, key=lambda i: -puntos[i]):      # como mucho 2 trozos del mismo artículo
        ref = indice.por_id[i]["ref"]
        if por_articulo[ref] < 2:
            por_articulo[ref] += 1
            elegidos.append(i)
    return elegidos


def leer(modelo: str, pregunta: str, f: dict) -> tuple[dict | None, dict, str]:
    """Lectura aislada de un fragmento. Devuelve (nota o None, contexto, motivo)."""
    r, ctx = llamar(modelo, {"pregunta": f"Pregunta: {pregunta}", "fragmento": f"Fragmento ({f['corto']}, {f['ref']}. {f['titulo']}):\n{f['texto']}"},
                    S_LEER, objeto(cita=TEXTO, dato=TEXTO, relevante=SINO))
    if not r.get("relevante"):
        return None, ctx, "no contesta"
    cita = r.get("cita", "").strip()[:CHARS_CITA]
    if len(plano(cita)) < 12 or plano(cita) not in plano(f["texto"]):
        return None, ctx, "cita no literal"
    return {"id": f["id"], "ref": f["ref"], "corto": f["corto"], "titulo": f["titulo"], "pagina": f["pagina"], "url": f["url"],
            "cita": cita, "dato": r.get("dato", "").strip()[:200]}, ctx, "nota"


def responder(modelo: str, pregunta: str, notas: list[dict], idioma: str) -> tuple[dict, dict]:
    bloque = "\n".join(f"[{n}] ({x['ref']}. {x['titulo']}) «{x['cita']}»" for n, x in enumerate(notas, 1))
    extra = " Answer in English." if idioma == "en" else ""
    r, ctx = llamar(modelo, {"pregunta": f"Pregunta: {pregunta}", "notas": f"Notas:\n{bloque}"},
                    sistema_final("notas") + extra, objeto(**ESQUEMA_FINAL))
    usadas = [n for n in dict.fromkeys(r.get("notas", [])) if 1 <= n <= len(notas)]
    if not r.get("hay_respuesta"):
        estado = "sin_evidencia"
    elif usadas and r.get("respuesta", "").strip():
        estado = "respaldada"
    else:
        estado = "rechazada"
    return {"estado": estado, "respuesta": r.get("respuesta", ""), "citas": [{"n": n, **notas[n - 1]} for n in usadas]}, ctx


def investigar(indice: Indice, pregunta: str, sector: str, modelo: str, idioma: str = "es") -> Iterator[dict]:
    norma = next((f["corto"] for f in indice.frags if f["sector"] == sector), None)
    if norma is None:
        raise ValueError(f"Sector desconocido: {sector}")
    t0 = time.perf_counter()
    busquedas, ctx = planificar(modelo, pregunta, norma)
    yield {"paso": "plan", "busquedas": busquedas, "norma": norma, "ctx": ctx}
    orden = candidatos(indice, busquedas, sector)
    yield {"paso": "buscar", "total": sum(f["sector"] == sector for f in indice.frags), "resultados": [
        {k: indice.por_id[i][k] for k in ("ref", "titulo", "pagina")} for i in orden[:LECTURAS]]}
    notas: list[dict] = []
    for ronda, tramo in enumerate((orden[:LECTURAS], orden[LECTURAS:LECTURAS + 4])):
        if notas:
            break
        if ronda:
            yield {"paso": "ampliar", "cuantos": len(tramo)}
        for i in tramo:
            f = indice.por_id[i]
            nota, ctx, motivo = leer(modelo, pregunta, f)
            if nota:
                notas.append(nota)
            yield {"paso": "leer", "id": i, "ref": f["ref"], "titulo": f["titulo"], "motivo": motivo, "nota": nota, "ctx": ctx,
                   "largo": len(f["texto"])}
    if notas:
        final, ctx = responder(modelo, pregunta, notas, idioma)
    else:
        final, ctx = {"estado": "sin_evidencia", "respuesta": "", "citas": []}, None
    yield {"paso": "final", **final, "ctx": ctx, "notas": len(notas), "segundos": round(time.perf_counter() - t0, 1)}


def rag_simple(indice: Indice, pregunta: str, sector: str, modelo: str, k: int) -> dict:
    """Línea base: meter los k primeros fragmentos de golpe en la ventana."""
    ids = indice.buscar(pregunta, sector, k)
    bloque = "\n\n".join(f"[{n}] ({indice.por_id[i]['ref']}) {indice.por_id[i]['texto']}" for n, i in enumerate(ids, 1))
    r, ctx = llamar(modelo, {"fragmentos": f"Fragmentos:\n{bloque}", "pregunta": f"Pregunta: {pregunta}"},
                    sistema_final("fragmentos"), objeto(**ESQUEMA_FINAL))
    refs = [indice.por_id[ids[n - 1]]["ref"] for n in r.get("notas", []) if 1 <= n <= len(ids)]
    estado = "sin_evidencia" if not r.get("hay_respuesta") else "respaldada" if refs else "rechazada"
    return {"estado": estado, "respuesta": r.get("respuesta", ""), "refs": refs, "ctx": ctx}

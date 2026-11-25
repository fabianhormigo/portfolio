"""Capa léxica (BM25) con filtro duro por norma y versión."""
from __future__ import annotations

import hashlib
import json
import math
import re
import unicodedata
from collections import Counter
from dataclasses import dataclass


class AmbiguedadVersion(Exception):
    pass


class SalidaNoValida(Exception):
    pass


@dataclass(frozen=True)
class Fragmento:
    id: str
    norma: str
    version: str
    fecha: str
    seccion: str
    texto: str


def _tokens(s: str) -> list[str]:
    s = "".join(c for c in unicodedata.normalize("NFKD", s.lower()) if not unicodedata.combining(c))
    return re.findall(r"\w+", s)


_VACIAS = {"de", "la", "el", "los", "las", "en", "y", "o", "a", "un", "una", "que", "se", "por", "con", "del", "al", "es", "para"}


def _ws(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


class Indice:
    def __init__(self, fragmentos: list[Fragmento], k1: float = 1.5, b: float = 0.75):
        self.frags, self.k1, self.b = fragmentos, k1, b
        self.tf = {f.id: Counter(_tokens(f.texto)) for f in fragmentos}
        self.len = {i: sum(c.values()) for i, c in self.tf.items()}
        self.avg = sum(self.len.values()) / max(len(self.len), 1)
        df = Counter(t for c in self.tf.values() for t in c)
        n = len(fragmentos)
        self.idf = {t: math.log(1 + (n - d + 0.5) / (d + 0.5)) for t, d in df.items()}

    def buscar(self, consulta: str, norma: str, version: str | None = None, k: int = 3) -> list[Fragmento]:
        cand = [f for f in self.frags if f.norma == norma and (version is None or f.version == version)]
        versiones = sorted({f.version for f in cand})
        if version is None and len(versiones) > 1:
            raise AmbiguedadVersion(f"{norma} tiene varias versiones {versiones}: indica cuál")
        q = [t for t in _tokens(consulta) if t not in _VACIAS]
        puntuados = []
        for f in cand:
            tf, dl = self.tf[f.id], self.len[f.id]
            s = sum(self.idf.get(t, 0) * tf[t] * (self.k1 + 1) /
                    (tf[t] + self.k1 * (1 - self.b + self.b * dl / self.avg)) for t in q if tf[t])
            if s > 0:
                puntuados.append((s, f))
        return [f for _, f in sorted(puntuados, key=lambda x: -x[0])[:k]]


@dataclass(frozen=True)
class Respuesta:
    consulta: str
    texto: str
    citas: tuple[tuple[str, str], ...]  # (id de fragmento, cita literal)

    @property
    def sha(self) -> str:
        return hashlib.sha256(json.dumps([self.consulta, self.texto, self.citas], ensure_ascii=False).encode()).hexdigest()


def responder(indice: Indice, consulta: str, norma: str, version: str | None = None, generador=None, k: int = 2):
    """Devuelve Respuesta o None si no hay evidencia. `generador(consulta, fragmentos)` -> {"texto", "citas"}."""
    hits = indice.buscar(consulta, norma, version, k)
    if not hits:
        return None
    if generador is None:  # extractivo: sin generación, cita literal
        salida = {"texto": hits[0].texto, "citas": [{"id": hits[0].id, "cita": hits[0].texto}]}
    else:
        salida = generador(consulta, hits)
    por_id = {f.id: f for f in hits}
    citas = []
    for c in salida["citas"]:
        f = por_id.get(c["id"])
        if f is None or _ws(c["cita"]) not in _ws(f.texto):
            raise SalidaNoValida(f"la cita {c['cita']!r} no es literal del fragmento {c['id']}")
        citas.append((f.id, c["cita"]))
    if not citas:
        raise SalidaNoValida("respuesta sin citas")
    return Respuesta(consulta, salida["texto"], tuple(citas))


class Revision:
    """Registro JSONL de decisiones humanas; la aprobación vale solo para el hash exacto de la respuesta."""

    def __init__(self, ruta):
        self.ruta = ruta

    def decidir(self, r: Respuesta, aprobada: bool, revisor: str, motivo: str = "") -> None:
        with open(self.ruta, "a", encoding="utf-8") as f:
            f.write(json.dumps({"sha": r.sha, "aprobada": aprobada, "revisor": revisor, "motivo": motivo}) + "\n")

    def es_valida(self, r: Respuesta) -> bool:
        try:
            with open(self.ruta, encoding="utf-8") as f:
                reg = [json.loads(x) for x in f if x.strip()]
        except FileNotFoundError:
            return False
        ult = [x for x in reg if x["sha"] == r.sha]
        return bool(ult) and ult[-1]["aprobada"]


def cargar_corpus(ruta) -> list[Fragmento]:
    with open(ruta, encoding="utf-8") as f:
        return [Fragmento(**d) for d in json.load(f)]

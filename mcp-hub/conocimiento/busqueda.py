"""Ranking BM25 de pasajes. Puro: recibe los pasajes, no lee ficheros."""
import math
from collections import Counter
from dataclasses import dataclass

from conocimiento.texto import tokens

K1, B = 1.5, 0.75   # BM25 (Robertson y Zaragoza, 2009): valores habituales, sin ajustar a este corpus


@dataclass(frozen=True)
class Pasaje:
    fuente: str        # ruta relativa a recursos/
    sitio: str         # «pág. 12» (PDF) o «línea 40» (texto)
    texto: str
    terminos: str      # tokens normalizados separados por espacios (precalculados al indexar)


@dataclass(frozen=True)
class Resultado:
    pasaje: Pasaje
    puntuacion: float
    coinciden: tuple[str, ...]


def ordenar(pregunta: str, pasajes: list[Pasaje], n: int = 5) -> list[Resultado]:
    q = list(dict.fromkeys(tokens(pregunta)))
    if not q or not pasajes:
        return []
    docs = [p.terminos.split() for p in pasajes]
    media = sum(map(len, docs)) / len(docs) or 1.0
    df = Counter(t for d in docs for t in set(d) & set(q))
    idf = {t: math.log(1 + (len(docs) - df[t] + 0.5) / (df[t] + 0.5)) for t in q}
    res = []
    for p, d in zip(pasajes, docs):
        tf = {t: d.count(t) for t in q if df[t]}
        s = sum(idf[t] * f * (K1 + 1) / (f + K1 * (1 - B + B * len(d) / media)) for t, f in tf.items() if f)
        if s > 0:
            res.append(Resultado(p, s, tuple(t for t in q if tf.get(t))))
    res.sort(key=lambda r: -r.puntuacion)
    return res[:n]

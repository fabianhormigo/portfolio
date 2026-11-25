"""Texto → pasajes y tokens. Puro: sin ficheros ni red (flujo, fase 01/02)."""
import re
import unicodedata

_TOKEN = re.compile(r"[a-z0-9]+(?:[.,/-][a-z0-9]+)*")
# Palabras vacías (es/en): sin ellas BM25 no premia «de», «la», «the»...
VACIAS = frozenset("""
a al algo ante antes como con cual cuando de del desde donde dos el ella en entre era es esa ese eso esta este
esto estos fue ha han hay la las le les lo los mas me mi muy no nos o otra otro para pero por que quien se segun
ser si sin sobre son su sus tambien te tiene todo tras un una unas uno unos y ya
an and are as at be by for from has have in is it its of on or that the this to was were which with
""".split())
MIN_CHARS_PASAJE = 20       # una página con menos texto (portadas de logos, figuras) no es un pasaje
CHARS_TROZO_MD = 1500       # tamaño objetivo de un pasaje de Markdown/texto
CHARS_FRAGMENTO = 700       # lo que se devuelve de cada pasaje


def normalizar(s: str) -> str:
    """Minúsculas y sin tildes (búsqueda insensible a «acústica»/«acustica»)."""
    return "".join(c for c in unicodedata.normalize("NFKD", s.lower()) if not unicodedata.combining(c))


def _raiz(t: str) -> str:
    """Plural español/inglés mínimo: recintos→recinto, reverberaciones→reverberacion."""
    if t.endswith("ciones") and len(t) > 7:
        return t[:-2]
    if t.endswith("s") and len(t) > 4 and not t[-2].isdigit():
        return t[:-1]
    return t


def tokens(s: str) -> list[str]:
    """Tokens normalizados. «16283-1» da también «16283» y «1» para que ambas formas encuentren."""
    out = []
    for t in _TOKEN.findall(normalizar(s)):
        partes = re.split(r"[.,/-]", t)
        for p in ([t] + partes if len(partes) > 1 else [t]):
            if p not in VACIAS:
                out.append(_raiz(p))
    return out


def limpiar_pagina(s: str) -> str:
    return s.strip()


def trocear_texto(s: str, objetivo: int = CHARS_TROZO_MD) -> list[tuple[int, str]]:
    """Markdown/texto → [(línea inicial 1-based, pasaje)], cortando en líneas en blanco o títulos."""
    trozos, actual, inicio, n = [], [], 1, 0
    for i, linea in enumerate(s.splitlines(), 1):
        corte = (not linea.strip() or linea.startswith("#")) and n >= objetivo
        if corte or (linea.startswith("#") and n > objetivo // 3):
            if "".join(actual).strip():
                trozos.append((inicio, "\n".join(actual).strip()))
            actual, inicio, n = [], i, 0
        if not actual and not linea.strip():   # la cita apunta a la primera línea con texto
            inicio = i + 1
            continue
        actual.append(linea)
        n += len(linea) + 1
    if "".join(actual).strip():
        trozos.append((inicio, "\n".join(actual).strip()))
    return [(l, t) for l, t in trozos if len(t) >= MIN_CHARS_PASAJE]


def fragmento(texto: str, terminos: set[str], largo: int = CHARS_FRAGMENTO) -> str:
    """La ventana de ~`largo` caracteres del pasaje con más términos de la pregunta."""
    lineas = [l for l in texto.splitlines() if l.strip()]
    mejor, mejor_p = "", -1
    for i in range(len(lineas)):
        ventana, j = [], i
        while j < len(lineas) and sum(len(x) for x in ventana) < largo:
            ventana.append(lineas[j].strip())
            j += 1
        p = sum(t in terminos for t in tokens(" ".join(ventana)))
        if p > mejor_p:
            mejor, mejor_p = " ".join(ventana), p
    return mejor[:largo + 200]

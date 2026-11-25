"""Texto extraído de recursos/ a ficheros JSON en .texto/ (uno por documento). Sin base de datos.

.texto/ es local y no se versiona.
"""
import json
import os
from pathlib import Path

from conocimiento.busqueda import Pasaje
from conocimiento.texto import MIN_CHARS_PASAJE, limpiar_pagina, tokens, trocear_texto

RAIZ = Path(__file__).resolve().parent.parent
RECURSOS = RAIZ / "recursos"
TEXTO = RAIZ / ".texto"
EXTENSIONES = {".pdf", ".md", ".txt", ".html", ".toml"}
VERSION = 2   # súbela si cambia cómo se extrae o trocea: invalida el texto guardado


def _dentro(rel: str) -> Path:
    p = (RECURSOS / rel).resolve()
    if p != RECURSOS and RECURSOS not in p.parents:
        raise ValueError(f"Ruta fuera de recursos/: {rel}")
    return p


def _fuentes(rel: str):
    base = _dentro(rel)
    if base.is_file():
        yield base
        return
    for dp, dirs, fn in os.walk(base):
        dirs[:] = sorted(d for d in dirs if not d.startswith("."))
        for f in sorted(fn):
            if Path(f).suffix.lower() in EXTENSIONES:
                yield Path(dp) / f


def _destino(fuente: Path) -> Path:
    return TEXTO / (fuente.relative_to(RECURSOS).as_posix() + ".json")


def _al_dia(fuente: Path) -> bool:
    d = _destino(fuente)
    if not d.exists():
        return False
    try:
        doc = json.loads(d.read_text(encoding="utf-8"))
        return doc.get("version") == VERSION and doc["mtime"] == fuente.stat().st_mtime
    except (ValueError, KeyError):
        return False


def _extraer(fuente: Path) -> list[dict]:
    if fuente.suffix.lower() == ".pdf":
        from pypdf import PdfReader   # solo al indexar; consultar no lo necesita
        paginas = ((f"pág. {i}", limpiar_pagina(pg.extract_text() or ""))
                   for i, pg in enumerate(PdfReader(fuente).pages, 1))
    else:
        paginas = ((f"línea {l}", t) for l, t in trocear_texto(fuente.read_text(encoding="utf-8", errors="replace")))
    return [{"sitio": s, "texto": t, "terminos": " ".join(tokens(t))}
            for s, t in paginas if len(t) >= MIN_CHARS_PASAJE]


def indexar(rel: str = "", forzar: bool = False) -> dict:
    """Extrae lo nuevo o cambiado (por fecha de modificación) y borra el texto de fuentes que ya no existen."""
    hechos, errores, al_dia = [], {}, 0
    vistos = set()
    for f in _fuentes(rel):
        vistos.add(_destino(f))
        if not forzar and _al_dia(f):
            al_dia += 1
            continue
        try:
            pasajes = _extraer(f)
        except Exception as e:   # un PDF roto no para el resto; queda en «errores»
            errores[f.relative_to(RECURSOS).as_posix()] = f"{type(e).__name__}: {e}"
            continue
        d = _destino(f)
        d.parent.mkdir(parents=True, exist_ok=True)
        d.write_text(json.dumps({"version": VERSION, "fuente": f.relative_to(RECURSOS).as_posix(), "mtime": f.stat().st_mtime,
                                 "pasajes": pasajes}, ensure_ascii=False), encoding="utf-8")
        hechos.append(f"{f.relative_to(RECURSOS).as_posix()} ({len(pasajes)} pasajes)")
    base = _dentro(rel)
    carpeta = TEXTO / base.relative_to(RECURSOS)
    borrados = [d for d in carpeta.rglob("*.json") if d not in vistos] if base.is_dir() and carpeta.is_dir() else []
    for d in borrados:
        d.unlink()
    return {"extraidos": hechos, "al_dia": al_dia, "borrados": len(borrados), "errores": errores}


def cargar(rel: str = "") -> tuple[list[Pasaje], list[str]]:
    """Pasajes ya extraídos bajo `rel` y lista de fuentes pendientes de (re)indexar."""
    pasajes, pendientes = [], []
    for f in _fuentes(rel):
        if not _al_dia(f):
            pendientes.append(f.relative_to(RECURSOS).as_posix())
            continue
        doc = json.loads(_destino(f).read_text(encoding="utf-8"))
        pasajes += [Pasaje(doc["fuente"], p["sitio"], p["texto"], p["terminos"]) for p in doc["pasajes"]]
    return pasajes, pendientes

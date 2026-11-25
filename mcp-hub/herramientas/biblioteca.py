"""Biblioteca central: todo lo que se deja en recursos/ queda accesible desde el MCP."""
import os
import re
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent / "recursos"
TEXTO = {".md", ".txt", ".toml", ".json", ".csv", ".yaml", ".yml", ".py", ".html", ".svg", ".tex"}
MAX_CHARS = 60_000
MAX_RESULTADOS = 60


def _dentro(rel: str) -> Path:
    p = (RAIZ / rel).resolve()
    if p != RAIZ and RAIZ not in p.parents:
        raise ValueError(f"Ruta fuera de recursos/: {rel}")
    return p


def listar(carpeta: str = "", profundidad: int = 2) -> str:
    base = _dentro(carpeta)
    if not base.is_dir():
        raise FileNotFoundError(f"No existe la carpeta recursos/{carpeta}")
    lineas = []
    for p in sorted(base.rglob("*")):
        if len(p.relative_to(base).parts) > profundidad:
            continue
        rel = p.relative_to(RAIZ).as_posix()
        lineas.append(f"{rel}/" if p.is_dir() else f"{rel}  ({p.stat().st_size / 1024:.0f} KB)")
        if len(lineas) >= 400:
            lineas.append("... (truncado; baja la profundidad o entra en una subcarpeta)")
            break
    return "\n".join(lineas) or "(vacía)"


def leer(ruta: str) -> str:
    p = _dentro(ruta)
    if not p.is_file():
        raise FileNotFoundError(f"No existe recursos/{ruta}")
    if p.suffix.lower() not in TEXTO:
        return f"Fichero binario ({p.suffix}). Ruta absoluta: {p}"
    txt = p.read_text(encoding="utf-8", errors="replace")
    if len(txt) > MAX_CHARS:
        return txt[:MAX_CHARS] + f"\n\n[... truncado: {len(txt)} caracteres en total; ruta {p}]"
    return txt


def buscar(patron: str, carpeta: str = "", contexto: int = 1) -> str:
    """Regex (sin distinguir mayúsculas) en los ficheros de texto de recursos/."""
    rx = re.compile(patron, re.I)
    base = _dentro(carpeta)
    res: list[str] = []
    for dp, _, fn in os.walk(base):
        for f in sorted(fn):
            p = Path(dp) / f
            if p.suffix.lower() not in TEXTO:
                continue
            lineas = p.read_text(encoding="utf-8", errors="replace").splitlines()
            for i, l in enumerate(lineas):
                if rx.search(l):
                    a, b = max(0, i - contexto), min(len(lineas), i + contexto + 1)
                    trozo = " ⏎ ".join(x.strip() for x in lineas[a:b])[:300]
                    res.append(f"{p.relative_to(RAIZ).as_posix()}:{i + 1}: {trozo}")
                    if len(res) >= MAX_RESULTADOS:
                        return "\n".join(res) + f"\n(truncado a {MAX_RESULTADOS}; afina el patrón o la carpeta)"
    return "\n".join(res) or "Sin resultados"


# ─────────────── RAG pequeño (capa 2: conocimiento/). Aquí solo se adapta la salida.
def consultar(pregunta: str, carpeta: str = "", max_pasajes: int = 5) -> str:
    from conocimiento.busqueda import ordenar
    from conocimiento.indice import cargar
    from conocimiento.texto import fragmento

    pasajes, pendientes = cargar(carpeta)
    res = ordenar(pregunta, pasajes, max(1, min(max_pasajes, 15)))
    salida = [f"[{i}] {r.pasaje.fuente} · {r.pasaje.sitio}  (coinciden: {', '.join(r.coinciden)})\n"
              f"{fragmento(r.pasaje.texto, set(r.coinciden))}" for i, r in enumerate(res, 1)]
    if not res:
        salida.append(f"Sin pasajes para «{pregunta}» en {len(pasajes)} pasajes indexados.")
    if pendientes:
        salida.append(f"AVISO: {len(pendientes)} documento(s) sin indexar o cambiados (p. ej. {pendientes[0]}); "
                      "no se han buscado. Ejecuta biblioteca_indexar.")
    return "\n\n".join(salida)


def indexar(carpeta: str = "", forzar: bool = False) -> dict:
    from conocimiento.indice import indexar as _indexar
    return _indexar(carpeta, forzar)

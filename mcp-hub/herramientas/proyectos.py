"""Explorador de solo lectura de proyectos.

Raíz: variable de entorno PROYECTOS_ROOT o, por defecto, la carpeta desde la que se arranca.
"""
import os
import re
import subprocess
from pathlib import Path


ROOT = Path(os.environ.get("PROYECTOS_ROOT") or Path.cwd()).resolve()   # nunca todo el disco por defecto
IGNORAR = {".git", "node_modules", "__pycache__", ".venv", "venv", "dist", "build", ".next", ".idea",
           "_internal", "site-packages", ".pytest_cache"}
MAX_BYTES_BUSCAR = 200_000      # no busca dentro de ficheros mayores
MAX_BYTES_LEER = 1_000_000      # no lee ficheros mayores
MAX_RESULTADOS = 100
MAX_LINEAS_ARBOL = 500


def _seguro(ruta: str) -> Path:
    p = (ROOT / ruta).resolve()
    if p != ROOT and ROOT not in p.parents:
        raise ValueError(f"Ruta fuera de la raíz permitida ({ROOT}): {ruta}")
    return p


def _es_binario(p: Path) -> bool:
    with open(p, "rb") as fh:
        return b"\0" in fh.read(4096)


def listar() -> str:
    filas = []
    for d in sorted(ROOT.iterdir(), key=lambda x: x.name.lower()):
        if d.is_dir() and not d.name.startswith("."):
            filas.append(f"{d.name}{' [git]' if (d / '.git').exists() else ''}")
    return f"Raíz: {ROOT}\n" + "\n".join(filas)


def arbol(ruta: str = "", profundidad: int = 2) -> str:
    base = _seguro(ruta)
    if not base.is_dir():
        raise NotADirectoryError(f"No es una carpeta: {ruta}")
    out: list[str] = []

    def rec(d: Path, nivel: int, pref: str):
        if nivel > profundidad or len(out) >= MAX_LINEAS_ARBOL:
            return
        try:
            hijos = sorted(d.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower()))
        except OSError:
            return
        for h in hijos:
            if h.name in IGNORAR:
                continue
            if len(out) >= MAX_LINEAS_ARBOL:
                out.append(f"{pref}... (truncado a {MAX_LINEAS_ARBOL} líneas)")
                return
            out.append(f"{pref}{h.name}{'/' if h.is_dir() else ''}")
            if h.is_dir():
                rec(h, nivel + 1, pref + "  ")

    rec(base, 1, "")
    return "\n".join(out) or "(vacío)"


def leer(ruta: str, inicio: int = 1, lineas: int = 400) -> str:
    p = _seguro(ruta)
    if not p.is_file():
        raise FileNotFoundError(f"No es un archivo: {ruta}")
    if p.stat().st_size > MAX_BYTES_LEER:
        raise ValueError(f"Archivo demasiado grande ({p.stat().st_size / 1e6:.1f} MB): {ruta}")
    if _es_binario(p):
        return f"Archivo binario ({p.suffix or 'sin extensión'}): {p}"
    txt = p.read_text(encoding="utf-8", errors="replace").splitlines()
    i0 = max(inicio, 1) - 1
    sel = txt[i0: i0 + max(lineas, 1)]
    cola = f"\n[... {len(txt)} líneas en total]" if i0 + len(sel) < len(txt) else ""
    return "\n".join(f"{i0 + 1 + i}\t{l}" for i, l in enumerate(sel)) + cola


def buscar(patron: str, ruta: str = "", extension: str = "") -> str:
    rx = re.compile(patron, re.I)
    base = _seguro(ruta)
    res: list[str] = []
    for dp, dn, fn in os.walk(base):
        dn[:] = [d for d in dn if d not in IGNORAR]
        for f in fn:
            if extension and not f.lower().endswith(extension.lower()):
                continue
            fp = Path(dp) / f
            try:
                if fp.stat().st_size > MAX_BYTES_BUSCAR:
                    continue
                for n, l in enumerate(fp.read_text(encoding="utf-8").splitlines(), 1):
                    if rx.search(l):
                        res.append(f"{fp.relative_to(ROOT).as_posix()}:{n}: {l.strip()[:200]}")
                        if len(res) >= MAX_RESULTADOS:
                            return "\n".join(res) + f"\n(truncado a {MAX_RESULTADOS}; afina el patrón o la ruta)"
            except (OSError, UnicodeDecodeError):
                continue
    return "\n".join(res) or "Sin resultados"


def _git(ruta: str, *args: str) -> str:
    p = _seguro(ruta)
    if not (p / ".git").exists():
        return f"{ruta or ROOT.name} no es un repositorio git"
    r = subprocess.run(["git", *args], cwd=p, capture_output=True, text=True, timeout=30)
    return (r.stdout + r.stderr).strip()


def git(ruta: str, n: int = 15) -> str:
    """Estado (status -sb) y últimos n commits, de una vez: casi siempre se piden juntos."""
    estado = _git(ruta, "status", "-sb")
    if estado.endswith("no es un repositorio git"):
        return estado
    log = _git(ruta, "log", f"-{max(1, min(n, 100))}", "--oneline")
    return f"{estado}\n\nÚltimos commits:\n{log}"

"""PDF oficiales -> fragmentos por artículo (o apartado) con página -> índice de vectores.

    python agente/ingesta.py                  descarga de las fuentes oficiales lo que falte (agente/pdf/)
    python agente/ingesta.py --pdf CARPETA    usa PDF ya descargados

Salida en agente/indice/ (local, no se versiona): fragmentos.json y vectores.npy (nomic-embed-text en Ollama).
"""
from __future__ import annotations

import argparse
import json
import re
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
from pypdf import PdfReader

AQUI = Path(__file__).resolve().parent
INDICE = AQUI / "indice"
OLLAMA = "http://127.0.0.1:11434/api/embed"
EMBED = "nomic-embed-text"
MAX_CHARS = 1300
LOTE, PARALELO = 32, 2      # textos por petición y peticiones simultáneas como máximo
RUIDO = re.compile(r"^\s*(BOLETÍN OFICIAL DEL ESTADO|LEGISLACIÓN CONSOLIDADA|Página \d+|DO L de .*|ELI: .*|.*Diario Oficial de la Unión Europea.*"
                   r"|Documento Básico HR - Protección frente al ruido|HR-\d+)\s*$")
CABECERA = {
    "articulos": re.compile(r"^(?:Artículo\s+(\d+(?:\s(?:bis|ter|quater))?)(?:\.\s*(.*))?|(Disposición\s+\w+\s+[\wáéíóú]+)\.\s*(.*)|(ANEXO(?:\s+[IVXL]+)?))\s*$"),
    "apartados": re.compile(r"^(?:(\d+(?:\.\d+)+)\s+([A-ZÁÉÍÓÚÑ].{3,100})|(Anejo\s+[A-Z])\.?\s*(.*))\s*$"),
}


def lineas(pdf: Path) -> list[tuple[int, str]]:
    """(página, línea) sin cabeceras, pies ni páginas de índice."""
    salida = []
    for n, pagina in enumerate(PdfReader(pdf).pages, 1):
        ls = (pagina.extract_text() or "").split("\n")
        if sum("....." in l or ". . . ." in l for l in ls) >= 8:   # índice
            continue
        salida += [(n, l.strip()) for l in ls if l.strip() and not RUIDO.match(l) and "....." not in l]
    return salida


def secciones(ls: list[tuple[int, str]], estilo: str) -> list[dict]:
    ini = next((i for i, (_, l) in enumerate(ls) if l.startswith("HAN ADOPTADO EL PRESENTE")), None)
    if ini is not None:                       # reglamentos UE: fuera los considerandos
        ls = ls[ini + 1:]
    out, actual = [], None
    for i, (pag, l) in enumerate(ls):
        m = CABECERA[estilo].match(l)
        if m:
            g = m.groups()
            if estilo == "articulos":
                ref = f"art. {g[0]}" if g[0] else (g[2] or g[4])
                titulo = (g[1] if g[0] else g[3]) or ""
                if g[0] and not titulo and i + 1 < len(ls):       # DOUE: el título va en la línea siguiente
                    titulo = ls[i + 1][1]
            else:
                ref = f"apdo. {g[0]}" if g[0] else g[2]
                titulo = (g[1] if g[0] else g[3]) or ""
            actual = {"ref": ref, "titulo": titulo.strip(" ."), "lineas": []}
            out.append(actual)
        elif actual:
            actual["lineas"].append((pag, l))
    return [s for s in out if s["lineas"]]


def trocear(seccion: dict) -> list[tuple[int, str]]:
    """Trozos de hasta MAX_CHARS cortando en fin de frase; cada uno con su página inicial."""
    trozos, texto, pagina = [], "", None
    for pag, l in seccion["lineas"]:
        pagina = pagina or pag
        texto = texto[:-1] + l if texto.endswith("-") else f"{texto} {l}".strip()
        if len(texto) >= MAX_CHARS * 0.75 and (l.rstrip().endswith((".", ";", ":")) or len(texto) >= MAX_CHARS * 1.25):
            trozos.append((pagina, texto))
            texto, pagina = "", None
    if texto:
        trozos.append((pagina, texto))
    return [(p, re.sub(r"\s+", " ", t)) for p, t in trozos]


def fragmentar(doc: dict, pdf: Path) -> list[dict]:
    frags, vistos = [], {}
    for s in secciones(lineas(pdf), doc["estilo"]):
        for pagina, texto in trocear(s):
            vistos[s["ref"]] = n = vistos.get(s["ref"], 0) + 1
            frags.append({"id": f"{doc['id']}:{s['ref'].replace(' ', '')}#{n}", "sector": doc["sector"], "doc": doc["id"],
                          "corto": doc["corto"], "ref": s["ref"], "titulo": s["titulo"], "pagina": pagina, "texto": texto,
                          "url": f"{doc['url']}#page={pagina}"})
    return frags


def embeber_lote(textos: list[str]) -> list[list[float]]:
    """Una sola petición al endpoint por lotes de Ollama."""
    cuerpo = json.dumps({"model": EMBED, "input": [f"search_document: {t}" for t in textos], "truncate": True}).encode()
    with urllib.request.urlopen(urllib.request.Request(OLLAMA, cuerpo, {"Content-Type": "application/json"}), timeout=600) as r:
        return json.load(r)["embeddings"]


def embeber(textos: list[str]) -> np.ndarray:
    lotes = [textos[i:i + LOTE] for i in range(0, len(textos), LOTE)]
    with ThreadPoolExecutor(max_workers=PARALELO) as hilos:       # map conserva el orden de los lotes
        m = np.asarray([v for lote in hilos.map(embeber_lote, lotes) for v in lote], dtype=np.float32)
    return m / np.linalg.norm(m, axis=1, keepdims=True)


def descargar(url: str, destino: Path) -> None:
    """Descarga solo si falta."""
    if destino.exists():
        return
    print("descargando", url)
    req = urllib.request.Request(url, headers={"User-Agent": "portafolio-ingesta"})
    with urllib.request.urlopen(req, timeout=120) as r:
        destino.write_bytes(r.read())


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--pdf", type=Path, default=AQUI / "pdf")
    a = ap.parse_args()
    a.pdf.mkdir(parents=True, exist_ok=True)
    todos = []
    fuentes = json.loads((AQUI / "fuentes.json").read_text(encoding="utf-8"))
    pdfs = [a.pdf / f"{d['id']}.pdf" for d in fuentes]
    with ThreadPoolExecutor(max_workers=PARALELO) as hilos:
        list(hilos.map(descargar, [d["url"] for d in fuentes], pdfs))     # list: propaga los errores
    for doc, pdf in zip(fuentes, pdfs):
        f = fragmentar(doc, pdf)
        refs = {x["ref"] for x in f}
        print(f"{doc['corto']:18s} {len(refs):4d} secciones  {len(f):5d} fragmentos")
        if not f:
            raise SystemExit(f"{doc['id']}: no se ha reconocido ninguna sección")
        todos += f
    INDICE.mkdir(exist_ok=True)
    np.save(INDICE / "vectores.npy", embeber([f"{f['corto']} {f['ref']} {f['titulo']}. {f['texto']}" for f in todos]))
    (INDICE / "fragmentos.json").write_text(json.dumps(todos, ensure_ascii=False), encoding="utf-8")
    print(f"\n{len(todos)} fragmentos en {INDICE}")


if __name__ == "__main__":
    main()

"""La web no tiene enlaces rotos: recursos locales, datos que se cargan, pestañas y redirecciones antiguas."""
import re
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
PAGINAS = sorted([*RAIZ.glob("*.html"), *RAIZ.glob("en/*.html")])
TABS = set(re.findall(r'id="p-(\w+)"', (RAIZ / "index.html").read_text(encoding="utf-8")))


@pytest.mark.parametrize("pagina", PAGINAS, ids=lambda p: p.relative_to(RAIZ).as_posix())
def test_recursos_y_enlaces_locales_existen(pagina):
    html = pagina.read_text(encoding="utf-8")
    for ref in re.findall(r'(?:src|href)="(?!https?:|mailto:|#)([^"]+)"', html):
        ruta, _, ancla = ref.partition("#")
        assert (pagina.parent / ruta).resolve().is_file(), f"{pagina.name}: no existe {ref}"
        assert not ancla or ancla in TABS, f"{pagina.name}: pestaña desconocida {ref}"


def test_cada_pestana_tiene_su_funcion_y_su_enlace():
    js = (RAIZ / "portfolio.js").read_text(encoding="utf-8")
    declaradas = set(re.search(r"const PAGINAS = \{([^}]+)\}", js).group(1).replace(" ", "").split(","))
    assert declaradas == TABS
    assert set(re.findall(r'data-t="(\w+)"', (RAIZ / "en/index.html").read_text(encoding="utf-8"))) == TABS
    assert {a for a in re.findall(r'href="#(\w+)"', js)} <= TABS


def test_los_ficheros_que_carga_el_javascript_existen():
    faltan = []
    for f in ("portfolio.js", "agente.js", "vivo.js", "navegador.js"):
        js = (RAIZ / f).read_text(encoding="utf-8")
        for ruta in re.findall(r'["`]((?:agente|vivo|docs)/[\w/.-]+\.json|[\w-]+\.js)["`]', js):
            if not (RAIZ / ruta).is_file():
                faltan.append(f"{f}: {ruta}")
    assert not faltan

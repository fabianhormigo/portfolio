"""Integración con el índice real (normas descargadas). Se salta si no se ha ejecutado ingesta.py."""
import json
from collections import Counter

import pytest

from agente import AQUI, Indice
from metricas import fragmentos_oro

pytestmark = pytest.mark.skipif(not (AQUI / "indice" / "fragmentos.json").exists(), reason="falta el índice: python agente/ingesta.py")


@pytest.fixture(scope="module")
def indice():
    return Indice()


def test_la_ingesta_reconoce_todos_los_articulos(indice):
    refs = {(f["doc"], f["ref"]) for f in indice.frags if f["ref"].startswith("art.")}
    n = Counter(d for d, _ in refs)
    assert n["rgpd"] == 99 and n["ia"] == 113                     # articulado oficial completo
    assert all(f["pagina"] >= 1 and f["texto"] for f in indice.frags)
    assert len(indice.por_id) == len(indice.frags) == len(indice.vec)


def test_cada_pregunta_tiene_su_respuesta_en_el_texto_oficial(indice):
    preguntas = json.loads((AQUI / "preguntas.json").read_text(encoding="utf-8"))
    sin_oro = [p["q"] for p in preguntas if p["ref"] and not fragmentos_oro(indice.frags, p)]
    assert not sin_oro

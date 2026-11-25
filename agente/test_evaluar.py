"""La evaluación y la ingesta con dobles de prueba: sin modelos ni PDF."""
import numpy as np
import pytest

import agente
import evaluar
import ingesta
from test_flujo import indice, modelo_simulado  # noqa: F401  (fixture y modelo reutilizados)

P = {"q": "¿plazo de la brecha?", "sector": "s", "ref": "art. 1", "esperado": "72 horas", "conjunto": "reservado"}


def test_una_pregunta_produce_tres_filas_y_metricas_por_etapa(indice, monkeypatch):  # noqa: F811
    monkeypatch.setattr(agente, "llamar", modelo_simulado("72 horas"))
    r = evaluar.evaluar_pregunta(indice, 0, P)
    assert [f["modo"] for f in r["filas"]] == ["simple", "volcado", "agente"]
    ag = r["filas"][-1]
    assert ag["correcta"] and ag["oro_leido"] and ag["oro_anotado"] and ag["etapa"] is None
    assert ag["llamadas"] == 2 + ag["lecturas"]                 # plan + lecturas + respuesta
    assert r["recuperacion"]["bm25"] == 1
    resumen = evaluar.resumir([r, {**r, "pregunta": {**P, "conjunto": "desarrollo"}}])
    assert resumen["reservado"]["agente"]["exactitud"] == 1


def test_un_fallo_de_lectura_se_atribuye_a_la_lectura(indice, monkeypatch):  # noqa: F811
    monkeypatch.setattr(agente, "llamar", modelo_simulado(None))
    ag = evaluar.evaluar_pregunta(indice, 0, P)["filas"][-1]
    assert not ag["correcta"] and ag["etapa"] == "lectura"


def test_una_pregunta_mal_definida_detiene_la_evaluacion(indice):  # noqa: F811
    with pytest.raises(ValueError, match="art. 1"):
        evaluar.evaluar_pregunta(indice, 0, {**P, "esperado": "99 siglos"})


def test_la_huella_cambia_con_el_modelo(monkeypatch):
    antes = evaluar.huella()
    monkeypatch.setattr(evaluar, "MODELO", "otro")
    assert evaluar.huella() != antes


def test_ingesta_quita_cabeceras_e_indices(monkeypatch):
    class Pagina:
        def __init__(self, t):
            self.t = t

        def extract_text(self):
            return self.t

    indice_pdf = "\n".join(f"Artículo {n}. Algo ........ {n}" for n in range(10))
    texto = "BOLETÍN OFICIAL DEL ESTADO\nLEGISLACIÓN CONSOLIDADA\nArtículo 1. Objeto.\nEsta ley regula algo.\nPágina 2"
    monkeypatch.setattr(ingesta, "PdfReader", lambda _: type("R", (), {"pages": [Pagina(indice_pdf), Pagina(texto)]})())
    assert ingesta.lineas("x.pdf") == [(2, "Artículo 1. Objeto."), (2, "Esta ley regula algo.")]
    doc = {"id": "l", "sector": "s", "corto": "L", "url": "https://u", "estilo": "articulos"}
    f = ingesta.fragmentar(doc, "x.pdf")
    assert f[0]["id"] == "l:art.1#1" and f[0]["url"] == "https://u#page=2" and f[0]["titulo"] == "Objeto"


def test_los_vectores_se_normalizan(monkeypatch):
    import io
    import json

    class Resp(io.BytesIO):
        def __enter__(self):
            return self

    monkeypatch.setattr(ingesta.urllib.request, "urlopen", lambda *a, **k: Resp(json.dumps({"embeddings": [[3.0, 4.0]] * 2}).encode()))
    assert np.allclose(np.linalg.norm(ingesta.embeber(["a", "b"]), axis=1), 1)

"""Tests de las métricas y del informe, con casos de resultado conocido."""
import pytest

import informe
import metricas as M

P = {"q": "¿plazo?", "sector": "s", "ref": "art. 1", "esperado": "72 horas"}
SIN = {"q": "¿precio?", "sector": "s", "ref": None, "esperado": None}


def test_fragmento_de_oro_exige_articulo_sector_y_dato():
    frags = [{"id": "a", "sector": "s", "ref": "art. 1", "texto": "en 72 horas"},
             {"id": "b", "sector": "s", "ref": "art. 1", "texto": "otra cosa"},
             {"id": "c", "sector": "s", "ref": "art. 2", "texto": "72 horas"},
             {"id": "d", "sector": "t", "ref": "art. 1", "texto": "72 horas"}]
    assert M.fragmentos_oro(frags, P) == ["a"]
    assert M.fragmentos_oro(frags, SIN) == []


def test_hit_y_mrr_con_valores_a_mano():
    m = M.recuperacion([1, 5, None, 2])
    assert (m["hit@1"], m["hit@4"], m["hit@6"], m["hit@12"]) == (0.25, 0.5, 0.75, 0.75)
    assert m["mrr"] == pytest.approx((1 + 1 / 5 + 1 / 2) / 4)
    assert M.posicion(["x", "y", "z"], ["z", "w"]) == 3 and M.posicion(["x"], ["z"]) is None


@pytest.mark.parametrize("valores,q,esperado", [([], 50, 0.0), ([3, 1, 2], 50, 2), ([1, 2, 3, 4], 95, 4), ([5], 95, 5)])
def test_percentil_por_rango(valores, q, esperado):
    assert M.percentil(valores, q) == esperado


@pytest.mark.parametrize("p,estado,respuesta,ok", [
    (P, "respaldada", "Son 72 horas.", True), (P, "respaldada", "Son 48 horas.", False), (P, "sin_evidencia", "72 horas", False),
    (SIN, "sin_evidencia", "", True), (SIN, "rechazada", "", True), (SIN, "respaldada", "100 euros", False)])
def test_correccion(p, estado, respuesta, ok):
    assert M.correccion(p, estado, respuesta) is ok


@pytest.mark.parametrize("vistos,anotados,etapa", [
    (["x"], [], "recuperacion"), (["oro"], [], "lectura"), (["oro"], ["oro"], "respuesta"), (["oro"], None, "respuesta")])
def test_atribucion_del_fallo_a_la_primera_etapa(vistos, anotados, etapa):
    assert M.etapa_fallida(["oro"], vistos, anotados) == etapa


def fila(ref, correcta, estado, **k):
    return {"ref": ref, "correcta": correcta, "estado": estado, "articulo": correcta, "max_entrada": 500, "tokens": 1000, "llamadas": 4,
            "segundos": 2.0, "etapa": None if correcta or not ref else "lectura", "q": "q|x", "respuesta": "r", "oro_leido": True,
            "oro_anotado": correcta, "lecturas": 6, "no_literales": 1, **k}


def test_agregado_cuenta_errores_confiados_y_negativas_falsas():
    m = M.agregar([fila("a", True, "respaldada"), fila("a", False, "sin_evidencia"), fila("a", False, "respaldada"),
                   fila(None, True, "sin_evidencia"), fila(None, False, "respaldada")])
    assert (m["correctas"], m["con_respuesta"], m["negativas"], m["sin_respuesta"]) == (1, 3, 1, 2)
    assert m["negativas_falsas"] == 1 and m["errores_confiados"] == 2
    assert m["fallos"] == {"recuperacion": 0, "lectura": 2, "respuesta": 0}
    e = M.embudo([fila("a", True, "respaldada"), fila("a", False, "sin_evidencia")])
    assert (e["recuperada"], e["anotada"], e["correcta"], e["citas_no_literales"]) == (2, 1, 1, 2)


def resultado(agente, simple):
    base = {"con_respuesta": 4, "errores_confiados": 1, "max_entrada": 500, "tokens_medios": 100, "segundos_p50": 1.0,
            "fallos": {"recuperacion": 2, "lectura": 0, "respuesta": 0}}
    c = {"agente": {**base, "correctas": agente}, "simple": {**base, "correctas": simple}, "volcado": {**base, "correctas": 1}}
    return {"huella": "h", "detalle": [], "resumen": {"reservado": c, "desarrollo": c}}


@pytest.mark.parametrize("a,s,frase", [(3, 2, "es el mejor"), (2, 2, "iguala"), (1, 3, "no supera")])
def test_la_conclusion_no_depende_de_que_el_agente_gane(a, s, frase, monkeypatch, tmp_path):
    monkeypatch.setattr(informe, "AQUI", tmp_path)
    assert frase in informe.conclusion(resultado(a, s), 0)[0]


def test_la_revision_manual_solo_vale_para_su_ejecucion(monkeypatch, tmp_path):
    (tmp_path / "resultados").mkdir()
    (tmp_path / "resultados/revision.json").write_text('{"huella": "h", "descartados": [{"n": 0, "modo": "agente", "motivo": "m"}]}')
    monkeypatch.setattr(informe, "AQUI", tmp_path)
    d = resultado(3, 2)
    d["detalle"] = [{"n": 0, "modo": "agente", "conjunto": "reservado"}]
    assert informe.revisados(d, "reservado", "agente") == 2
    assert informe.revisados({**d, "huella": "otra"}, "reservado", "agente") == 3


def test_el_informe_se_genera_en_los_dos_idiomas_y_escapa_las_tablas(tmp_path, monkeypatch):
    filas = [{**fila("a", False, "respaldada"), "modo": "agente"}]
    un = M.agregar(filas)
    resumen = {c: {**{m: un for m in ("simple", "volcado", "agente")}, "embudo": M.embudo(filas),
                   "recuperacion": {"bm25": M.recuperacion([1])}} for c in ("desarrollo", "reservado")}
    d = {"fecha": "2026-01-01", "modelo": "m", "embeddings": "e", "num_ctx": 4096, "fragmentos": 3, "equipo": "x", "huella": "abc",
         "resumen": resumen, "detalle": filas}
    monkeypatch.setattr(informe, "DOCS", tmp_path)
    informe.escribir(d)
    es, en = (tmp_path / "EVALUACION.md").read_text(encoding="utf-8"), (tmp_path / "EVALUATION.md").read_text(encoding="utf-8")
    assert "Errores confiados" in es and "Confident errors" in en
    assert "q/x" not in es or "q|x" not in es.split("## Fallos concretos")[1].split("\n")[4]

"""El agente de principio a fin con un modelo simulado, y la búsqueda con un índice pequeño en disco."""
import json

import numpy as np
import pytest

import agente
from metricas import fragmentos_oro

FRAGS = [{"id": f"ley:art.{n}#1", "sector": "s", "doc": "ley", "corto": "Ley X", "ref": f"art. {n}", "titulo": t, "pagina": n,
          "texto": x, "url": f"u#page={n}"} for n, t, x in [
    (1, "Notificación", "La brecha se notificará en un plazo de 72 horas."),
    (2, "Sanciones", "Las multas llegarán hasta 20 000 euros."),
    (3, "Registro", "Se llevará un registro de actividades.")]]


@pytest.fixture
def indice(tmp_path, monkeypatch):
    (tmp_path / "fragmentos.json").write_text(json.dumps(FRAGS), encoding="utf-8")
    np.save(tmp_path / "vectores.npy", np.eye(3, dtype=np.float32))
    # embedding simulado: cualquier consulta apunta al segundo documento
    monkeypatch.setattr(agente, "post", lambda ruta, cuerpo: {"embeddings": [[0.0, 1.0, 0.0]]})
    return agente.Indice(tmp_path)


def test_busqueda_por_modos(indice):
    assert indice.buscar("plazo notificar brecha", "s", 1, "bm25") == ["ley:art.1#1"]
    assert indice.buscar("plazo notificar brecha", "s", 1, "vector") == ["ley:art.2#1"]
    assert set(indice.buscar("plazo notificar brecha", "s", 2, "hibrido")) == {"ley:art.1#1", "ley:art.2#1"}
    with pytest.raises(ValueError):
        indice.buscar("x", "otro", 1)
    with pytest.raises(ValueError):
        indice.buscar("x", "s", 1, "magia")


def test_sin_indice_el_error_dice_que_hacer(tmp_path):
    with pytest.raises(FileNotFoundError, match="ingesta.py"):
        agente.Indice(tmp_path)


def modelo_simulado(relevante: str | None):
    """Imita al LLM: anota solo el fragmento cuyo texto contiene `relevante`."""
    def llamar(modelo, partes, sistema, esquema, num_ctx=agente.NUM_CTX):
        ctx = {"entrada": 100, "salida": 10, "ms": 1, "num_ctx": num_ctx, "partes": {}}
        campos = set(esquema["properties"])
        if "busquedas" in campos:
            return {"busquedas": ["plazo de notificación " * 20]}, ctx
        if "relevante" in campos:
            texto = partes["fragmento"].split("\n", 1)[1]
            si = relevante is not None and relevante in texto
            return {"cita": texto if si else "", "dato": "d", "relevante": si}, ctx
        return {"respuesta": "72 horas", "notas": [1], "hay_respuesta": True}, ctx
    return llamar


def test_flujo_completo_responde_con_cita_y_pagina(indice, monkeypatch):
    monkeypatch.setattr(agente, "llamar", modelo_simulado("72 horas"))
    ev = list(agente.investigar(indice, "¿plazo de la brecha?", "s", "m"))
    assert [e["paso"] for e in ev][:2] == ["plan", "buscar"] and ev[-1]["paso"] == "final"
    assert all(len(b.split()) <= 10 for b in ev[0]["busquedas"][1:])           # las búsquedas largas se recortan
    assert ev[-1]["estado"] == "respaldada" and ev[-1]["citas"][0]["pagina"] == 1
    assert {"id", "motivo", "ctx"} <= set(next(e for e in ev if e["paso"] == "leer"))


def test_sin_notas_no_se_llama_a_responder(indice, monkeypatch):
    monkeypatch.setattr(agente, "llamar", modelo_simulado(None))
    ev = list(agente.investigar(indice, "¿salario?", "s", "m"))
    assert ev[-1] == {**ev[-1], "estado": "sin_evidencia", "citas": [], "ctx": None, "notas": 0}


def test_respuesta_del_modelo_cortada_se_trata_como_no_se(monkeypatch):
    monkeypatch.setattr(agente, "post", lambda *a: {"message": {"content": '{"respuesta": "a medias'}, "prompt_eval_count": 50, "eval_count": 400})
    salida, ctx = agente.llamar("m", {"pregunta": "x" * 30, "notas": "y" * 70}, "z" * 100, {})
    assert salida == {} and ctx["entrada"] == 50 and sum(ctx["partes"].values()) == pytest.approx(50, abs=2)


def test_fragmento_de_oro_en_el_indice_de_prueba(indice):
    assert fragmentos_oro(indice.frags, {"sector": "s", "ref": "art. 2", "esperado": "20 000"}) == ["ley:art.2#1"]
